#!/usr/bin/python
# -*- coding: UTF-8 -*-

import datetime
import threading
import re
import sys
import importlib
import traceback

from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.ObjectNotFoundException import ObjectNotFoundException
from UniAutos.Exception.PropertyException import PropertyException
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.InvalidParamException import InvalidParamException

from UniAutos import Log
from UniAutos.Util.WrapperHolder import WrapperHolder
from UniAutos.Device.DeviceBase import DeviceBase
from UniAutos.Wrapper.Api.ApiBase import ApiBase
from UniAutos.Wrapper.Tool.Selenium.UniWebBase import UniWebBase
from UniAutos.Util.Units import Units, SECOND
from UniAutos.Wrapper.Api.VmwareBase import VmwareBase
from UniAutos.Util.Time import sleep
from UniAutos.Util.Codec import getFormatString
from UniAutos.Wrapper.Template.CLI import CliWrapper
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import Adapter
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import CmdMapping

# NewWrapper = True
NewWrapper = False


class Dispatcher(object):
"""命令分发器,所有下发到设备的命令都会经由分发器，选择合适的Wrapper来执行
Wrapper分为：
CLI - Command Line Interface命令行接口模式
API - 通过API远程调用，比如Rest，Vmware SDK，etc.

Changes:
2015-06-01 y00292329 Created

"""

validateParamsFlag = False

ignoreDispatchPauseLock = False

# 操作allowTid的锁
__allDispatchLock = threading.Lock()
# 标记只允许下发命令的线程id
__allowTid = -1

def __init__(self):
"""Dispatcher命令下发的构造器，一般情况下作为Device Class类的基类。

Examples:
from UniAutos.Dispatcher import Dispatcher
class HostBase(Dispatcher)
...

"""
self.original_wrapper_list = []
self.wrapper_list = []
self._pauseDispatches = dict()
self._dispatchesInProgress = dict()
self._pauseDispatches['until'] = None
self.logger = Log.getLogger(__name__)
self.highPriorityView = dict()
# 操作allowTid的锁
self.__allDispatchLock = threading.Lock()
# 标记只允许下发命令的线程id
self.__allowTid = -1

@property
def dispatchesInProgress(self):
return self._dispatchesInProgress

def registerToolWrapper(self, host, wrapper=None, wrapper_type=None, require=None):
"""注册Wrapper,可以直接传递一个Wrapper对象，也可以传递一个函数，该函数可以生成一个Wrapper对象。

Args:
host (Host): Wrapper所属的主机

**下面参数必须二选一
wrapper (Wrapper): Wrapper对象
wrapper_type (str): Wrapper的类型

**如果wrapper_type被赋值，则require必须使用
require (function): 生成Wrapper的代码

Examples:
1. dispatcherClass.registerToolWrapper(host, wrapper=adminCliWrapper)
2. def requireFunc(params):
return AdminCli(params)
dispatcherClass.registerToolWrapper(host, wrapper_type='UniAutos.Wrapper.Tool.AdminCli.AdminCli'
require=requirFunc)

"""

wrapperDictInfo = {}
for hostWrapperPair in self.wrapper_list:
hostWrapper = hostWrapperPair["wrapper"]
wrapperClassName = hostWrapper.__module__ + '.' + hostWrapper.__class__.__name__
# if (wrapper_type is not None and wrapper_type == wrapperClassName) or \
# 修改判断方式，通过hostWrapperPair['wrapper_type']获取wrapper_type
if (wrapper_type is not None and wrapper_type == hostWrapperPair['wrapper_type']) or \
(wrapper is not None and wrapper.__module__ + '.' + wrapper.__class__.__name__ == hostWrapperPair[
'wrapper_type']):
self.logger.debug('The test script requested to re-register the wrapper: ' +
wrapperClassName + '\n but is was already registered')
return
if wrapper is not None:
wrapperDictInfo['require'] = 1
wrapperDictInfo['wrapper'] = wrapper
wrapperDictInfo['host'] = host
wrapperDictInfo["wrapper_type"] = wrapper.__module__ + '.' + wrapper.__class__.__name__
if isinstance(self, DeviceBase):
wrapper.setDevice(self)
else:
wrapperDictInfo['require'] = 0
# TODO Wrapper holder
wrapperDictInfo['wrapper'] = WrapperHolder(require, wrapper_type, host)
wrapperDictInfo['host'] = host
wrapperDictInfo["wrapper_type"] = wrapper_type
self.wrapper_list.append(wrapperDictInfo)

self.original_wrapper_list = self.wrapper_list

def getWrapper(self, wrapperClassName=None):
"""获取注册在这个Dispatcher上的wrapper/host对象

Args:
wrapperClassName (Str) : (可选参数)Wrapper Class Str，例如：AdminCli

Returns:
if wrapperClassName is specified, then returned the wrapper dict info
otherwise it returns the whole wrapper list
{ 'wrapper' : wrapperObject, 'host' : hostObject, 'wrapper_type' : classString, 'required' : boolean, 'require' : codeRefs}
{ 'wrapper' : wrapperObject, 'host' : hostObject, 'wrapper_type' : classString, 'required' : boolean, 'require' : codeRefs}
...

Raises:
UniAutosException

Examples:
None

"""

