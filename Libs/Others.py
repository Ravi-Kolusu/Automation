
__author__ = 'rWX641509'

import re
import numpy as np
"""
Pick the element in array based on probability
"""
a = np.array([0.1,0.1,0.1,0.7])
check = ['1', '2', '3', '4']
for i in range(10):
a=a.ravel()
k = np.random.choice(check)
print(k)

=======================================================================================================
"""
Remove a line from linux file
"""

import logging
import re, paramiko, pdb, threading


ip_list = ['10.18.18.102']
user_name = 'root'
passwd = 'huawei@123'
final_list = []

p1 = paramiko.SSHClient()
p1.set_missing_host_key_policy(paramiko.AutoAddPolicy)
p1.connect(hostname=ip_list[0], port=22, username=user_name, password=passwd)
cmd = 'cat /etc/passwd'
s1,s2,s3 = p1.exec_command(cmd)
output = s2.readlines()
for line in output:
if re.search('ravi', line):
final = filter(lambda a:output[a] == line, range(0, len(output)))

#print(final)
#print(len(final))
def del_line(line_no, ip='10.18.18.102', u=user_name, p=passwd):
p1 = paramiko.SSHClient()
p1.set_missing_host_key_policy(paramiko.AutoAddPolicy)
p1.connect(hostname=ip, port=22, username=u, password=p)
cmd = "sed -i '%s'd /etc/passwd"%(line_no+1)
pdb.set_trace()
p1.exec_command(cmd)

threads = []
for i in final:
pdb.set_trace()
t = threading.Thread(target=del_line,args=i)
threads.append(t)

for i in threads:
i.start()

for i in threads:
i.join()

======================================================
"""
Remove a line in linux config file(/etc)
"""
cmd_Get_uid = ["awk -F':' '{print $1','NR}' /etc/passwd | grep ravi | awk -F',' '{print $2}'"]
cmd_del_uid = "sed -i %sd /etc/passwd"%(line)
for i in $k;
do
sed -i $i'd' /etc/passwd
echo 'check k inside loop'
echo $k
done

cat /etc/passwd
=================================================================
"""
use of super function in python
"""
import pdb

class grandparent(object):
def __init__(self):
pass
def func(self):
self.e1 = 1
self.e2 = 2

class parent(grandparent):
def __init__(self):
super(parent, self).__init__()
def func_1(self):
self.f1 = 3
self.f2 = 4

class child(parent):
def func(self):
super(child, self).func()
self.f3 = 5
self.f4 = 6
return [self.e1, self.e2, self.f3, self.f4]


print(child().func())




================================================================================================
"""
Execute SIO tool from remote system
"""
#sio

import paramiko
import time

ip_list = ['10.19.172.16', '10.19.172.17', '10.19.172.18']
file_size = '10m'
block_size = '4k'
choice = [0, 50, 100]
threads = 2
cmd_file = "cd /home/SIO_executable_Tool;touch file"
time = 60*10

p1 = paramiko.SSHClient()
p1.set_missing_host_key_policy(paramiko.AutoAddPolicy)

for _ in xrange(100):
p1.connect(ip_list[0], 22, 'root', 'huawei@123')
p1.exec_command(cmd_file)
cmd = "./sio_ntap_linux {0} {1} {2} {3} {4} {5} file".format(choice[0], choice[0],
block_size, file_size, time,
threads)
start = time.time()
p1.exec_command(cmd)
while True:
time.sleep(120)
process_time = time.time() - start
if process_time >= 600:
break

==========================================================================================================
"""
Execte SIO in the same node
"""
import os, time
import commands
import random
import logging

mount_list = ['/mnt/node1/', '/mnt/node2/', '/mnt/node3/']
file_size = '10m'
block_size = '4k'
choice = [0, 50, 100]
threads = 2
tim = 60*10

