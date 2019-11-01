DockerControllerHost ::

#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：控制器类
版权信息：华为技术有限公司，版本所有(C) 2014-2015
"""

from time import time
from UniAutos.Util.Time import sleep
from UniAutos import Log
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Device.Host.Controller.OceanStor import OceanStor


class DockerControllerHost(OceanStor):
"""Docker Virtual controller host object
"""
logger = Log.getLogger(str(__file__))
def __init__(self, username, password, params):
super(DockerControllerHost, self).__init__(username, password, params)
self.virtual = True

def updateRunningVersion(self, productInfo=None):
"""This is a BDM virtual controller host, if tester need running version, please update this func

Returns:

"""

# Mock some fake attributes
default_mock_attributes = {'system_name': 'Huawei.Storage',
'product_model': 'Dorado6000 V3',
'running_status': 'Normal',
'product_version': 'V600R003C00',
'patch_version': 'SPC100',
'health_status': 'Normal',
'high_water_level': '80',
'sn': '21023598251008000002',
'low_water_level': '20',
'wwn': '21003400a303c020',
'totalcapacity': '21.801TB'}
if productInfo:
productInfo = default_mock_attributes.update(productInfo)
else:
productInfo = default_mock_attributes

self.softVersion = productInfo.get("product_version", "")
self.patchVersion = productInfo.get("patch_version", "")
self.productModel = productInfo.get("product_model", "")
self.SN = productInfo.get("sn", "")
self.systemName = productInfo.get("system_name", "")
self.location = productInfo.get("location", "")
self.systemHealthStatus = productInfo.get("health_status", "")
self.systemRunningStatus = productInfo.get("running_status", "")
self.totalCapacity = productInfo.get("totalcapacity", "")
self.systemHighWaterLevel = productInfo.get("high_water_level", "")
self.systemLowWaterLevel = productInfo.get("low_water_level", "")
self.wwn = productInfo.get("wwn", "")
