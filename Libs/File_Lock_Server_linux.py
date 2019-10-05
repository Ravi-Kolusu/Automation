import os, sys, json
import subprocess
import socket
from datetime import datetime
from flask import Flask, request, Response, jsonify

Log_file = '/opt/data/log/app_' + socket.gethostname() + '.log'

def write_log(log):
    with open(Log_file, 'a') as f:
        f.write(datetime.now().strftime('[%d-%m-%y%H:%M:%S:%f]') + str(log) + '\n')
        f.flush()

if 'win' in sys.platform:
    # Below is windows based File Locking
    import msvcrt

    def file_size(f):
        return os.path.getsize(os.path.realpath(f.name))

    def _lockFileWin(f, op=msvcrt.LK_RLCK, offset=0, length=None):
        if not length:
            length = file_size(f)
        f.seek(offset)
        msvcrt.locking(f.fileno(), op, length)

    def _unlockFileWin(f, offset=0, length=None):
        if not length:
            length = file_size(f)
        f.seek(offset)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, length)

else:
    # Below is the POSIX based Filelocking, used in Linux, MacOS
    import fcntl

    def _lockFilePosix(f, op=fcntl.LOCK_EX|fcntl.LOCK_NB, offset=0, length=0):
        fcntl.lockf(f, op, length, offset, 0)

    def _unlockFilePosix(f, offset=0, length=0):
        fcntl.lockf(f, fcntl.LOCK_UN, length, offset)

    records = dict()
    lock_op = {1: fcntl.LOCK_SH,
               2: fcntl.LOCK_EX,
               5: fcntl.LOCK_SH | fcntl.LOCK_NB,
               6: fcntl.LOCK_EX | fcntl.LOCK_NB}

    def mount_nfs(**kwargs):
        cmd = 'mount -t nfs %s:%s %s'%(kwargs['serverIp'],
                                       kwargs['fsPath'],
                                       kwargs['mountPath'])
        if len(kwargs) > 3:
            if kwargs['mountVersion'] or kwargs['vers']:
                cmd += ' -o vers=%s'%(kwargs['vers']|kwargs['mountVersion'])
            if kwargs['minorversion']:
                cmd += ' -o minorversion=%s'%(kwargs['minorversion'])
        # TODO :: need to add more options
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            if result is None or result == "":
                return json.dumps({'cmd':cmd, 'result':'success'})
            return json.dumps({'cmd':cmd, 'result':result})
        except subprocess.CalledProcessError as e:
            return json.dumps({'cmd':e.cmd, 'result':'failed', 'reason':e.output})
        except Exception as e:
            return json.dumps({'cmd':kwargs, 'result':'failed', 'reason':e.message})

    def unmount_nfs(**kwargs):
        try:
            cmd = 'umount -lf %s'%(kwargs['mountPath'])
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
                if result is None or result == "":
                    return json.dumps({'cmd': cmd, 'result': 'success'})
                return json.dumps({'cmd': cmd, 'result': result})
            except subprocess.CalledProcessError as e:
                return json.dumps({'cmd': e.cmd, 'result': 'failed', 'reason': e.output})
        except Exception as e:
            return json.dumps({'cmd': kwargs, 'result': 'failed', 'reason': e.message})

    def open_file(**kwargs):
        try:
            fh = open(kwargs['file_path'], kwargs['mode'])
            fd = fh.fileno()
            records[fd] = fh
            kwargs['fd'] = fd
            kwargs['mode'] = fh.mode
            return json.dumps(kwargs)
        except Exception as e:
            kwargs['result'] = 'failed'
            kwargs['reason'] = str(e)
            return json.dumps(kwargs)

    def lock_file(cmd):
        try:
            fh = records[int(str(cmd['fd']))]
            write_log(str(fh))
            if fh.closed:
                raise Exception('Invalied FD')
            if 'lock_list' in cmd:
                passed=failed=0
                for lock in cmd['lock_list']:
                    try:
                        _lockFilePosix(cmd['fd'],
                                       op=cmd['op'],
                                       length=lock['length'],
                                       offset=lock['offset'])
                        lock['status'] = 'success'
                        passed += 1
                    except Exception as e:
                        failed += 1
                        lock['status'] = 'failed'
                        lock['reason'] = str(e)
                cmd['passed'] = passed
                cmd['failed'] = failed
            else:
                _lockFilePosix(int(cmd['fd']),
                               op=int(cmd['op']),
                               length=int(cmd['length']),
                               offset=int(cmd['offset']))
                cmd['result'] = 'success'
            return json.dumps(cmd)
        except Exception as e:
            cmd['result'] = 'failed'
            cmd['reason'] = str(e)
            return json.dumps(cmd)

    def unlock_file(cmd):
        try:
            fh=records[int(cmd['fd'])]
            write_log(str(fh))
            if fh.closed:
                raise Exception('Invalid FD')
            if 'lock_list' in cmd:
                passed = failed = 0
                for lock in cmd['lock_list']:
                    try:
                        _unlockFilePosix(cmd['fd'],
                                         length=lock['length'],
                                         offset=lock['offset'])
                        lock['status']='success'
                        passed += 1
                    except Exception as e:
                        failed += 1
                        lock['status']='failed'
                        lock['reason']=str(e)
                cmd['passed']=passed
                cmd['failed']=failed
            else:
                _unlockFilePosix(int(cmd['fd']),
                                 length=int(cmd['length']),
                                 offset=int(cmd['offset']))
                cmd['result']='success'
            return json.dumps(cmd)
        except Exception as e:
            return json.dumps({'cmd':cmd, 'result':'failed', 'reason':str(e)})

    def close_file(**kwargs):
        try:
            fd=int(kwargs['fd'])
            if fd in records:
                fh=records.pop(fd)
                fh.close()
                kwargs['result']='success'
                return json.dumps(kwargs)
            else:
                kwargs['result']='failed'
                kwargs['reason']='Bad Fd'
                return json.dumps(kwargs)
        except Exception as e:
            kwargs['result'] = 'failed'
            kwargs['reason'] = str(e)
            return json.dumps(kwargs)

    op_map = {'open_file':open_file, 'lock_file':lock_file, 'unlock_file':unlock_file, 'close_file':close_file,
              'mount':mount_nfs, 'unmount':unmount_nfs}
    app = Flask(__name__)

    @app.route("/fileop")
    def fileop():
        try:
            args=request.args.to_dict()
            write_log(args)
            result=op_map[args['cmd']](args)
            write_log(str(result))
            return str(result)
        except Exception as e:
            write_log('FATAL ERROR:'+str(e))
            return str(e)

    @app.route("/multi_cmd", methods=['POST'])
    def multi_cmd():
        try:
            data=request.get_json()
            for entry in data.get('cmds'):
                write_log(entry)
                result=op_map[entry['cmd']](entry['para'])
                write_log(str(result))
            return app.response_class(response=json.dumps(data),
                                      status=200,
                                      mimetype='application/json')
        except Exception as e:
            write_log("FATAL ERROR:" + str(e))
            return str(e)

if __name__=='__main__':
    ip='0.0.0.0'
    if len(sys.argv) > 1:
        ip=sys.argv[1]
    write_log("start server\n")
    app.run(host=ip, port=4240, debug=False, threaded=False)