for _ in range(100):
cmd_create = 'touch %sfile'%random.choice(mount_list)
commands.getoutput(cmd_create)
cmd = "cd /home/testTools/SIO_executable_Tool;./sio_ntap_linux {0} {1} {2} {3} {4} {5} {" \
"6}file".format(choice[0], random.choice(choice), block_size, file_size, tim, threads,
random.choice(mount_list))
start = time.time()
commands.getoutput(cmd)
while True:
time.sleep(120)
pro = time.time() - start
if pro >= 600:
break
cmd_delete = 'rm %sfile'%random.choice(mount_list)
commands.getoutput(cmd_delete)
(OR)
mount_list = ['/mnt/node1/', '/mnt/node2/', '/mnt/node3/']
file_size = '10m'
block_size = '4k'
choice = [0, 50, 100]
threads = 2
tim = 60*10
logging.basicConfig(filename=script.log, filemode='a', format='%(asctime)s,%(msecs)d %(name)s %('
'levelname)s %(message)s',
datefmt='%H:%M:%S', level=logging.INFO)

for _ in range(100):
cmd_create = 'touch %sfile'%random.choice(mount_list)
result = commands.getoutput(cmd_create)
logging.info('%s'%result)
cmd = "cd /home/testTools/SIO_executable_Tool;./sio_ntap_linux {0} {1} {2} {3} {4} {5} {" \
"6}file".format(choice[0], random.choice(choice), block_size, file_size, tim, threads,
random.choice(mount_list))
start = time.time()
result = commands.getoutput(cmd)
logging.info('%s'%result)
while True:
time.sleep(120)
pro = time.time() - start
if pro >= 600:
break
cmd_delete = 'rm %sfile'%random.choice(mount_list)
commands.getoutput(cmd_delete)



===========================================================================================================
"""
take the input of students and marks and return the average of marks of given student
"""
n = int(raw_input())
student_marks = {}
for _ in range(n):
line = raw_input().split()
name, scores = line[0], line[1:]
scores = map(float, scores)
student_marks[name] = scores
query_name = raw_input()

marks = lambda a,b,c : a+b+c
result = float(marks(student_marks[query_name][0], student_marks[query_name][1], student_marks[
query_name][2]))/float(len(student_marks[query_name]))
result = round(result, 2)
print(result)

============================================================================================================
"""
if A subset of B ==> True
if A not subset of B ==> False
"""
import pdb

if __name__ == '__main__':
final = []
tcase_count = int(raw_input(''))
for case in range(tcase_count):
A_set_count = int(raw_input(''))
A = raw_input('').split(' ')
A_set = set(A)
B_set_count = int(raw_input(''))
B = raw_input('').split(' ')
B_set = set(B)
if A_set.issubset(B_set):
final.append(True)
else:
final.append(False)
for i in final:
print(i)
===================================================================================================================

"""
Given a matrixin an order M*N , interchange the columns given.

InputFormat:

Firsttwo values are the order of matrix M and N.

MatrixElements

Lasttwo values are the columns to be interchanged.

OutputFormat:

Print theinterchanged matrix.

SampleInput:

3 3 4 1 7 5 2 8 6 3 9 1 2

SampleOutput:

1 4 7

2 5 8

3 6 9

SampleInput:

3 4 2 4 6 8 3 6 9 12 1 2 3 4 2 4

SampleOutput:

2 8 6 4

3 12 9 6

1 4 3 2
"""
k = [int(i) for i in raw_input('').split()]
row = k[0]
col = k[1]
inter_1 = k[-2]
inter_2 = k[-1]
final = k[2:-2]
ini_list = [final[i*col:col*(i+1)] for i in range(row)]
temp1 = 0
temp2 = 0
for lis in ini_list:
temp1 = lis[inter_1-1]
temp2 = lis[inter_2-1]
lis[inter_1-1] = temp2
lis[inter_2-1] = temp1
result = [str(i) for i in lis]
print(" ".join(result))

===============================================================
"""
Find the longest common substring between two strings
"""

def subStr_list(s):
l = []
for i in range(len(s)+1):
for j in range(len(s)+1):
k = s[i:j]
if k not in l:
l.append(k)
return l
f1 = subStr_list('abcdghf')
f2 = subStr_list('ablcdghlk')
f3 = []
for i in f1:
if i in f2:
f3.append(i)

print(max(f3, key=len))


=============================================================
"""
Run the local script on remote server/client which has only python (No script)
"""

import sys
import os

def main():
print os.name

if __name__ == '__main__':
try:
if sys.argv[1] == 'deploy':
import paramiko

# Connect to remote host
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('remote_hostname_or_IP', username='john', password='secret')

