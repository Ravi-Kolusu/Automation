# -*- coding: utf-8 -*-

"""
功 能: SNMP V2C版本基本操作接口

版权信息: 华为技术有限公司，版权所有(C) 2014-2015
"""

from pysnmp.entity.rfc3413.oneliner import cmdgen

from UniAutos.Wrapper.Api.Snmp.SnmpV1 import SnmpV1


class SnmpV2C(SnmpV1):

def __init__(self,
hostIp,
port=161,
communityData=None,
userDefineMibsDir=None,
timeout=3,
retries=5):
"""SNMP V2c版本构造函数

Args:
hostIp (str) : 阵列IP地址
port (int) : (可选参数)阵列开放的SNMP通信端口。默认：161
userDefineMibDir (str) : (可选参数)用户自定义Mib文件的存放路径，识别文件夹中的*mib.py文件。默认：None
communityData (tuple) : (可选参数)读写团体字。默认：('storage_private', 'storage_public')
timeout (int) : (可选参数)超时时间。单位：秒。默认：3
retries (int) : (可选参数)重试次数。默认：5次

Returns:
返回SNMP对象

Raises:
None

Examples:
None

"""

super(SnmpV2C, self).__init__(
hostIp,
port=port,
communityData=communityData,
userDefineMibsDir=userDefineMibsDir,
timeout=timeout,
retries=retries
)

self.communityData = cmdgen.CommunityData(*communityData, mpModel=1)