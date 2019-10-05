__author__ = 'Raviteja'

import json
import requests
import logging

class pyLock(object):
    """
    @version : 1.0
    @date : 05-10-2019
    """
    def __init__(self, server_address):
        self.server_address = server_address
        self.logger = logging.getLogger(__name__)

    def excute_py_cmd(self, cmd, **kwargs):
        params = {'cmd':cmd}
        if kwargs:
            params.update(kwargs)
        if 'timeout' in kwargs.keys():
            t_out = kwargs['timeout']
        else:
            t_out = 300
        resp = requests.get(url='http://%s/fileop'%(self.server_address),
                            params=params,
                            timeout=t_out).text
        try:
            return json.loads(resp)
        except json.JSONEncoder:
            return resp

    def execute_py_multi_cmd(self, req_data, timeout=500):
        resp=requests.post('http://%s/multi_cmd'%(self.server_address), json=req_data,
                           timeout=timeout)
        return resp.json()

    def mount_nfs(self, mountIp, mountPath, exportPath,
                  mountVers, minorversion, timeo, retry):
        resp = self.excute_py_cmd('mount', mount_ip=mountIp, export_path=exportPath, mount_path=mountPath,
                                  mount_vers=mountVers, minorversion=minorversion, timeo=timeo, retry=retry)
        if type(resp) is dict:
            assert resp['result'] == 'success'
        else:
            raise Exception(resp)

    def unmount_nfs(self, mountPath):
        resp = self.excute_py_cmd('unmount', mount_path=mountPath)
        return resp

    def open_file(self, filePath, mode, get_fd=True):
        resp = self.excute_py_cmd('open_file', file_path=filePath, mode=mode)
        if get_fd:
            return resp['fd']
        return resp

    def lock_file(self, fd, op, offset, length, validate=True):
        resp = self.excute_py_cmd('lock_file', fd=fd, op=op, offset=offset, length=length)
        if validate:
            assert resp['result']=='success'
        return resp

    def get_res_from_cmds(self, cmds):
        res=[]
        failed=[]
        for cmd in cmds:
            if 'fd' not in cmd['para']:
                failed.append(cmd['para'])
            else:
                res.append(cmd['para'])
        return res, failed

    def multi_open(self, mode, file_paths, verify, timeout):
        cmds = {'cmds':[]}
        for path in file_paths:
            cmds['cmds'].append({'cmd':'open_file',
                                 'para':{'file_path':path, 'mode':mode}})
        if timeout:
            resp = self.execute_py_multi_cmd(cmds, timeout)
        else:
            resp = self.execute_py_multi_cmd(cmds)
        results, failed = self.get_res_from_cmds(resp['cmds'])
        if verify:
            if len(results) != len(file_paths) or failed != []:
                raise Exception('Some open failed :: %s'%(failed))
            return {'success':results, 'failed':failed}

    def multi_lock(self, fd_list, ranges, op, validate, timeout=500):
        cmds = {'cmds': []}
        lock_list = []
        for offset, length in ranges:
            lock_list.append({'offset':offset, 'length':length})
        for fd in fd_list:
            cmds['cmds'].append({'cmd':'lock_file',
                                 'para':{'fd':fd, 'op':op, 'lock_list':lock_list}})
        if timeout:
            resp = self.execute_py_multi_cmd(cmds, timeout)
        else:
            resp = self.execute_py_multi_cmd(cmds)
        if validate:
            for cmd in resp['cmds']:
                assert cmd['para']['failed'] == 0
        return resp

    def unlock_file(self, fd, offset=0, length=0, validate=True):
        resp = self.excute_py_cmd('unlock_file', fd=fd, offset=offset, length=length)
        if validate:
            assert resp['result'] == 'success'
        return resp

    def multi_unlock(self, fd_list, ranges, validate=True):
        cmds = {'cmds': []}
        lock_list = []
        for offset, length in ranges:
            lock_list.append({'offset': offset, 'length': length})
        for fd in fd_list:
            cmds['cmds'].append({'cmd': 'unlock_file',
                                 'para': {'fd': fd, 'lock_list': lock_list}})
        resp = self.execute_py_multi_cmd(cmds)
        if validate:
            for cmd in resp['cmds']:
                assert cmd['para']['failed'] == 0
        return resp

    def close_file(self, fd):
        resp = self.excute_py_cmd('close_file', fd=fd)
        assert resp['result'] == 'success'

    def multi_close(self, fd_list):
        cmds = {'cmds': []}
        for fd in fd_list:
            cmds['cmds'].append({'cmd':'close_file',
                                 'para':{'fd':fd}})
        resp = self.execute_py_multi_cmd(cmds)
        for cmd in resp['cmds']:
            assert cmd['para']['result'] == 'success'
        return resp['cmds']


