#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: 在阵列中申请UniAutos.Requirement.Configuration指定的业务对象.

"""

import re
import threading
from UniAutos.Requirement.ConfigureInfo.Heal import Heal
from UniAutos.Requirement.ConfigureInfoBase import ConfigureInfoBase
from UniAutos import Log
from UniAutos.Util.TypeCheck import validateDict
from UniAutos.Component.ComponentBase import ComponentBase
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Device.Storage.StorageBase import StorageBase

logger = Log.getLogger(__file__)

def applyConfig(requirement, testObject=None):
"""在阵列中验证UniAuto.Requirement.Configuration

Args:
requirement (instance): ConfigureInfoBase对象.
testObject (instance): 测试用例对象.

Returns:
ret (list): 由componentCreate创建的component列表.

Raises:
None.

Examples:
None.
"""
if not isinstance(requirement, ConfigureInfoBase):
raise InvalidParamException()

testObj = testObject if testObject else None
deviceType = requirement.deviceType
dev = requirement.device
logger.debug("[ConfigureEnv] Locking device for apply()")
dev.acquireThreadDeviceLock()
ret = []
try:
if requirement.validateAndHeal:
isValid = validateConfig(requirement)
if not isValid:
logger.debug("[ConfigureEnv] Healing current configuration"
" rather than applying a new configuration")
ret = healConfig(requirement, testObj)
else:
logger.debug("[ConfigureEnv] Current configuration on array"
" fulfills the configuration requirements")
return ret
else:
logger.debug("[ConfigureEnv] Configuration apply start")
componentMaps = requirement.getDevice().getConfigEnvComponentMap()
tmpComponentDict = {}
for compMap in componentMaps:
compName = compMap["component"].lower()
if not hasattr(requirement, compName):
continue
tmpRetComponent = []
componentList = getattr(requirement, compName)
if isinstance(componentList, list):
for tmpComponentParams in componentList:
tmpRetComponent = dev.componentCreate(compName, tmpComponentParams)
for compObj in tmpRetComponent["requested_components"]:
compObj.setCreatedByConfigureEnv(True)
if testObj:
testObj.addCreatedConfigEnvComponent(compObj)
for compObj in tmpRetComponent["dependency_components"]:
compObj.setCreatedByConfigureEnv(True)
if testObj:
testObj.addCreatedConfigEnvComponent(compObj)
if "child_dicts" in tmpRetComponent and tmpRetComponent["child_dicts"]:
_lookIntoChildHash(tmpRetComponent["child_dicts"], testObj)
ret.append(tmpRetComponent)
else:
raise InvalidParamException("Each component must be List.")
logger.debug("[ConfigureEnv] Configuration apply end")
return ret
# except Exception as exe:
# logger.error("[ConfigureEnv] Configuration apply failed: %s" % errorMsg)
# raise
finally:
dev.releaseThreadDeviceLock()


def wipeConfig(device, componentTypes=None, testObject=None):
"""清除设备中的指定类型且归属于某个用例的component对象.

Args:
componentTypes (list): component对象的类名全称列表.
device (instance): 设备对象.
testObject (instance): 测试用例对象.

Returns:
None.

Raises:
None.

Examples:
None.
"""

if not isinstance(device, StorageBase):
raise InvalidParamException()

testObj = testObject if testObject else None
componentTypes = componentTypes if componentTypes and isinstance(componentTypes, str) else None

# 将componentTypes全部转换为小写，便于统一使用.
if componentTypes:
tmpTypes = list()
for tmp in componentTypes:
tmpTypes.append(tmp.lower())
componentTypes = tmpTypes

logger.debug("[ConfigureEnv] Locking device for wipe()")
device.acquireThreadDeviceLock()

def safeWipe(comp):
if comp.isDead():
return
else:
comp.wipe()

logger.debug("[ConfigureEnv] Configuration remove starting")
try:
# 指定了需要删除业务的用例.
if testObj:
logger.debug("Only wiping Configuration Engine created components created in Test Case: %s" % testObj.name)
deviceId = device.id
componentObj = testObj.getNextCreatedConfigEnvComponent()
tmpComponentDict = {}

while componentObj:
compObjType = componentObj.classFullName.lower() # todo need component add type
compObjDevice = componentObj.owningDevice

if not componentTypes or (componentTypes and compObjType in componentTypes):
if compObjDevice.id == deviceId:
if componentObj.isCreateByConfigureEnv:
safeWipe(componentObj)
if compObjType in tmpComponentDict:
tmpComponentDict[compObjType].append(componentObj)
else:
tmpComponentDict[compObjType] = [componentObj]
elif componentObj.validatedByEngine():
componentObj.removeValidatedByConfigureEnv()
componentObj = testObj.getNextCreatedConfigEnvComponent()

for compName in tmpComponentDict:
objectsToWaitFor = tmpComponentDict[compName]
device.waitForDeadComponent(objectsToWaitFor)

# 指定了需要删除的业务全称.
elif componentTypes:
logger.debug("Only wiping Configuration Engine created components "
"of these component types: %s" % ", ".join(componentTypes))

# 获取指定全名的业务类的别名，用以find.
allCompObjectMaps = device.getEnableComponents()
componentAliases = list()
for key in allCompObjectMaps:
if allCompObjectMaps[key].lower in componentTypes:
componentAliases.append(key.lower())

for compType in componentTypes:
compObjects = device.find(alias=compType, createByConfigureEnv=True)
map(safeWipe, compObjects)
device.waitForDeadComponent(compObjects)
validateObjects = device.find(alias=compType, validatedByConfigureEnv=True)
for validatedComp in validateObjects:
validatedComp.removeValidatedByConfigureEnv()

# 只指定删除业务的设备.
else:
logger.debug("Wiping all Configuration Engine created components")
allCompObjectTypes = device.getEnableComponents()

for compTypes in allCompObjectTypes.itervalues():
for compType in compTypes:
compObjs = device.getCurrentOwnedComponents(compType)
objectsToWaitFor = []
for compObj in compObjs:
if isinstance(compObj, ComponentBase):
objectsToWaitFor.append(compObj)
safeWipe(compObj)
elif compObj.isValidatedByConfigureEnv:
compObj.removeValidatedByConfigureEnv()
device.waitForDeadComponent(objectsToWaitFor)
logger.debug("[ConfigureEnv] Configuration remove end")
# except Exception, errorMsg:
# logger.error("[ConfigureEnv] Configuration remove failed: %s" % errorMsg)
finally:
if device.isDeviceThreadLocked():
device.releaseThreadDeviceLock()


def validateConfig(requirement):
"""在阵列中验证UniAuto.Requirement.Configuration