if wrapperClassName:
for wrapperinfoDict in self.wrapper_list:
if 'wrapper' in wrapperinfoDict:
fullName = wrapperinfoDict['wrapper'].__module__ + '.' + wrapperinfoDict[
'wrapper'].__class__.__name__
if re.match(r'UniAutos\.Wrapper\.(Tool|Api)(\.\w+)*' + wrapperClassName + '(\.\w+)*',
fullName,
re.IGNORECASE):
return wrapperinfoDict
elif 'wrapper_type' in wrapperinfoDict:
if re.match(r'UniAutos\.Wrapper\.(Tool|Api)(\.\w+)*' + wrapperClassName + '(\.\w+)*',
wrapperinfoDict['wrapper_type'],
re.IGNORECASE):
return wrapperinfoDict

raise UniAutosException("Unable to find the requested wrapper:['%s'] in the test bed. "
"Please verify the test bed is correct.\n"
"Current Wrapper list:\n %s" %
(wrapperClassName, getFormatString(self.wrapper_list)))

return self.wrapper_list

def dispatch(self, methodName, wrapperParamsDict=None, interactRule=None, option=None):
"""找到一个配置的Tool Wrapper去执行所对应的方法，调用该方法，并且返回相应的结果

Args:
methodName(String): Tool wrapper方法的名字
wrapperParamsDict(Dict): wrapper方法所用的方法参数

Returns:
ret(List): 一个包含多个Dict的List，以下所对应的Key-Value

rc : 返回命令所退出的Integer值，典型的一个非零的返回值就意味着整个命令失败了，反之成功
stdout : List, 包含命令返回回来的命令回显列表
stderr : List, 可选返回值，包含命令返回回来的命令错误回显列表
parsed : Dict, 可选返回值，包含解析之后的标准输出stdout的回显

Raises:
UniAutos.Exception.UniAutosException

Examples:
dispatcher.dispatch(methodName, methodParams)

"""
if wrapperParamsDict is None:
wrapperParamsDict = dict()
if interactRule is None:
interactRule = dict()
if option is None:
option = dict()
if NewWrapper:
if methodName.find("_") == -1:
newName = CmdMapping.WrapperHash.get(methodName, None)
if newName:
if isinstance(newName, dict):
extra = newName.get("extra", {})
wrapperParamsDict.update(extra)
func = Adapter.__dict__.get(newName["method"])
newName, wrapperParamsDict = func(wrapperParamsDict)
return self.runNewWrapper(newName, wrapperParamsDict, interactRule, option)
else:
return self.runNewWrapper(methodName, wrapperParamsDict, interactRule, option)
else:
if methodName.find("_") != -1:
return self.runNewWrapper(methodName, wrapperParamsDict, interactRule, option, 1)
else:
return self.__dispatchCommon(methodName, 1, wrapperParamsDict)

def runNewWrapper(self, methodName, params, interactRule=None, option=None, interrupt=0):
"""
Changes:
2016-05-10 y00292329 Created

"""
dispatching = None
try:
if interrupt != 0:
dispatching = self.markAsDispatching()
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
result = cliWrapper.runWrapper(methodName, params, interactRule, option)
return [result]
finally:
if dispatching:
dispatching()

def setCliWrapperConf(self, option):
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
cliWrapper.setOption(option)

def getClassPropertyDispatch(self, componentClass, propertiesList=None):
"""检索业务类的属性(如果没有给定要检索的属性，则检索所有属性)

Args:
componentClass (type): 业务类型
propertiesList (list): 需要检索的属性

Returns:
propsSetLists(List) - Properties array, include the prop dict returned from
[{
idProp : id,
prop1 : val1,
prop1 : val2,
...
}
...
]

Raises:
UniAutosException

Examples:
#cls为component的class名的字符串
#properties为需要获取的属性列表
unifiedDevice.getClassPropertyDispatch(cls, properties)

"""

allProps = False

if not propertiesList:
allProps = True
propertiesList = []

propertiesDict = {}
for prop in propertiesList:
propertiesDict[prop] = 1

propsSetLists = []
for twInfoDict in self.wrapper_list:
wrapperObj = twInfoDict['wrapper']
hostObj = twInfoDict['host']
if NewWrapper:
wrapperList = filter(
lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
temp = self.createWrapperParams(componentClass.__module__ + '.' + componentClass.__name__, "show")
result = cliWrapper.runWrapper(temp.get("methodName"), temp.get("params", {}))
info = result.get('parser', {})
propInfoDict = {'propSets': [info], "properties": propertiesList}
else:
# propInfoDict = self.__getPropertyDispatchTw(componentClass, wrapperObj, compObject, propertiesList, hostObj)
propInfoDict = self.__getPropertyDispatchTw(componentClass, wrapperObj, hostObj=hostObj,
propertiesList=propertiesDict.keys(), )
for propsDict in propInfoDict['propSets']:
propsSetLists.extend(propsDict.values())

for props in propInfoDict['properties']:
if props in propertiesDict:
del propertiesDict[props]

if len(propertiesDict) == 0:
break

if not allProps and len(propertiesDict) > 0:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' + wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('THe following properties for %s could not be '
'retrieved from any of configured tool wrappers (%s): %s'
% (componentClass, ','.join(wrappers), ','.join(propertiesDict.keys())))

return propsSetLists

def syncClassDispatch(self, componentClass, criteriaDict=None, syncParamsDict=None, device=None, ):
"""使用Tool Wrappers同步更新这个类别里面所有对象实例的properties

Args:
componentClass(String): Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
criteriaDict(Dict): 根据同步的对象属性Dict和过滤的Dict进行匹配
syncParamsDict(Dict): 需要同步的参数属性Dict
device(UniAUtos.Device): UniAutos Device 对象

Returns:
returnDict(Dict): 获得相应的Wrapper对象

Raises:
UniAutos.Exception.UniAutosException

"""

if not syncParamsDict:
syncParamsDict = {}
classes = []
candidateKeys = componentClass.getCandidateKeys()

