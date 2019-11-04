#!/usr/bin/python
# coding=utf-8

"""

Function: UniWebBase the base class for all web application interface.

Copyright @ Huawei Technologies Co., Ltd. 2014-2024
"""

from UniAutos.Wrapper.Tool.ToolBase import ToolBase
from UniAutos.Wrapper.Tool.Selenium.UniWebs.Common.BrowserType import BrowserType

class UniWebBase(ToolBase):
"""
Desc: UniWebBase the base class for all web application interface.

Import all the operations from ISM. We have added following operations in below:
UniAutos.Wrapper.Tool.Selenium.DeviceManager.Function.DiskDomain

"""

def __init__(self, ipAddress, port, userName, password, browserType=BrowserType.FIREFOX):
"""
Constructor: The base class for all web application factory.

Args:
ipAddress Type(str) : device ip address
port Type(str) : device connection port from web browser
userName Type(str) : user name for device
password Type(str) : password for device
browserType Type(BrowserType): web browser type

Return:
Type(UniWebBase)

Rises:
None

"""
super(UniWebBase, self).__init__()