Args:
requirement (instance): ConfigureInfoBase对象.

Returns:
ret (bool): 是否验证通过，True：验证通过不再进行创建，False: 验证失败需要再次进行创建.

Raises:
None.

Examples:
None.
"""
if not isinstance(requirement, ConfigureInfoBase):
raise InvalidParamException()

deviceType = requirement.deviceType
dev = requirement.getDevice()
logger.debug("[ConfigureEnv] Locking device for validateConfig()")
dev.acquireThreadDeviceLock()
ret = True
try:
validateComponentOrder = dev.getConfigEnvComponentMap()
for compMap in validateComponentOrder:
compType = compMap["component"].lower()
if not hasattr(requirement, compType):
continue
componentList = getattr(requirement, compType)
if isinstance(componentList, list):
logger.trace("Sorting keys from most to least for config type:%s" % compType)
sortedComponentDicts = _sortConfigByKeyCounts(configsList=componentList, sort="desc")
for componentDict in sortedComponentDicts:
if "validated" in componentDict and componentDict["validated"]:
componentDict.pop("validated")
ret = dev.componentValidate(compType, componentDict)
if "validated" in ret and ret["validated"]:
_markAsValidated(ret)
componentDict["validated"] = True
else:
ret = False
break
else:
raise InvalidParamException("Each component must be List")

logger.debug("[ConfigureEnv] Configuration validate end")
return ret
# except Exception, errorMsg:
# logger.error("[ConfigureEnv] Configuration validate failed: %s" % errorMsg)
finally:
if dev.isDeviceThreadLocked():
dev.releaseThreadDeviceLock()


def healConfig(requirement, testObject=None):
"""计算requirement是否缺失，并创建requirement对应的component.

Args:
requirement (instance): ConfigureInfoBase对象.
testObject (instance): 测试用例对象．

Returns:
ret (list): 创建的component对象列表.

Raises:
None.

Examples:
None.
"""
if not isinstance(requirement, ConfigureInfoBase):
raise InvalidParamException()

testObj = testObject if testObject else None

dev = requirement.getDevice()

if not dev.isDeviceThreadLocked():
logger.debug("[ConfigureEnv] Locking device for healConfig()")
dev.acquireThreadDeviceLock()
try:
logger.debug("[ConfigureEnv] Configuration healConfig() start.")
newConfig = calculateMissingRequirements(requirement)
newConfig.validateAndHeal = 0
ret = applyConfig(newConfig, testObj)
logger.debug("[ConfigureEnv] Configuration heal end")
return ret
# except Exception, errorMsg:
# logger.error("[ConfigureEnv] Configuration heal failed: %s" % errorMsg)
finally:
if dev.isDeviceThreadLocked():
dev.releaseThreadDeviceLock()


def calculateMissingRequirements(requirement):
"""计算缺失的component，并创建.

Args:
requirement (instance): UniAuto.Requirement.Configuration对象.

Returns:
heal (instance): UniAuto.Requirement.Configuration.Heal对象.

Raises:
None.

