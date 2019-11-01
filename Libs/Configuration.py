#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: Configuration, 用例配置基类.

版权信息: 华为技术有限公司，版本所有(C) 2014-2015

"""

from UniAutos.TestEngine.Base import Base


class Configuration(Base):
"""用于关联测试用例的配置参数和执行

Args:
caseValidation (dict): testSet传入的Case使用的数据.格式如下：
test_validation = {"name": "",
"path": "",
"resource": None,
"params": [],
"description": '',
"tags": [],
"required_equipment": [],
"steps_to_perform": [],
"shareable_equipment": 0,
"identities": {"identity": [{"name": "ax_id", "value": 1}, ]},
"instance_id": "",
"order": 1,
"dependencies": {}}
Attributes:
self.configParams (list): 设置配置的参数.
self.deConfigParams (list): 清理配置的参数.
传入的参数的格式如下:
[{"name": "lun_type", "value": "thin"}, {"name" :"size", "value": ["10GB", "20GB", ]}, ]
Returns:
Configuration (instance): Configuration实例对象.

Examples:
conObj = Configuration(caseValidation)

"""

def __init__(self, caseValidation):

self.configParams = caseValidation.pop("config_params", None)
self.deConfigParams = caseValidation.pop("deConfig_params", None)
super(Configuration, self).__init__(caseValidation)

# NOTE: 每个脚本需要自定义如下参数.
# def createMetaData(self):
# self.addParameter(
# name='Mode',
# description='It describes the mode of the test configuration',
# default_value='Config',
# type='select',
# display_name='Mode',
# validation={'valid_values': ['Config', 'DeConfig']}
# )

def configuration(self):
"""执行此测试配置的配置操作

此方法必须被重写使用, 默认下使用会打印告警信息.

Examples:
self.configuration()

"""
self.logger.warn("Configuration has not been defined!")

def runConfiguration(self):
"""由Engine调用用于执行configuration()和deConfiguration()方法.

Examples:
self.runConfiguration()

"""

if self.configParams:
self.setParameter(self.configParams)
self.configuration()
if self.deConfigParams:
self.setParameter(self.deConfigParams)

def deConfiguration(self):
"""执行此测试配置的清除配置操作

此方法必须被重写使用, 默认下使用会打印告警信息.

Examples:
self.deConfiguration()

"""
self.logger.warn('De-configuration has not been defined!')