# Setup sftp connection and transmit this script
sftp = client.open_sftp()
sftp.put(__file__, '/tmp/myscript.py')
sftp.close()

# Run the transmitted script remotely without args and show its output.
# SSHClient.exec_command() returns the tuple (stdin,stdout,stderr)
stdout = client.exec_command('python /tmp/myscript.py')[1]
for line in stdout:
# Process each line in the remote output
print line

client.close()
sys.exit(0)
except IndexError:
pass

# No cmd-line args provided, run script normally
main()

================================================================================


from threading import *
from queue import *
import os, re
import random, time, sys

def write_file(file_path, mode, data):
if isinstance(data, str):
with open(file_path, mode) as f:
f.write(data)
f.close()
elif isinstance(data, list):
with open(file_path, mode) as f:
for line in data:
f.write(line)
f.close()
else:
raise Exception('Unidentified instance of %s'%(data))
return "Success"

def generate_data(Req_size):
"""
Args:
Req_size (str) :: Required amount of data

Returns:
final_str (str) :: string with required size

Example:
generate_data("100M")
"""
final_str = ""

if 'k' in Req_size or 'K' in Req_size:
size = 1024*(int(re.search('\d+', Req_size).group()))
while sys.getsizeof(final_str) < size:
final_str += str(random.randint(0, 20))

elif 'm' in Req_size or 'M' in Req_size:
size = 1024*1024*(int(re.search('\d+', Req_size).group()))
while sys.getsizeof(final_str) < size:
final_str += str(random.randint(0, 20))

elif 'g' in Req_size or 'G' in Req_size:
size = 1024*1024*1024*(int(re.search('\d+', Req_size).group()))
while sys.getsizeof(final_str) < size:
final_str += str(random.randint(0, 20))

else:
raise Exception("Not supported")

print("Created file size :: %sB"%(sys.getsizeof(final_str)))
return final_str

root_dir = 'C:'
sub_dir1 = 'Users'
sub_dir2 = 'rWX641509'
sub_dir3 = 'Desktop'
file_name = 'file1.txt'

filePath = os.path.join(root_dir, sub_dir1, sub_dir2, sub_dir3, file_name)
fileMode = 'a+'

q = Queue()
q.put(generate_data('1m'))
print(write_file(filePath, fileMode, q.get()))


=========================================================

__author__ = 'a'

# Below are the important packages


import netmiko, pdb
import paramiko
from paramiko import AuthenticationException
import scrapy
import pandas
import selenium
#import pyod
import numpy
#import spacy
import matplotlib
import seaborn
#import bokeh
#import tensorflow
#import lime
import twisted
#import pywin32_system32
#import IPython
import multiprocessing
import threading
import logging
import os, sys
# Below are the frameworks
#import robot
#import pytest
#import behave
#import lettuce

l = logging.getLogger(__name__)

i = 1
while i < sys.argv:
l.debug('the value of %s'%i)
if i == sys.argv:
os.system('kill -9 %s'%(os.getpid()))



logging.basicConfig(filename=script.log, filemode='a', format=)
================

l = ["10.19.172.171, 10.19.172.172, 10.19.172.173, 10.19.172.174, 10.18.12.220, 10.19.172.30, "
"10.19.172.27, 10.19.172.28, 10.19.172.29, 10.19.120.233, 10.19.172.43, 10.19.172.44, 10.19.172.45, 10.19.172.46, 10.19.120.218, 10.19.172.23, 10.19.172.24, 10.19.172.25, "
"10.19.172.26, 10.19.120.227, 10.19.172.163, 10.19.172.164, 10.19.172.165, 10.19.172.166, "
"10.19.120.228, 10.19.172.197, 10.19.172.183, 10.19.172.184, 10.19.172.196, 10.18.4.85, "
"10.19.172.179, 10.19.172.180, 10.19.172.181, 10.19.172.182, 10.18.4.66, 10.19.172.175, "
"10.19.172.176, 10.19.172.177, 10.19.172.178, 10.18.110.70, 100.107.211.35, 100.107.194.170, "
"100.107.235.31, 100.107.227.47, 100.107.181.47, 10.19.172.124, 10.19.172.125, 10.19.172.126, "
"10.19.171.91, 10.19.172.127, 10.19.172.128, 10.19.172.129, 10.19.172.92, ", "10.19.172.130, 10.19.172.131, 10.19.172.106, 10.19.171.93"]

