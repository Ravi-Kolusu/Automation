#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能: wrapper中tool部分的基类
"""

from UniAutos.Wrapper.WrapperBase import WrapperBase
from UniAutos.Util.TypeCheck import validateParam
from UniAutos import Log
import re

class ToolBase(WrapperBase):
"""wrapper的tool基类

Args:
params (dict): 此处仅关注key: retry

Attributes:
logger (obj): 一个日志对象，用于记录日志
retry (dict): 命令执行失败后是否重试的重试信息
method_release_requirement (list): 释放时需要执行的方法列表
user_retry_codes (list): 用户自定义的需要重试的字符串列表

Returns:
None

Raises:
None

Examples:
None

"""
def __init__(self, params=None):
super(ToolBase, self).__init__(params)
self.logger = Log.getLogger(__name__)
def tmpmethod(param):
return 0
self.retry = {"criteria": tmpmethod, "count": 0, "interval": '10 S'}
if params and "retry" in params:
self.retry = params["retry"]
self.retry["user_criteria"] = tmpmethod
self.methodReleaseRequirement = []
self.userRetryCodes = []


def setRetry(self, userRetryCodes=[]):
"""设置用于检测是否需要重试的检测字符串

Args:
userRetryCodes (list): 检测字符串列表

Returns:
None

Raises:
None

Examples:
None

"""
if userRetryCodes:
self.userRetryCodes = userRetryCodes

def userCriteria(info):
"""通过回显信息info，检测执行是否成功，并能通过用户指定的检测字符串的检测

Args:
info (dict): {"rc": "", "stderr": "", "stdout": ""}

Returns:
0/1: 执行成功返回0，失败返回1

Raises:
None

Examples:
None

"""
retryCodes = self.userRetryCodes
result = 0
if info:
result = info.pop("rc")
if result != 0:
for key in info.keys():
output = info[key]
for line in output:
for retryError in retryCodes:
matcher = re.match(retryError, line)
if matcher:
self.logger.debug("the following error was returned:\n %s\nretrying command." %line)
return 1
return 0
return 0

if hasattr(self, "retry"):
self.retry["user_criteria"] = userCriteria
pass

def restoreRetry(self):
"""设置默认的重试方法

Args:
None

Returns:
None

Raises:
None

Examples:
None

"""
def retryCodes():
return 0
if hasattr(self, "retry") and hasattr(self.retry, "user_criteria"):
self.retry["user_criteria"] = retryCodes
pass

def deadObjectCheck(self, regexStr):
def check(info):
if "stderr" in info:
matcher = re.match(regexStr, info["stderr"])
if matcher:
return 1
if "stdout" in info:
matcher = re.match(regexStr, info["stdout"])
if matcher:
return 1
return 0

return check

def can(self, methodName):
"""检查方法methodName是否存在，存在就返回方法的引用

Args:
methodName (str): 方法的名称

Returns:
None/方法的引用: methodName对应的方法存在时返回方法的引用，不存在就返回None

"""
dev = self.getDevice()
if not dev:
if hasattr(self, methodName):
return eval("self."+methodName)

if methodName not in self.methodReleaseRequirement:
if hasattr(self, methodName):
return eval("self."+methodName)

if hasattr(self, methodName):
return eval("self."+methodName)