searchKeys = candidateKeys
if criteriaDict is not None:
for critProp in criteriaDict.keys():
if critProp not in searchKeys:
searchKeys.append(critProp)

propInfoDict = {}
twInfoDict = {}
if NewWrapper:
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
propInfoDict = self.createPropertyInfoHash(componentClass, searchKeys)
twInfoDict = wrapperList[0]
else:
for wrapperDict in self.wrapper_list:
wrapperObj = wrapperDict['wrapper']
if wrapperDict['wrapper'].getDevice is None:
if (isinstance(self, DeviceBase)):
wrapperDict['wrapper'].setDevice(self)
propInfoDict = wrapperObj.createPropertyInfoHash(componentClass, searchKeys)
loopBreak = False
if criteriaDict is not None:
for prop in criteriaDict:
if prop not in propInfoDict:
loopBreak = True
break
if loopBreak:
continue
twInfoDict = wrapperDict
break
else:
if propInfoDict:
twInfoDict = wrapperDict
break
else:
continue
if twInfoDict is None:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' \
+ wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('None of the configured tool wrappers (%s) supply '
'any of the defined identifier properties (%s) '
'for %s.' % (','.join(wrappers), ','.join(searchKeys), componentClass))

host = twInfoDict.get('host')
wrapper = twInfoDict.get('wrapper')

methodDict = {}
partial = False
if NewWrapper:
result = propInfoDict.get("show")
if isinstance(result, dict):
params = result.get("extra", {})
if result.get("method").startswith("adapter"):
methodName, params = Adapter.__dict__.get(result["method"])(params)
else:
methodName = result.get("method")
syncParamsDict.update(params)
partial = result.get("partial", False)
else:
methodName = result
methodDict = {"methdName": methodName}
else:
for propValue in propInfoDict.values():
if propValue.has_key('getmethod'):
funcId = propValue['getmethod']
if not methodDict.has_key(funcId):
methodDict[funcId] = funcId
if not syncParamsDict:
classObj = wrapper.getCommonPropertyInfo(propValue['getmethod'], searchKeys)
classes.extend(classObj)

if len(classes) == 0:
classes.append(componentClass.__module__ + '.' + componentClass.__name__)

# threadLock here for all classes
threadComponentClassLocks = []
try:
for klass in classes:
device.threadComponentClassLock(klass)
threadComponentClassLocks.append(klass)
newCriteriaDict = {}
optionKeys = candidateKeys + componentClass.getOptionKeys()

fullFind = True

if criteriaDict is not None:
for criteriaKey in criteriaDict.keys():
if type(criteriaDict[criteriaKey]).__name__ in ['str', 'bool', 'int', 'float']:
if (criteriaKey in optionKeys):
newCriteriaDict[criteriaKey] = criteriaDict[criteriaKey]

if len(newCriteriaDict) != 0:
if 'options' not in syncParamsDict:
syncParamsDict['options'] = []
syncParamsDict['options'].append(newCriteriaDict)
else:
tempKeys = componentClass.getCandidateKeys()
if criteriaDict:
for criteriaKey in criteriaDict.keys():
if (criteriaKey in tempKeys):
if 'options' not in syncParamsDict:
syncParamsDict['options'] = []
syncParamsDict['options'].append(criteriaKey)

twProps = []
for methodName in methodDict.values():
runWrapperParams = {}
if host is not None:
runWrapperParams['host'] = host
runWrapperParams['wrapper'] = wrapper
ret = self.__callWrapper(runWrapperParams, methodName, syncParamsDict, 1)

for result in ret:
twProps.extend(result['parser'].values())
if result.get("partial", False) or partial:
fullFind = False
return {'properties': twProps,
'classes': classes,
'full_find': fullFind,
'thread_locks': threadComponentClassLocks}
except Exception as e:
self.logger.info(traceback.format_exc())
for name in threadComponentClassLocks:
device.threadUnlock(name)
raise e

def getPropertyDispatch(self, compObject, propertiesList):
"""为相应的Component对象通过查询所配置的Tool Wrappers获取所需要的属性,直到所有属性被查询到

Args:
compObject(UniAUtos.Component.ComponentBase): UniAutos Component对象
propertiesList(List): 所想要得到的属性列表

Returns:
objPropsDict(Dict): 获得对应对象的属性Dict

Raises:
UniAutos.Exception.UniAutosException

Examples:
dispatcher.getPropertyDispatch(self, properties)

"""

allProps = False
if propertiesList is None:
propertiesList = []
if not propertiesList:
allProps = True

propertiesDict = {}
for prop in propertiesList:
propertiesDict[prop] = 1

componentClass = compObject.__module__ + "." + compObject.__class__.__name__