fin = l[1].split(", ")
cmd = "reboot -f"
user='root'
pass1 = 'huawei@123'
pass2 = 'huawei'
result = []
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy)
for ip in fin:
try:
print('IP :: %s'%(ip))
print('Username :: %s'%(user))
print('Password :: %s'%(pass1))
c1.connect(ip, 22, username=user, password=pass1)
except AuthenticationException as e:
print('IP :: %s'%(ip))
print('Username :: %s'%(user))
print('Password :: %s'%(pass2))
c1.connect(ip, 22, username=user, password=pass2)
finally:
result.append(ip)
c1.exec_command(cmd)

if fin == result:
raise Exception('All not got executed')

Given a set of mutual friends in a class, can you divide the class in two groups such that:
For all students in a group, each student is a friend of every other student?

Note: Friendship is not transitive, i.e. if A and B are friends, and B and C are friends, it does not imply that A and C are friends.


import pyftpdlib
from threading import *
from queue import *
import os, re
import random, time, sys

def write_file(file_path, mode, data):
if isinstance(data, str):
with open(file_path, mode) as f:
f.write(data)
f.close()
elif isinstance(data, list):
with open(file_path, mode) as f:
for line in data:
f.write(line)
f.close()
else:
raise Exception('Unidentified instance of %s'%(data))
return "Success"

def generate_data(Req_size):
final_str = ""

if 'k' in Req_size or 'K' in Req_size:
size = 1024*(int(re.search('\d+', Req_size).group()))
while sys.getsizeof(final_str) < size:
final_str += str(random.randint(0, 20))

elif 'm' in Req_size or 'M' in Req_size:
size = 1024*1024*(int(re.search('\d+', Req_size).group()))
while sys.getsizeof(final_str) < size:
final_str += str(random.randint(0, 20))

elif 'g' in Req_size or 'G' in Req_size:
size = 1024*1024*1024*(int(re.search('\d+', Req_size).group()))
while sys.getsizeof(final_str) < size:
final_str += str(random.randint(0, 20))

else:
raise Exception("Not supported")

print("Created file size :: %sB"%(sys.getsizeof(final_str)))
return final_str

root_dir = 'C:'
sub_dir1 = 'Users'
sub_dir2 = 'rWX641509'
sub_dir3 = 'Desktop'
file_name = 'file1.txt'

filePath = os.path.join(root_dir, sub_dir1, sub_dir2, sub_dir3, file_name)
fileMode = 'a+'

q = Queue()
q.put(generate_data('1m'))
print(write_file(filePath, fileMode, q.get()))

==============================
#ord(a-z) == 97 - 122, ord(A-Z) == 65 - 90, ord(0-9) == 48-57
l = 'abc%def4'
k = []
for i in l:
if ord(i) >= 97 and ord(i) = 65 and ord(i) = 48 and ord(i) 2:
self._buffer = []
self._retries = 0
if self._shutdown_event.is_set():
self._send_data()
if self._retries == 0 or self._retries > 2:
break
time.sleep(1)

def shutdown(self):
self._shutdown_event.set()

def _get_all_data(self):
if self._queue.empty():
return
for _ in xrange(self._queue.qsize()):
item = self._queue.get()
self._current_length -= len(item)
self._buffer.append(item)

def _send_data(self):
try:
self._get_all_data()
if self._buffer:
rsp = requests.post(self._elastic_msg_url, data=''.join(self._buffer), timeout=15)
if rsp.ok:
self._buffer = []
self._retries = 0
else:
ElasticHandler.write_es_access_log(
'warn', 'The post request return code %s, and not raise any exception yet' % rsp.status_code)
self._retries += 1
except Exception as e:
ElasticHandler.write_es_access_log('warn', 'Elastic worker send data failed, %s' % e.message)
self._retries += 1
if self._retries > 2:
ElasticHandler.write_es_access_log(
'error', '%s logs send to es failed and there logs won\'t retry to send.' % len(self._buffer))


class ElasticHandler(logging.Handler):
_log_worker = None
__file_lock = RLock()
__es_error_log = None