Examples:
None.
"""
if not isinstance(requirement, ConfigureInfoBase):
raise InvalidParamException("")

componentMaps = requirement.getDevice().getConfigEnvComponentMap()
tmpComponentDict = {}
for compMap in componentMaps:
compName = compMap["component"].lower()
if not hasattr(requirement, compName):
continue
componentList = getattr(requirement, compName)
if isinstance(componentList, list):
newComponents = []
for tmpComponent in componentList:
isValidated = tmpComponent.pop("validated", None)
if not isValidated:
newComponents.append(tmpComponent)
setattr(requirement,compName, newComponents)
tmpComponentDict.update({compName: newComponents})
else:
raise InvalidParamException()

if not getattr(requirement, compName):
delattr(requirement, compName)

return Heal(requirement.testCase, requirement.deviceId, requirement.deviceType, tmpComponentDict,
device=requirement.device, validateAndHeal=requirement.validateAndHeal, configId=requirement.configId)


def _lookIntoChildHash(childList, testObject=None):
"""采用的递归的方法使所有的components被标记为由ConfigureEnv创建, 且添加到用例的configEnvCreateComponents列表中

Args:
childList (list): components列表，必选参数；单个元素为Dict，单个元素dict的键值对为：
requested_components (list): 需要创建的components.
dependency_component (list): 依赖的components.
child_dicts (list): 与childList相同的components列表.
testObject (instance): 需要childList标识的参数的测试用例对象，可选参数.

Returns:
None.

Raises:
None.

Examples:
None.
"""
testObj = testObject if testObject else None

for child in childList:
if "requested_components" in child and child["requested_components"]:
for obj in child["requested_components"]:
obj.setCreatedByConfigureEnv(True)
if testObj:
testObj.addCreatedConfigEnvComponent(obj)
if "dependency_component" in child and child["dependency_component"]:
for obj in child["dependency_component"]:
obj.setCreatedByConfigureEnv(True)
if testObj:
testObj.addCreatedConfigEnvComponent(obj)
if "child_dicts" in child and child["child_dicts"]:
_lookIntoChildHash(child["child_dicts"], testObj)

return


def _sortConfigByKeyCounts(configsList=list(), sort="asc"):
"""将一个元素为多个config列表组成的configsList按照包含的config数量进行排序

Args:
configsList (list): 特定业务对象的多份配置需求参数，configsList的单个元素一个dict，元素dict为其中一个特定业务对象的参数，
-元素的key为业务对象的别名，值为参数列表.
如, storagepool：
[{
"lun": [{size: '100GB', count: 4},
{size: '200GB',count: 2}]
"filesystem": [{size: '100GB', count: 4},
{size: '200GB',count: 2}]
}
{...
}

sort (str): 排序的关键字，取值范围为升序："asc", 降序: "desc"。

Returns：
sortedCfg (list): 经过排序后的特定业务对象配置需求参数.

Raises:
InvalidParamException: sort参数非法时抛出.

Examples:
None.

"""
if not re.match(r'^asc|desc$', sort):
raise InvalidParamException("parameter sort[%s] must be asc or desc. " % sort)

tmpCfg = {} # 临时保存configList中的configuration，key为单个configuration的个数，值为个数相同的configuration.
sortedCfg = []

# Create a hash using the number of keys as top-level hash key.
for cfg in configsList:
numKeys = str(len(cfg))
if numKeys not in tmpCfg:
tmpCfg[numKeys] = [cfg]
else:
tmpCfg[numKeys].append(cfg)

# Sort by the number of keys (most to least, or least to most)
orderedConfigKeys = []
if sort == "asc":
orderedConfigKeys = sorted(tmpCfg)
if sort == "desc":
orderedConfigKeys = sorted(tmpCfg, reverse=True)
logger.trace("Ordering by key counts in '%s' order: %s" % (sort, ",".join(orderedConfigKeys)))

# 获取排序后的configuration
for cfgKey in orderedConfigKeys:
sortedCfg.extend(tmpCfg[cfgKey])

# 检查排序后的configuration个数是否正确.
originalCount = len(configsList)
sortedCount = len(sortedCfg)
if originalCount != sortedCount:
raise UniAutosException("When sorting the config array, we did not end "
"up with the same number of configs:\n\n "
"\tOriginal config count.: %s \n"
"\tSorted config count...: %s" % (originalCount, sortedCount))

return sortedCfg


def _markAsValidated(params):
"""该方法用来标记component验证数据为validated.

Args:

params (dict): 需要标记的component数据字典, 键值对说明如下:
validated (bool): 标记validated_components，validated_child_dicts中的数据是否要进行
-标记.
validated_components (list): component对象的列表，每一个元素为一个component对象.
validated_child_params (list): 每一个元素为一个params字典数据，即：可以包含"validated"、
"validated_components"、"validated_child_dicts".
Returns:
None.

Raises:
None.

Examples:
None.

"""
template = {"validated": {"types": bool, "optional": True},
"validated_components": {"types": list, "optional": True},
"validated_child_params": {"types": list, "optional": True}
}
validateDict(params, template)

if "validated" in params and params["validated"]:
if "validated_components" in params and params["validated_components"]:
for componentObj in params["validated_components"]:
if isinstance(componentObj, ComponentBase):
componentObj.setValidatedByConfigureEnv(True)
if "validated_child_params" in params and params["validated_child_params"]:
for tmpDict in params["validated_child_params"]:
if isinstance(tmpDict, dict):
_markAsValidated(tmpDict)
return