objPropsDict = {}
for twInfoDict in self.wrapper_list:
wrapperObj = twInfoDict['wrapper']
hostObj = twInfoDict['host']
if NewWrapper:
wrapperList = filter(
lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
temp = self.createWrapperParams(componentClass, "detail")
params = {}
for k, v in temp.get("paramsName").items():
params[k] = compObject.properties.get(v, "")
params.update(temp.get("params", {}))
result = cliWrapper.runWrapper(temp.get("methodName"), params)
info = result.get('parser', {})
propInfoDict = {'propSets': [info], "properties": propertiesList}
else:
propInfoDict = self.__getPropertyDispatchTw(componentClass, wrapperObj, compObject, propertiesList,
hostObj)

for propSetDict in propInfoDict['propSets']:
propsDict = None
if len(propSetDict.keys()) == 1:
propsDict = propSetDict.values()[0]
else:
for key in compObject.getCandidateKeys():
if not compObject.isClean([key]):
compObject.getProperty(key)
if compObject.isClean([key]):
keyVal = compObject.getProperty(key)
if keyVal in propSetDict:
propsDict = propSetDict.get(keyVal)
break
if not propsDict:
wrapperName = compObject.__module__ + '.' + compObject.__class__.__name__
objectName = compObject.__module__ + '.' + compObject.__class__.__name__
msg = 'Failed to detect which candidate key is used for ' + \
wrapperName + ' for ' + objectName + '\'s properties'

candidateKeys = compObject.getCandidateKeys()
msg = msg + "\nResult of the wrapper call:\n" + getFormatString(propInfoDict)
msg = msg + "\nAll the properties that exist on this object already\n" + getFormatString(
compObject.properties)
msg = msg + "\nCandidate Keys tried:\n" + getFormatString(candidateKeys)
raise PropertyException(msg)
objPropsDict = dict(propsDict, **objPropsDict)

for props in propInfoDict['properties']:
if props in propertiesDict:
del propertiesDict[props]

if NewWrapper or (not allProps and len(propertiesDict) == 0):
break

if not allProps and len(propertiesDict) > 0:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' \
+ wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('The following properties for %s could not be '
'retrieved from any of configured tool wrappers (%s): %s'
% (compObject.classFullName,
','.join(wrappers),
','.join(propertiesDict.keys())))

return objPropsDict

def setPropertyDispatch(self, compObject, propertiesDict):
"""为相应的Component对象通过查询所配置的Tool Wrappers设置属性的值,直到所要求的属性被设置

Args:
compObject(UniAutos.Component.ComponentBase): Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
propertiesDict(Dict): 需要被设置的属性Dict，包含属性的Key-Value

Returns:
objPropsDict(Dict): 获得被设置的对象属性Dict

Raises:
UniAutos.Exception.UniAutosException

Examples:
dispatch.setPropertyDispatch(self, properties)

"""

parsedDict = {}
if NewWrapper:
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
componentClass = compObject.__module__ + '.' + compObject.__class__.__name__
temp = self.createWrapperParams(componentClass, "update")
params = {}
for k, v in temp.get("paramsName").items():
params[k] = compObject.properties.get(v, "")
params.update(propertiesDict)
ret = cliWrapper.runWrapper(temp.get("methodName"), params)
compObject.markDirty(propertiesDict.keys())
return parsedDict

for twInfoDict in self.wrapper_list:
wrapperObj = twInfoDict['wrapper']
propsNameList = propertiesDict.keys()
if wrapperObj.getDevice is None:
if isinstance(self, DeviceBase):
wrapperObj.setDevice(self)

className = compObject.__module__ + '.' + compObject.__class__.__name__
twPropertyDict = wrapperObj.createPropertyInfoHash(className, propsNameList)

methodDict = {}
for props in propsNameList:
if twPropertyDict.has_key(props) and twPropertyDict[props].has_key('setmethod'):
funcId = twPropertyDict[props]['setmethod']
if funcId not in methodDict:
methodDict[funcId] = dict()
methodDict[funcId]['method'] = funcId
if 'properties' not in methodDict[funcId]:
methodDict[funcId]['properties'] = list()
methodDict[funcId]['properties'].append(props)

for funcId in methodDict.keys():
method = methodDict[funcId]['method']
setPropsList = methodDict[funcId]['properties']
setParamDict = {'object': compObject}

for setProp in setPropsList:
setParamDict[setProp] = propertiesDict[setProp]

runWapperParamsDict = {}
if 'host' in twInfoDict and twInfoDict['host']:
runWapperParamsDict['host'] = twInfoDict['host']
runWapperParamsDict['wrapper'] = twInfoDict['wrapper']

retList = self.__callWrapper(runWapperParamsDict, method, setParamDict, 1)
del setParamDict['object']

compObject.markDirty(setParamDict.keys())

if (retList[0].has_key('parser')):
retDict = retList[0].values()

for key in retDict.keys():
parsedDict[key] = retDict[key]

cleanPropsDict = {}

for setProps in setParamDict.keys():
if retDict[setProp] is not None:
cleanPropsDict[setProp] = retDict[setProp]

compObject.markClean(cleanPropsDict)

for setProps in setPropsList:
del propertiesDict[setProps]

if len(propertiesDict) == 0:
break

if len(propertiesDict) > 0:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' \
+ wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('The following properties for %s could not be '
'set via any of configured tool wrappers (%s): %s'
% (compObject.classFullName,
','.join(wrappers),
','.join(propertiesDict.keys())))

return parsedDict

def getDispatchInfo(self, methodName, wrapperParamsDict={}):
"""遍历Wrapper列表，根据Wrapper的方法名和Wrapper方法的参数得到相应的Wrapper对象

Args:
methodName(String): Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
wrapperParamsDict(Dict): Wrapper方法的参数字典

Returns:
returnDict(Dict): 获得相应的Wrapper对象

"""
for wrapperDict in self.wrapper_list:
if hasattr(wrapperDict['wrapper'], methodName):
returnDict = {'wrapper': wrapperDict['wrapper']}
if 'host' in wrapperDict and wrapperDict['host']:
returnDict['host'] = wrapperDict['host']
returnDict['command'] = wrapperDict['host'].getCmdObj
return returnDict

