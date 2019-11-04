#!/usr/bin/env python
# -*- coding: utf8 -*

"""
功 能：当前模块为UniAutos.Wrapper所定义的一个place holder，不同于UniAuto.Wrapper对象直接实例化注册到主机，
WrapperHolder是在第一次被用的时候才会被注册

版权信息：华为技术有限公司，版本所有(C) 2014-2015

"""


class WrapperHolder(object):
""" 定义WrapperHolder类，用于保存UniAutos.wrapper类，
-直到wrapper对象的方法被调用才会实例化wrapper对象
"""

def __init__(self, requireCodRef, wrapperType, deviceObj ):
"""WrapperHolder构造函数，创建一个WrapperHolder对象

Args:
requireCodRef (func) : 创建Wrapper对象的回调函数
wrapperType (str) : wrapper类型
deviceObj (UniAutos.Device.HostBase) : 注册wrapper的主机对象

Attributes:
requireCodRef(func) - 创建Wrapper对象的回调函数
wrapperType(Str) - wrapper类型
deviceObj(HostObj) - 注册wrapper的主机对象
realWrapper(WrapperObj) - 实例化的wrapper对象

Returns:
wrapperHolder对象

Raises:
None

Examples:
def adminCliReq():
from UniAutos.Wrapper.Tool.AdminCli import AdminCli
return AdminCli()
hostObj.registerToolWrapper(hostObj, wrapper_type='UniAutos.Wrapper.Tool.AdminCli', require=adminCliReq)

"""
self.requireCodRef = requireCodRef
self.wrapperType = wrapperType
self.deviceObj = deviceObj
self.realWrapper = None

def __getattr__(self, item):
"""重写Object积累的__getattr__方法以保证对象初始化时自动化调用replaceWithRealWrapper方法

Input:
None

Returns:
None

Raises:
None

"""
replacedWapperObj = self.replaceWithRealWrapper()
return getattr(replacedWapperObj, item)

def replaceWithRealWrapper(self):
"""WrapperHolder构造函数，创建一个WrapperHolder对象

Input:
None

Returns:
None

Raises:
None

"""
if not self.realWrapper:
wrapperObj = self.requireCodRef()
wrappers = self.deviceObj.getWrapper()
flag = False
for wrapperDict in wrappers:
if 'wrapper_type' in wrapperDict and wrapperDict['wrapper_type'] == self.wrapperType:
wrapperDict['wrapper'] = wrapperObj
wrapperDict['require'] = 1
flag = True
break
if not flag:
raise Exception('Could not automatically invoke the wrapper class:%s' % self.wrapperType)
wrapperObj.setDevice(self.deviceObj)
self.realWrapper = wrapperObj
return wrapperObj
else:
return self.realWrapper