def __init__(self, es_index, conf, log_id=None, elastic_type="log"):
super(ElasticHandler, self).__init__()

self.html_parser = HTMLParser.HTMLParser()
self.index = "{}_{}".format(es_index, datetime.now().strftime("%Y-%m-%d"))
self.type = elastic_type
self.elastic_index_url = "{}/{}".format(conf['elkUri'], self.index)
self.elastic_msg_url = "{}/{}/{}/_bulk".format(conf['elkUri'], self.index, self.type)
self.log_id = str(log_id)
self.source_ip = self._get_local_ip()
self.sequence = 0
self.__class__.__es_error_log = os.path.join(conf['logDir'], 'elastic_err.log')
if conf.get('level') is not None:
self.setLevel(conf['level'])
self._start_worker()

def _make_elk_index(self):
try:
mapping = json.dumps({"mappings": {
self.type: {
"properties": {"timestamp": {
"type": "date"
}}
}
}})
requests.put(self.elastic_index_url, data=mapping, timeout=3)
except Exception as ex:
ElasticHandler.write_es_access_log('warn', 'ElasticHandler _make_elk_index error. msg:%s' % ex.message)

def _start_worker(self):
if ElasticHandler._log_worker is not None and ElasticHandler._log_worker.is_alive():
return

ElasticHandler._log_worker = ElasticLogWorker(self.elastic_msg_url)
ElasticHandler._log_worker.start()
self._make_elk_index()

def format(self, record):
try:
self.sequence += 1
record_dict = {
'timestamp': datetime.fromtimestamp(record.created).isoformat()[:-3],
'sequence': self.sequence,
'source': self.source_ip,
'log_id': self.log_id
}
for key in ['created', 'levelname', 'levelno', 'lineno', 'module', 'msecs', 'name', 'process', 'thread']:
record_dict[key] = getattr(record, key)

match = re.search(r'(.*?)', record.html, re.DOTALL)
if match:
record_dict["levelname"] = match.group(1)

record_dict["traceback"] = ''
if record_dict.get('levelno', 0) > 20:
match = re.search(r'
}
]

Raises:
None.

Examples:
filePath = "C:/Users/c00223425/Documents/test/InspectorResult_20160316170136.zip"
file = ParseInspectFile(filePath)
info = file.getAllResults()

"""
return self.results
def getFailResult(self):
"""get inspect fail results

Args:

Returns:
List, the element is a dictionary:
[
{
Original_info :
Check_method : Step 1 Log in to the device as the admin user. Step 2 Run the following command: show controller general.
Check_result : by
Inspect_item : 'frame status'
Check_criteria : All controllers are online, Health Status is Normal and Running Status is Online, which is normal. Other conditions are abnormal.
Recovery_suggestion : 1 If the power status is abnormal, please refer to the case processing. 2 If you have any questions, please contact your technical support engineer.
Original_info : show controller general

Controller : 0A
Health Status : Normal
Running Status : Online
CPU : Intel 6core 2.1GHz *1
Location : CTE0.A
Role : Slave
Cache Capacity : 32.000GB
CPU Usage(%) : 2
admin:/>
}
]
Raises:
None.

Examples:
filePath = "C:/Users/c00223425/Documents/test/InspectorResult_20160316170136.zip"
parseFiles = ParseInspectFile(filePath)
info = parseFiles.getFailResult()

"""
allInfo = self.results
failInfo = []
for item in allInfo:
if 'check_result' in item:
if re.search(r'不通过|Not Passed', item['check_result']):
failInfo.append(item)
return failInfo
======================================================================================================================
PureStorage ::

#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
PureStorage business object
Author: liruiqi 00355383 2018-10-15 16:53:20
"""

import purestorage
from UniAutos.Log.BaseLogger import BaseLogger
from UniAutos.Util.Units import Units


class PureStorage(object):

def __init__(self, ip_address, username, password):
"""Initialize the PureStorage object

Args:
Ip_address (str): ip information
Username (str): login username
Password (str): login password

"""
self.logger = BaseLogger('pure storage')
self.logger.info('Pure Storage login ip: %s, username:%s, password:%s' % (ip_address, username, password))
self.array = purestorage.FlashArray(ip_address, username, password)