def __dispatchCommon(self, methodName, interrupt, wrapperParamsDict={}):
"""该方法被用于调用wrapper dispatch方法，普通wrapper分发调用

Args:
methodName (String) : 工具Wrapper的方法名称
interrupt (Boolean) : 使Wrapper方法能被后台调用
wrapperParamsDict (Dict) : Wrapper方法的参数字典

Returns:
ret(List): 一个包含多个Dict的List，以下所对应的Key-Value
{
'rc' (Integer) : 命令执行后的范围值，通常情况下非零的rc表示命令有错
'stdout' (List) : 命令的标准输出，将每行作为一个数组的元素并且返回数组
'stderr' (List) : 命令的标准错误，将每行作为一个数组的元素并且返回数组
'parsed' (Dict) : 命令回显解析之后的字典格式
}

Raises:
UniAutos.Exception.UniAutosException

Changes:
2015-06-01 y00292329 Created

"""

Dispatcher.validateParamsFlag = True
wrapperInfoDict = self.getDispatchInfo(methodName, wrapperParamsDict)
Dispatcher.validateParamsFlag = False

if wrapperInfoDict is None or 'wrapper' not in wrapperInfoDict:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' + wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise InvalidParamException('None of the configured wrappers (%s) provide '
'the requested method (%s) with your input parameters '
'(%s). Any errors will be shown in a debug meessage right'
' before this exception'
% (','.join(wrappers), methodName, getFormatString(wrapperParamsDict.keys())))

runWrapperParams = {}
if 'host' in wrapperInfoDict and wrapperInfoDict['host']:
runWrapperParams['host'] = wrapperInfoDict['host']
runWrapperParams['wrapper'] = wrapperInfoDict['wrapper']
if wrapperInfoDict['wrapper'].getDevice is None:
if isinstance(self, DeviceBase):
wrapperInfoDict['wrapper'].setDevice(self)

return self.__callWrapper(runWrapperParams, methodName, wrapperParamsDict, interrupt)

def activateCan(self, can, wrapperObj, wrapperParamsDict=None):
"""Activate Can method in wrapper object with the wrapper parameters

Args:
can (String) : 工具Wrapper的方法名称
wrapperObj (Wrapper Object) : 工具Wrapper的方法名称
wrapperParamsDict (Dict) : Wrapper方法的参数字典

Returns:
ret(List): 一个包含多个Dict的List，以下所对应的Key-Value
{
'rc' (Integer) : 命令执行后的范围值，通常情况下非零的rc表示命令有错
'stdout' (List) : 命令的标准输出，将每行作为一个数组的元素并且返回数组
'stderr' (List) : 命令的标准错误，将每行作为一个数组的元素并且返回数组
'parsed' (Dict) : 命令回显解析之后的字典格式
}

Raises:
UniAutos.Exception.UniAutosException

"""

if re.search("instancemethod", str(type(can))):
if wrapperParamsDict:
ret = can(wrapperParamsDict)
else:
ret = can()
else:
ret = can(wrapperObj, wrapperParamsDict)

if isinstance(ret, dict):
ret = [ret]
return ret

def __callWrapper(self, runWrapperParamsDict, methodName, wrapperParamsDict={}, interrupt=0):
"""该方法被用于调用wrapper

Args:
runWrapperParamsDict (Dict) : wrapper参数字典
-包含以下key-values:
host (UniAutos.Device.Host) : 主机对象，能够调用执行wrapper方法
wrapper (UniAutos.Wrapper) : wrapper对象
methodName (String) : 工具Wrapper的方法名称
wrapperParamsDict (Dict) : Wrapper方法的参数字典
interrupt (Boolean) : 使Wrapper方法能被后台调用

Returns:
ret(List): 一个包含多个Dict的List，以下所对应的Key-Value
{
'rc' (Integer) : 命令执行后的范围值，通常情况下非零的rc表示命令有错
'stdout' (List) : 命令的标准输出，将每行作为一个数组的元素并且返回数组
'stderr' (List) : 命令的标准错误，将每行作为一个数组的元素并且返回数组
'parsed' (Dict) : 命令回显解析之后的字典格式
}

Raises:
UniAutos.Exception.UniAutosException

Examples:
None

"""

curWrapper = runWrapperParamsDict['wrapper']
if isinstance(curWrapper, WrapperHolder):
specifiedType = curWrapper['wrapper_type']
classNameList = specifiedType.split('.')
className = classNameList.pop()
module = ".".join(classNameList)
__import__(module)
moduleClass = getattr(sys.modules[specifiedType], className)
for wrapper in self.wrapper_list:
if isinstance(wrapper, moduleClass):
curWrapper = wrapper

ret = []
dispatching = None
if interrupt != 0:
dispatching = self.markAsDispatching()

try:
wrapperClassNm = '%s.%s' % (curWrapper.__module__, curWrapper.__class__.__name__)
self.logger.debug("Running: %s\nMethod: %s\nWith params: %s" %
(wrapperClassNm, methodName, getFormatString(wrapperParamsDict)))

if isinstance(curWrapper, ApiBase):
can = curWrapper.can(methodName)
if can is None:
raise CommandException(
"Invalid method name '%s' specified for wrapper '%s'" % (methodName, wrapperClassNm))

if isinstance(curWrapper, VmwareBase):
timeSpan = datetime.datetime.now() - curWrapper.connectedTime
if Units.compareTime(str(timeSpan.seconds) + 'S', '20M') >= 0:
curWrapper.disConnect()
curWrapper.connect()
curWrapper.connectedTime = datetime.datetime.now()

ret = self.activateCan(can, curWrapper, wrapperParamsDict)
self.logger.cmdResponse(getFormatString(ret))
elif isinstance(curWrapper, UniWebBase):
can = curWrapper.can(methodName)
if can is None:
raise CommandException(
"Invalid method name '%s' specified for wrapper '%s'" % (methodName, wrapperClassNm))

