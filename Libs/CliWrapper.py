#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 执行CLI命令下发相关操作

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/3 严旭光 y00292329 created

"""
import re
import copy
import importlib
import pprint
from TemplateCLIObj import CLIObj
from UniAutos.Exception.CommandException import CommandException
from Dryrun import Dryrun
from UniAutos import Log



class CliWrapper(CLIObj):
logger = Log.getLogger(__name__)
defaultVersion = "V300R003C00"
dryrun = Dryrun()

def __init__(self, productModel=None, version=None, patchVersion=None):
"""OceanStor CLI wrapper object

Args:
productModel (str): 设备类型
version (str): 版本号
patchVersion (str) : 补丁版本号

Changes:
2016-06-06 y00292329 Created

"""
super(CliWrapper, self).__init__(productModel, version, patchVersion)


def runWrapper(self, methodName, params, interactRule=None, option=None):
"""执行wrapper命令

Args:
methodName (str): 方法名
params (dict): 方法参数
interactRule (dict): 交互输入规则
option (dict): 控制参数

Changes:
2016-06-06 y00292329 Created

"""
isTimeout = True
if option is None:
option = dict()
elif 'time_out' in option:
isTimeout = False
if interactRule is None:
interactRule = dict()
cmdTemplate, retTemplate = self.getTemplate(methodName)

comperList = [i for i in params.keys() if i not in cmdTemplate["params"].keys()]
if len(comperList) > 0:
self.logger.info("find some param not in cmdTemplate's params %s !" % comperList)

if cmdTemplate:
cmdTemplate = copy.deepcopy(cmdTemplate)
self.logger.debug("[WrapperName] %s [params] %s" % (methodName, params))
option = {k.lower():v for k, v in option.items() if True}
option = dict(self.conf, **option)
option = dict(cmdTemplate.get("opt", {}), **option)
self.adaptParams(methodName, params, option)
cmdSpace = self.generator.generator(cmdTemplate, params, interactRule, option)

# add view method to option, used to ignore some return code.
option['sessionType'] = cmdSpace['sessionType']
option['method'] = methodName

# 如果是非用户传入并且没有修改timeout
if 'timeout' in cmdSpace and isTimeout and self.device.getTimeout:
del cmdSpace['timeout']

if not option.get("debug", False):
if self.device:
result = self.device.run(cmdSpace)
stdout = result.get("stdout", None)
if stdout:
result["stdout"] = re.split("\x0d?\x0a|\x0d", stdout)
validateResult = self.validate(result, option)
if validateResult:
result = self.paserResult(retTemplate, result, option)
else:
msg = 'Failed to execute the command ' + methodName
msg = msg + "\nResult of the wrapper call:\n" + pprint.pformat(result)
raise CommandException(msg, result)
else:
response = self.dryrun.dryrun(methodName, cmdTemplate, params)
result = dict()
if response is None:
result = self.device.run(cmdSpace)
self.dryrun.insertData(methodName,cmdTemplate,params,result["stdout"])
else:
result["stdout"] = response
result["rc"] = None
result["stderr"] = None
validateResult = self.validate(result, option)
if validateResult:
result = self.paserResult(retTemplate, result, option)
else:
result["parser"] = {}

return result
else:
raise Exception("not find cli cmd")

def choseCMDTemplate(self, productModel, version, patchVersion):
"""选择命令模板module

Args:
productModel (str): 设备类型
version (str): 版本号
patchVersion (str): 补丁版本号

Returns:
cmdTemplate (Module): 命令行模板模块

Exceptions:
None

Changes:
2016-06-06 c00305140 Created

"""
cmdTemplate = None
if re.search('Dorado', productModel, re.I) or re.search('D', productModel):
if re.search('V300R001C20', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C20")
self.logger.info("load Dorado cmd template")
elif re.search('V300R001C00', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C00")
self.logger.info("load Dorado cmd template")
elif re.search('V600R002C00', version, re.I):
#TODO：C30暂时加载无OMRP，继承C20的。待独立OMRP后修改
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C20")
self.logger.info("load Dorado cmd template")
elif re.search('V300R002C00', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R002C00")
self.logger.info("load Dorado cmd template: %s" % "DoradoV300R002C00")
elif re.search('V300R002C10', version, re.I) and "NAS" not in productModel:
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R002C10")
self.logger.info("load Dorado cmd template: %s" % "DoradoV300R002C10")
elif re.search('V300R002C20', version, re.I) and "NAS" not in productModel:
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R002C20")
self.logger.info("load Dorado cmd template: %s" % "DoradoV300R002C20")
elif re.search('V100R005C10', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C20")
self.logger.info("load Dorado cmd template")
elif re.search('V300R001C21', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C21")
self.logger.info("load Dorado cmd template")
elif re.search('V300R001C30', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C30")
self.logger.info("load Dorado cmd template: %s" % "DoradoV300R001C30")
elif re.search('6.0.', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV600R003C00")
self.logger.info("load Dorado cmd template: %s" % "DoradoV600R003C00")
elif re.search('V100R001C00', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV100R001C00")
self.logger.info("load Dorado cmd template: %s" % "DoradoV100R001C00")
elif re.search('V500R007C30|V300R002C10|V300R002C20', version, re.I) and "NAS" in productModel:
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "OceanStorDoradoNAS")
self.logger.info("load Dorado cmd template: %s" % "OceanStorCOMMONDoradoNAS")
else:
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "Dorado")
self.logger.info("load Dorado cmd template")
elif productModel=="EMC":
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.EMC.cmd.%s" % version)
else:
try:
if patchVersion:
spcVersion = version + patchVersion
if spcVersion == 'V300R003C20SPC200' or spcVersion == 'V300R003C20SPC100':
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.V300R003C20SPC200")
self.logger.info("version is %s, load V300R003C20SPC200 cmd template" % spcVersion)
if not cmdTemplate:
if 'V300R006C10' in version or 'V500R007C00' in version:
version = 'V500R007C00'
if 'V300R006C20' in version or 'V500R007C10' in version:
version = 'V500R007C10'
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
if 'V500R007C20' in version or 'V300R006C21' in version or 'V300R006C30' in version:
version = 'V500R007C20'
if 'V500R007C30' in version or 'V300R006C50' in version:
version = 'V500R007C30'
if ('V500R007C50' in version or 'V300R006C60' in version) and re.search("18\d{3}", productModel):
version = 'V500R007C5018000'
if ('V500R007C50' in version or 'V300R006C60' in version) and not re.search("18\d{3}", productModel):
version = 'V500R007C50'
if 'V500R008C00' in version:
version = 'V500R008C00'
if 'V500R007C60' in version:
version = 'V500R008C00'
if 'V300R001' in version:
version = 'V300R001C00'
if 'V300R002C10' in version or 'V300R002C20' in version:
version = 'V300R002C10'
if 'V300R005C00' in version:
version = 'V300R005C00'
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % version)
self.logger.info("load %s cmd template" % version)
except Exception:
self.logger.warn("load %s cmd template failed" % version)
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % self.defaultVersion)
self.logger.warn("load default cmd template %s" % self.defaultVersion)
return cmdTemplate