def get_volume_space(self, volume_name):
"""Get SPACE information for a single VOLUME

Args:
Volume_name (str): volume name

Returns:
space_info (dict):
{u'size': '10.0GB', u'name': u'01_vd_8k', u'system': None, u'snapshots': 0, u'volumes': '154.721679688MB',
u'data_reduction': 6.207451671999644, u'total': '154.721679688MB', u'shared_space': None,
u'thin_provisioning': 0.905712890625, u'total_reduction': 65.83563451193822}

"""
space_info = self.array.get_volume(volume_name, space='true')
space_info['volumes'] = self.convert_space_unit(space_info['volumes'])
space_info['size'] = self.convert_space_unit(space_info['size'])
space_info['total'] = self.convert_space_unit(space_info['total'])
self.logger.info('The SPACE information of VOLUME[%s] is：%s' % (volume_name, space_info))
return space_info

def get_volumes_space(self):
"""Get SPACE information for each VOLUME

Returns:
space_info (dict):
{u'size': '10.0GB', u'name': u'01_vd_8k', u'system': None, u'snapshots': 0, u'volumes': '154.721679688MB',
u'data_reduction': 6.207451671999644, u'total': '154.721679688MB', u'shared_space': None,
u'thin_provisioning': 0.905712890625, u'total_reduction': 65.83563451193822}

"""
space_infos = self.array.list_volumes(space='true')
for space_info in space_infos:
space_info['volumes'] = self.convert_space_unit(space_info['volumes'])
space_info['size'] = self.convert_space_unit(space_info['size'])
space_info['total'] = self.convert_space_unit(space_info['total'])
self.logger.info('The SPACE information for each VOLUME is：\n%s' % space_infos)
return space_infos

def get_system_space(self):
"""Get the SPACE information of the array

Returns:
space_info (dict):
{u'parity': 1.0, u'capacity': '11.1653411865TB', u'provisioned': '10.0GB', u'hostname': u'sanscont',
u'system': 0, u'snapshots': 0, u'volumes': '154.721679688MB', u'data_reduction': 1.0, u'total': '965.5MB',
u'shared_space': '810.778320312MB', u'thin_provisioning': 0.905712890625,
u'total_reduction': 10.605903676851373}

"""
space_info = self.array.get(space='true')[0]
space_info['capacity'] = self.convert_space_unit(space_info['capacity'])
space_info['volumes'] = self.convert_space_unit(space_info['volumes'])
space_info['total'] = self.convert_space_unit(space_info['total'])
space_info['provisioned'] = self.convert_space_unit(space_info['provisioned'])
if space_info['shared_space'] is not None:
space_info['shared_space'] = self.convert_space_unit(space_info['shared_space'])
self.logger.info('The SPACE information of the system is：\n%s' % space_info)
return space_info

def create_volume(self, volume_name, size):
self.logger.info('Create VOLUME NAME: %s, SIZE: %s' % (volume_name, size))
self.array.create_volume(volume_name, size)

def connect_host(self, volume_name, host_name):
self.logger.info('Create a mapping between VOLUME:%s and host: %s' % (host_name, volume_name))
self.array.connect_host(host_name, volume_name)

def disconnect_host(self, volume_name, host_name):
self.logger.info('Demap VOLUME:%s from host: %s' % (host_name, volume_name))
self.array.disconnect_host(host_name, volume_name)

def destroy_volume(self, volume_name):
self.logger.info('Delete VOLUME %s' % volume_name)
self.array.destroy_volume(volume_name)

def eradicate_volume(self, volume_name):
self.logger.info('Destroy VOLUME %s' % volume_name)
self.array.eradicate_volume(volume_name)

def convert_space_unit(self, space_number):
"""Convert int capacity units

Args:
Space_number (int): int capacity value

Returns:
Space_size (str): Capacity information with capacity units

"""
if space_number / 1024 < 1:
return '%s%s' % (space_number, 'B')
elif space_number / 1024 / 1024 < 1:
return Units.convert('%s%s' % (space_number, 'B'), 'KB')
elif space_number / 1024 / 1024 / 1024 < 1:
return Units.convert('%s%s' % (space_number, 'B'), 'MB')
elif space_number / 1024 / 1024 / 1024 / 1024 < 1:
return Units.convert('%s%s' % (space_number, 'B'), 'GB')
elif space_number / 1024 / 1024 / 1024 / 1024 / 1024 < 1:
return Units.convert('%s%s' % (space_number, 'B'), 'TB')


