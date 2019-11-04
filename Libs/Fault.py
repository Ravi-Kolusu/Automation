#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 故障类

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2015/4/17 严旭光 y00292329 created

"""
import random
import re
import datetime
import traceback
import threading
from UniAutos.Util.Units import Units
from UniAutos import Log
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Util.Time import sleep


class Fault(object):
""" 定义设备故障

Args:
device (DeviceBase): 故障运行的设备
name (str): 故障名称
closureCodeRef (method): 故障执行代码
obj (object): 对象
parameters (dict): 故障执行代码所需要的参数
cleanupClosure (method): 故障执行完后恢复的代码

Examples:

Changes:
2015-4-17 严旭光 y00292329 Created

"""

def __init__(self, device, name, closureCodeRef, obj=None, parameters=None, cleanupClosure=None):
self.device = device
self.name = name
self.closureCodeRef = closureCodeRef
self.obj = obj
if parameters is None:
parameters ={}
self.parameters = parameters
self.cleanupClosure = cleanupClosure
self.__tiggerCount = 0
self.logger = Log.getLogger(self.__module__)
self.injectTime = None
try:
if "6.0." in self.device.controllers[0].host.softVersion:
self.injectTime = self.device.getCurrentTimeByDebug().split(' ')[0]
else:
self.injectTime = self.device.getCurrentTime().split(' ')[0]
except Exception:
self.logger.info("Get device current time fail, because system is not normal.")
self.recoverTime = None
self.faultType = self.device.getDeviceFault()

def inject(self, background=False, count=None, duration=None,
isRandom=False, randomInterval=None, fixedInterval='5M', registerCleanup=True):
"""

Args:
background (boolean): 是否后台运行，如果是就会另起线程执行故障注入代码
count (int): 执行次数，可选参数
duration (str): 执行时长，可选参数
isRandom (boolean): 执行间隔时间是随机的
randomInterval (dict): 执行间隔随机的范围，默认5分钟-60分钟{'lowerLimit':'20S', 'upperLimit':'40S'}
fixedInterval (str): 固定间隔时间，默认5分钟
registerCleanup (boolean): 是否注册

Returns:
None

Raises:
None

Examples:
1、后台注入故障代码20次
fault.inject(background=True,count=20)
2、后台注入故障5分钟，每次间隔1分钟
fault.inject(background=True,duration='5M',fixedInterval='1M')
3、注入故障5分钟，随机间隔，最小间隔1分钟，最大间隔2分钟
randomInterval = {'lowerLimit':'1M', 'upperLimit':'2M'}
fault.inject(duration='5M',isRandom=True,randomInterval=randomInterval)

Changes:
2015-04-17 y00292329 Created

"""
if randomInterval is None:
randomInterval = {}
kwargs = dict(count=count, duration=duration, isRandom=isRandom, randomInterval=randomInterval,
fixedInterval=fixedInterval)
if registerCleanup:
self.device.registerFault(self)
try:
if "6.0." in self.device.controllers[0].host.softVersion:
self.injectTime = self.device.getCurrentTimeByDebug().split(' ')[0]
else:
self.injectTime = self.device.getCurrentTime().split(' ')[0]
except Exception:
self.logger.info("Get device current time fail, because system is not normal.")
self.recoverTime = None
self.faultType.addFault(self)
# 临时加打印，定位注册Fault但未恢复的情况
self.logger.info('Register fault 【%s】 on device successfully' % self.name)
if background:
threading.Thread(target=self.__runFault, name=self.name, kwargs=kwargs)
else:
self.__runFault(**kwargs)

def __runFault(self, count=None, duration=None,
isRandom=False, randomInterval=None, fixedInterval='5M'):
"""执行故障命令

Args:
count (int): 执行次数，可选参数
duration (str): 执行时长，可选参数
isRandom (boolean): 执行间隔时间是随机的
randomInterval (dict): 执行间隔随机的范围，默认5分钟-60分钟
fixedInterval (str): 固定间隔时间，默认5分钟

Returns:
None

Raises:
InvalidParamException: 执行时长和执行次数其中一个必须被设置
InvalidParamException: 随机间隔时间有误，最小时间必须小于最大时间.