ret = self.activateCan(can, curWrapper, wrapperParamsDict)
self.logger.cmdResponse(getFormatString(ret))
elif isinstance(curWrapper, CliWrapper):
ret = [curWrapper.runWrapper(methodName, wrapperParamsDict)]
else:
newParams = {}
newParams['wrapper'] = curWrapper
newParams['method'] = methodName
newParams['params'] = wrapperParamsDict
ret = runWrapperParamsDict['host'].runToolWrapperMethod(newParams)

return ret
finally:
if dispatching:
dispatching()

def __getPropertyDispatchTw(self, componentClass, wrapperObj, compObject=None, propertiesList=None, hostObj=None):
"""调用Wrapper对象里面的方法获取所对应对象的属性

Args:
componentClass (String) : 所需要查询属性的类名
wrapperObj (UniAutos.Wrapper) : 指定哪一个wrapper对象来查询属性列表
compObject (UniAutos.Component) : 可选参数 ，限制wrapper只查询该对象的属性
propertiesList (List) : 可选参数， 需要查询的属性列表，默认值为None，表示查询所有属性
hostObj (UniAutos.Device.Host) : 指定哪一个主机调用执行Wrapper命令

Returns:
ret(Dict): 一个包含keys('propSets', 'properties')的字典

'propSets' (List) : 包含多个命令行回显的解析格式，例如
[{
idVar1 : {
'id' : idVar1
'prop' : val
}

idVar1 : {...}

}]

'properties' (List) : 返回一个List包含所有属性名称


Raises:
UniAutos.Exception.UniAutosException

Examples:
None

"""

allProps = False
if not propertiesList:
allProps = True
propertiesList = []

if not wrapperObj.getDevice():
if isinstance(self, DeviceBase):
wrapperObj.setDevice(self)

twPropertyDict = wrapperObj.createPropertyInfoHash(componentClass, propertiesList)

if (allProps):
propertiesList = twPropertyDict.keys()

methodDict = {}
handlePropsList = []

for prop in propertiesList:
if twPropertyDict.has_key(prop) and twPropertyDict[prop].has_key('getmethod'):
handlePropsList.append(prop)
funcId = twPropertyDict[prop]['getmethod']
if funcId not in methodDict:
methodDict[funcId] = dict()
methodDict[funcId]['method'] = twPropertyDict[prop]['getmethod']
if not methodDict[funcId].has_key('properties'):
methodDict[funcId]['properties'] = []

if not allProps:
methodDict[funcId]['properties'].append(prop)

propSetsList = []
for funcId in methodDict.keys():
method = methodDict[funcId]['method']
getPropsList = methodDict[funcId]['properties']
getParamDict = {'options': getPropsList}
if compObject:
getParamDict['object'] = compObject
runWapperParamsDict = {}
if hostObj is not None:
runWapperParamsDict['host'] = hostObj
runWapperParamsDict['wrapper'] = wrapperObj

retList = []

try:
retList = self.__callWrapper(runWapperParamsDict, method, getParamDict, 1)
except Exception, exe:
if isinstance(exe, ObjectNotFoundException) and 'object' in getParamDict:
if getParamDict.has_key('object'):
getParamDict['object'].getDevice.removeObject(getParamDict['object'])
getParamDict['object'].checkDead()
else:
raise exe

for ret in retList:
if ret.has_key('parser') and len(ret['parser'].keys()) > 0:
propSetsList.append(ret['parser'])

return {'propSets': propSetsList, 'properties': handlePropsList}

def isThisThreadDispatching(self):
"""判断当前线程是否在Dispatching处理中。

Examples:
host.isThisThreadDispatching

"""

dispatchingThreads = self._dispatchesInProgress
tid = threading.currentThread().ident
for thd in dispatchingThreads:
if thd == tid:
self.logger.debug('This thread [%d] is currently dispatching' % tid)
return True
return False

def isDispatching(self):
"""判断当前Dispatcher是否正在下发命令
Returns:
Boolean - True: it stands for the thread is dispatching
False: it means the thread is not dispatching
"""

dispatchingThreads = self._dispatchesInProgress

# 新增定位注释，用于定位Vstore的pause信息
isVstoreDevice = self.isVstoreDevice if hasattr(self, 'isVstoreDevice') else False
if hasattr(self, 'vstoreControllers') and not isVstoreDevice:
# 如果当前控制器对象有Vstore在下发业务，则直接返回正在下发业务, 不必再判断unified的控制器对象
# 如果都没有下发业务，则再判断unified的控制器对象.

self.logger.debug("Current unified controller have vstore: %s" % self.vstoreControllers)
self.logger.debug("Check Current Unified Controller's Vstore Controllers is Dispatching.")
for name in self.vstoreControllers:
_dispatching = self.vstoreControllers[name].isDispatching()
if _dispatching:
return True

self.logger.debug("Current Host Object[%s] dispatchesInProgress :%s, Is Vstore Device: %s"
% (self, dispatchingThreads, isVstoreDevice))
if dispatchingThreads:
module = 'UniAutos.Device.Host.HostBase'
__import__(module)
moduleClass = getattr(sys.modules[module], "HostBase")
if isinstance(self, moduleClass):
self.logger.debug(
'The following threads are dispatching to this host %s: %s' % (self.localIP, dispatchingThreads))
else:
self.logger.debug('The following threads are dispatching to this Device: %s' % dispatchingThreads)
return True
return False