if __name__ == '__main__':
pure = PureStorage('100.148.173.125', 'pureuser', 'pureuser')
space_info = pure.get_volumes_space()
array_space_info = pure.get_system_space()
print 0
==============================================================================================
Pycharm ::

1. Place the get-pip.py file in the path C:\Python27. Open the command prompt and run the command[python C:\Python27\get-pip.py]


2. Place the requirements.txt in C:\Python27. Open the command prompt and run the command [ python –m pip install –r C:\Python27\requirement.txt]
Requirements.txt

html==1.16
pyftpdlib==1.4.0
pyvmomi==6.5.0.2017.5.post1
pyvim==0.0.21
pyyaml==3.11
requests==2.7.0
selenium==2.52.0
six>=1.10
xlrd==0.9.4
xlutils==1.7.1
xlwt==1.0.0
Ply==3.8
Pysmi==0.0.6
pysnmp==4.2.5
paramiko==2.2.1
cryptography==1.2.1
pyOpenSSL==0.15.1
chardet==2.3.0
pysftp
numpy
mysql
hdfs
pytz
xlsxwriter
Pyasn1==0.1.8



3. Download PyCharm from Rtools.
4. Install PyCharm on Windows machine.
5. Download Python (2.7.3) from Rtools.
6. Install Python on Windows machine.
7. Configure Python path variable
a. Right click on my computer icon --> click Properties. Then follow the instructions given in the image below.

b. In the above image >> edit system variable >>> Variable value >>>
Add python path and scripts path. eg: C:\Python27;C:\Python27\Scripts
Once the python path has been set, open command prompt and type python and you should be in python interpreter.
8. Place pip.ini file in the following folder -->> C:\Users\ -->> create folder name pip and place the below file in the pip folder.

9. Place the get-pip.py file in the path C:\Python27. Open the command prompt and run the command[python C:\Python27\get-pip.py]


10. Place the requirements.txt in C:\Python27. Open the command prompt and run the command [ python –m pip install –r C:\Python27\requirement.txt]


11. Download TortoiseGit from Rtools and install it.
12. Generating SSH Key.
a. Create a folder of interest in D drive (to clone the code from git).
b. Open the folder and click the right button. Choose Git Bash.
c. Use key-gen to generate the key
[Eg: ssh-keygen -t rsa -C “ABCD.EFGH@huawei.com”]

d. Login to http://10.183.61.55/profile/keys & add the SSH Key

13. Clone the code from Git Repository.
a. git clone ssh://git@10.183.61.55:81/NAS-AutoTest/CaseLib.git
b. git clone ssh://git@10.183.61.55:81/oceanstor-autotest/UniAutos.git
c. Open the folder and click the right button. Choose Git Bash.
d. Git checkout
e. Git branch ->> This should show * (It will highlight in green colour)
14. Adding UniAutos and CaseLib in Pycharm.
a. Open Pycharm -> Flie --> Open --> “Select path for UniAutos”
b. Open Pycharm --> File --> Open --> “Select patch for CaseLib”

Note: When you are adding second directory mark as below image then it will create under same project

15. Marking Directories as “Sources Root”.
In the navigation bar, Right Click on CaseLib and “Mark Directory as” --> Sources Root.
Repeat the same process for i. CaseLib/Nas
ii. UniAutos
iii. UniAutos/src/Framework/Dev/bin
iv. UniAutos/src/Framework/Dev/lib

16. Edit Configuration in Pycharm.

a. In the above image Script parameters path place the following files mainconfig.xml, testbed.xml and testset.xml files

17. Click the run script icon in pycharm and you will find authentication successful in pycharm output window. Like below shown image


========================


# Below are the important packages
import netmiko
import paramiko
import scrapy
import pandas
import selenium
import pyod
import numpy
import spacy
import matplotlib
import seaborn
import bokeh
import tensorflow
import lime
import twisted
import pywin32_system32
import IPython


# Below are the frameworks
import robot
import pytest
import behave
import lettuce