Examples:

Changes:
2015-04-17 y00292329 Created

"""
if randomInterval is None:
randomInterval = {}
if (not duration) and (not count):
raise InvalidParamException('duration or count must be set for this fault')
if duration:
matchObj = re.match(r'\d+$', duration)
if matchObj:
duration += 'S'
duration = int(Units.getNumber(Units.convert(duration, 'S')))
if isRandom:
if not randomInterval:
randomInterval['lowerLimit'] = '5M'
randomInterval['upperLimit'] = '60M'
lowerLimit, upperLimit = self.__getRandomIntervalSeconds(randomInterval)
else:
matchObj = re.match(r'\d+$', fixedInterval)
if matchObj:
fixedInterval += 'S'
fixedInterval = Units.getNumber(Units.convert(fixedInterval, 'S'))
stop = False
starttime = datetime.datetime.now()
while not stop:
self.closureCodeRef(self.parameters)
self.__tiggerCount += 1
self.logger.debug('Fault %s has been triggered %d times' % (self.name, self.__tiggerCount))
if isRandom:
sleepTime = random.randint(lowerLimit, upperLimit)
else:
sleepTime = fixedInterval
if count and self.tiggerCount >= count:
break
if duration:
current = datetime.datetime.now()
if (current - starttime).seconds >= duration:
break
if (current - starttime).seconds + sleepTime > duration:
sleepTime = duration - (current - starttime).seconds
sleep(sleepTime)

def __getRandomIntervalSeconds(self, randomInterval):
"""获取随机间隔时间的秒数

Args:
randomInterval (dict): 随机间隔的最小时间和最大时间

Returns:
lowerLimit: 最小间隔
upperLimit: 最大间隔

Raises:
InvalidParamException: 最小间隔时间大于最大间隔时间

Examples:


Changes:
2015-05-14 y00292329 Created

"""

matchObj = re.match(r'\d+$', randomInterval['lowerLimit'])
if matchObj:
randomInterval['lowerLimit'] += 'S'
lowerLimit = Units.getNumber(Units.convert(randomInterval['lowerLimit'], 'S'))
matchObj = re.match(r'\d+$', randomInterval['upperLimit'])
if matchObj:
randomInterval['upperLimit'] += 'S'
upperLimit = Units.getNumber(Units.convert(randomInterval['upperLimit'], 'S'))
if lowerLimit >= upperLimit:
raise InvalidParamException("The randomInterval values for upper and lower limits are incorrect."
"Lower limit must be less than the Upper Limit")
return lowerLimit, upperLimit

def recover(self):
"""恢复故障

Args:
None

Returns:
None

Raises:
None

Examples:
1、恢复故障
fault.recover()

Changes:
2015-04-17 y00292329 Created

"""
if self.getStatus() == 'running':
self.stop()
if self.cleanupClosure:
if self.recoverTime is None:
self.cleanupClosure(self.parameters)
try:
self.recoverTime = self.device.getCurrentTime().split(' ')[0]
except Exception:
self.logger.info("The Fault may be power down device, can not connect to device, detailt:"
"%s" % traceback.format_exc())
else:
self.logger.info('The Fault %s is already recovery at %s' % (self.name, self.recoverTime))
else:
self.logger.warn('There was no cleanup closure registered to the Fault %s' % self.name)
# 通过recoverTime来判断是否恢复
# self.device.unregisterFault(self)

def stop(self):
"""停止故障运行

Args:
None

Returns:
None

Raises:
None

Examples:

Changes:
2015-04-17 y00292329 Created

"""
pass

def getStatus(self):
"""获取故障运行的状态

Args:
None

Returns:
str: stopped/running

Raises:
None

Examples:

Changes:
2015-04-17 y00292329 Created

"""
return 'stopped'

@property
def tiggerCount(self):
"""故障执行的次数

Args:
None

Returns:
int: 故障执行次数

Raises:
None

Examples:
None

Changes:
2015-04-17 y00292329 Created

"""
return self.__tiggerCount

def getObject(self):
return self.obj