def markAsDispatching(self):
"""标记当前的Dispatcher正在下发命令

Changes:
2015-05-19 y00292329 Created

"""
# 新增定位注释，用于定位Vstore的pause信息
isVstoreDevice = self.isVstoreDevice if hasattr(self, 'isVstoreDevice') else False
self.logger.debug("Current Host Object: %s, pauseDispatches: %s, Is VstoreDevice: %s"
% (self, self._pauseDispatches, isVstoreDevice))

# 如果是Vstore的设备还需要检查对应的unified设备有没有被pause
unifiedPaused = False
if isVstoreDevice and hasattr(self, 'unifiedController'):
self.logger.debug("This is a vstore controller, Unified controller[%s] pauseDispatches: %s" %
(self.unifiedController, self.unifiedController._pauseDispatches))
if self.unifiedController._pauseDispatches.get('until'):
unifiedPaused = True
# 如果unified pause了但是vstore未pause， 需要设置vstore pause
if self._pauseDispatches['until'] is None:
self._pauseDispatches['until'] = self.unifiedController._pauseDispatches.get('until')
# 如果vstore或者unified被pause了那么当前的控制器不管是unified还是vstore都不能下发命令
if self._pauseDispatches['until'] or unifiedPaused:

# 设置_allowTid一般为unified，如果不是unified必须进行pause
if (self.__allowTid == -1 and DeviceBase.globalDoesThreadHaveAnyLocks() and not isVstoreDevice) or \
self.__allowTid == threading.currentThread().ident:
self.logger.debug('Dispatches are paused on this device'
' but we can go because we are either in the middle of a dispatch already or '
'we have an active class lock（Tid:%d）' % self.__allowTid)
# 处于被标记状态的正在下发命令的dispatcher不能被pause
elif threading.currentThread().ident in self._dispatchesInProgress:
self.logger.debug('Dispatches are paused on this device '
'but we can go because we are in the middle of a dispatch already '
'(Tid:%d)' % threading.currentThread().ident)
else:

module = 'UniAutos.Device.Host.HostBase'
__import__(module)
moduleClass = getattr(sys.modules[module], "HostBase")
if isinstance(self, moduleClass):
self.logger.debug('Dispatches on this host (%s) have been '
'paused until %s, Current Object: %s, is Vstore Device: %s.'
% (self.localIP, self._pauseDispatches['until'], self, isVstoreDevice))
else:
self.logger.debug('Dispatches on this Device have been '
'paused until %s, Current Object: %s, is Vstore Device: %s '
% (self._pauseDispatches['until'], self, isVstoreDevice))
while self._pauseDispatches['until'] is not None and datetime.datetime.now() < \
self._pauseDispatches['until']:
sleep(1)
if not self._pauseDispatches['until']:
break

if isinstance(self, moduleClass):
self.logger.debug('Dispatches have resumed on host (%s)' % self.localIP)
else:
self.logger.debug('Dispatches have resumed on Device')
# 这里只需要设置自己设备为None， 其他设备进行下发命令是会自行判断并设置
self._pauseDispatches['until'] = None

origLockValue = Dispatcher.ignoreDispatchPauseLock
Dispatcher.ignoreDispatchPauseLock = True
tid = threading.currentThread().ident
if tid not in self._dispatchesInProgress:
self._dispatchesInProgress[tid] = 0
self._dispatchesInProgress[tid] += 1
self.logger.debug(' markAsDispatching in dispatchesInProgress %s' % str(self._dispatchesInProgress))

def dispatching():
self._dispatchesInProgress[tid] -= 1
if self._dispatchesInProgress[tid] == 0:
del self._dispatchesInProgress[tid]
Dispatcher.ignoreDispatchPauseLock = origLockValue

return dispatching

def pauseDispatches(self, duration):
"""暂停下发命令，设置暂停时间长短

Args:
duration (str): 暂停的时长，例如 30S

Examples:
#可以参照UniAutos.Component.Controller.Huawei.OceanStor.StorController的reboot方法
#并且结合pauseCommandsDispatch和unpauseCommandDispatch
controllerHost.pauseDispatches(pausingTime)

"""

matchObj = re.match(r'\d+$', duration)
if matchObj:
duration += 'S'
duration = Units.getNumber(Units.convert(duration, SECOND))
unit = datetime.datetime.now() + datetime.timedelta(seconds=duration)
self._pauseDispatches['until'] = unit

# 新增定位注释，用于定位Vstore的pause信息
isVstoreDevice = self.isVstoreDevice if hasattr(self, 'isVstoreDevice') else False
self.logger.debug("Current Controller Hosts Object: %s, _pauseDispatches: %s, Is Vstore Device: %s"
% (self, self._pauseDispatches, isVstoreDevice))

tid = threading.currentThread().ident
module = 'UniAutos.Device.Host.HostBase'
__import__(module)
moduleClass = getattr(sys.modules[module], "HostBase")
if duration == 0:
if isinstance(self, moduleClass):
self.logger.debug('Thread %d is unpausing dispatches to this host [%s]' % (tid, self.localIP))
else:
self.logger.debug('Thread %d is unpausing dispatches to this Device' % tid)
else:
if isinstance(self, moduleClass):
self.logger.debug('Thread %d is issuing a pause for dispatches to this host [%s], '
'pause: %s second' % (tid, self.localIP, duration))
else:
self.logger.debug('Thread %d is issuing a pause for dispatches to this Device, '
'pause: %s second.' % (tid, duration))
# TODO 这里的睡眠5秒是做什么的不知道，暂时注释掉
# sleep(5)

