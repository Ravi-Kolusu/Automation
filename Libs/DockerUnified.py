
DockerUnified ::

#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 抽象多租户的设备对象

版权信息: 华为技术有限公司，版权所有(C) 2014-2016

修改记录: 2018/6/12 w00401573 created

"""

import re
import os
import sys
import traceback
import datetime
from UniAutos.Util.Units import Units
from UniAutos.Device.Storage.Huawei.Unified import Unified
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos import Log


class DockerUnified(Unified):
logger = Log.getLogger(str(__file__))

def __init__(self, **kwargs):
kwargs['logStartTime'] = ""
super(DockerUnified, self).__init__(**kwargs)
self.logStartTime = self.getCurrentTime()
print self.logStartTime


def getCurrentTime(self):
result = self.controllers[0].host.run({'command':[ 'date "+%Y-%m-%d/%H:%M:%S"'], 'sessionType':'debug'})['stdout']
time = result.split("\n")[1]
return time.replace('\r', '')

def getMasterController(self):
"""get current unified master.

Returns:

"""
result = self.dispatch("sysShowCls")[0]["parser"]
master_modie_id = None
for node_id in result:
if 'role' not in result[node_id]:
continue
if result[node_id]['role'] == 'master':
master_modie_id = node_id
break

if not master_modie_id:
raise UniAutosException('Does not find master role from sys showcls, please check env')

for ctrl in self.controllers:
if ctrl.nodeId == master_modie_id:
return ctrl

raise UniAutosException('Does not find master controller according to the master node id:%s' % master_modie_id)


ValueException ::

# -*- coding: UTF-8 -*-

"""
功 能： 访问的变量值错误

版权信息：华为技术有限公司，版本所有(C)
"""

from UniAutosException import UniAutosException


class ValueException(UniAutosException):

"""
当访问的变量值不时期望值时，可以抛出此异常

Args:
msg (str): 自定义提示信息,默认值None

Returns:
ValueException 实例

Examples:
1.局部变量值不是期望值，抛出一个 ValueException 异常
代码:
if a is not "Type":
raise ValueException('a is not Type')

message值:
a is not Type
Details:
traceback information

Changes:
2015-03-18 17:00 lkf59217 创建
"""

def __init__(self, msg=None):
UniAutosException.__init__(self, msg)