def createPropertyInfoHash(self, cls, properties=None):
if properties is None:
properties = list()
if not isinstance(cls, str):
cls = cls.__module__ + '.' + cls.__name__
return CmdMapping.MethodHash.get(cls)

def createWrapperParams(self, clsName, method, params=None):
methodDict = CmdMapping.MethodHash.get(clsName, {})
if method == "show":
result = methodDict.get(method, "")
params = {}
if isinstance(result, str):
methodName = result
elif isinstance(result, dict):
params = result["extra"]
methodName, params = Adapter.__dict__.get(result["method"])(params)
return {"methodName": methodName, "params": params}
elif method == "detail":
result = methodDict.get("show", "")
params = {}
if isinstance(result, str):
methodName = result
elif isinstance(result, dict):
if result.get("method").startswith("adapter"):
params = result.get("extra", {})
methodName, params = Adapter.__dict__.get(result["method"])(params)
else:
methodName = result.get("method")
paramName = methodDict.get("detail", {}).get("param")
extraparams = methodDict.get("detail", {}).get("extra", {})
propertiesName = methodDict.get("detail", {}).get("properties", "id")
return {"methodName": methodName, "params": extraparams, "paramsName": {paramName: propertiesName}}
elif method == "update":
methodName = methodDict.get("update", "")
paramName = methodDict.get("detail", {}).get("param")
propertiesName = methodDict.get("detail", {}).get("properties", "id")
return {"methodName": methodName, "paramsName": {paramName: propertiesName}}
return {}

def setHighPriorityView(self, wrapperName, params=None):
"""
设置高优先级的VIEW，命令会有限在该视图下发
Args:
wrapperName: 视图名 (vstore, admincli)
params: 切换到该视图的参数

Returns:

"""
self.highPriorityView['name'] = wrapperName
self.highPriorityView['view_params'] = params
if wrapperName == "vstore" and not self.highPriorityView.get("cmdTemplate", ""):
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V300R006C00").__dict__
self.highPriorityView['cmdTemplate'] = cmdTemplate

def selectHighPriorityView(self, cmdSpace, version):
"""
根据设置的HighPriorityView， 选择命令下发的模式，在HostBase.run 方法中调用
Args:
cmdSpace:

Returns:

"""
if self.highPriorityView.get('name') == "vstore":
cmd = " ".join(cmdSpace['command'])
if "|filter" in cmd:
awname = cmd.split('|')[0].strip().replace(" ", "_")
cmdSpace['waitstr'] = None
else:
awname = re.split(r"\s*\S+\s*=\s*\S*\s*", cmd)[0].replace(" ", "_")
if version in ['V300R006C00']:
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V300R006C00").__dict__
elif version in ['V500R007C00', 'V500R007C10', 'V300R006C10', 'V300R006C20']:
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V500R007C00").__dict__
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
elif version in ['V500R007C20', 'V300R006C21', 'V300R006C30', 'V500R007C30', 'V300R006C50',
'V500R007C50', 'V300R006C60', 'V500R008C00', "V500R007C60 Kunpeng", "V500R007C60"]:
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V500R007C20").__dict__
elif version in ['V300R006C01']:
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V300R006C01").__dict__
else:
cmdTemplate = self.highPriorityView['cmdTemplate']
if awname in cmdTemplate:
if 'vstore' in cmdTemplate[awname]['view']:
cmdSpace['sessionType'] = self.highPriorityView['name']
cmdSpace['view_params'] = self.highPriorityView['view_params']
return cmdSpace
# if self.highPriorityView.get('name') == "vstore":
# cmd = " ".join(cmdSpace['command'])
# awname = re.split(r"\s*\S+\s*=\s*\S*\s*", cmd)[0].replace(" ", "_")
# if awname in self.highPriorityView['cmdTemplate']:
# if self.highPriorityView['name'] in self.highPriorityView['cmdTemplate'][awname]['view']:
# cmdSpace['sessionType'] = self.highPriorityView['name']
# cmdSpace['view_params'] = self.highPriorityView['view_params']
# return cmdSpace

def setHighPriorityWrapper(self, *wrappers):
"""
设置wrapper优先级
Args:
*wrappers: wrapper名例如"admincli", "developer", "upgrade"

Returns:

"""

def getkey(e):
try:
wrapper_type = e['wrapper_type']
wrapperName = wrapper_type.split('.')[-1].lower()
lens = len(wrappers)
for idx, val in enumerate(wrappers):
if wrapperName.startswith(val.lower()):
return idx
return lens
except Exception as e:
self.logger.warn(e)
return 999

self.original_wrapper_list = self.wrapper_list
self.wrapper_list = sorted(self.wrapper_list, key=getkey)

# @classmethod
def setAllowDispatchThread(self, tid=None):
"""
设置dispatch全局锁，可以锁住全局dispatch并且只允许当前线程下发命令
Args:
tid (int): (optional)线程id，默认将全局dispatch锁住，设置只允许当前线程下发命令

Returns:
None

Raises:
None

Examples:
设置全局dispatch锁
allControllers[0].getHostObject().setAllowDispatchThread()
恢复全局dispatch锁
allControllers[0].getHostObject().setAllowDispatchThread(-1)
"""
if tid is None:
tid = threading.currentThread().ident
self.__allDispatchLock.acquire()
self.__allowTid = tid
# unified设置了vstore也需要设置
if (hasattr(self, 'isVstoreDevice') and not getattr(self, 'isVstoreDevice')
and hasattr(self, 'vstoreControllers')):
for name in getattr(self, 'vstoreControllers', {}):
getattr(self, 'vstoreControllers')[name].setAllowDispatchThread(tid=tid)
self.__allDispatchLock.release()

