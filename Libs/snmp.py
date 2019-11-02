# -*- coding: utf-8 -*-
"""
功 能:

版权信息: 华为技术有限公司，版权所有(C) 2014-2015
"""

from Libs.SnmpV1 import SnmpV1
from Libs.SnmpV2 import SnmpV2C
from Libs.SnmpV3 import SnmpV3
from Libs.Exception.CustomExceptions import UnsupportedException

class Snmp:
    @staticmethod
    def create(hostIp, port=161, snmpVer='v3', userName=None, userDefineMibsDir=None, timeout=16, retries=5,
               communityData=('storage_public', 'storage_private'), authKey=None, privKey=None, authProtocol=None, privProtocol=None):
        """SNMP工厂类的静态方法，用户使用SNMP协议组件的入口

        Args:
        hostIp (str) : 阵列IP地址
        port (int) : (可选参数)阵列开放的SNMP通信端口。默认：161
        snmpVer (str) : (可选参数)SNMP协议版本。取值：v1/v2c/v3。默认：v3
        userName (str) : (可选参数)SNMP V3版本中需要设置的用户名
        userDefineMibDir (str) : (可选参数)用户自定义Mib文件的存放路径，识别文件夹中的*mib.py文件。默认：None
        timeout (int) : (可选参数)超时时间。单位：秒。默认：3
        retries (int) : (可选参数)重试次数。默认：5次
        communityData (tuple) : (可选参数)读写团体字。默认：('storage_public', 'storage_private')
        authKey (str) : (可选参数)鉴权密码。默认：None
        privKey (str) : (可选参数)加密密码。默认：None
        authProtocol (str) : (可选参数)鉴权协议。取值：MD5/SHA/NONE。默认：NONE
        privProtocol (str) : (可选参数)加密协议。取值：AES128/AES192/AES256/DES/3DES/NONE。默认：NONE

        Returns:
        指定SNMP版本的SNMP对象

        Raises:
        None

        Examples:
        None
        """
        snmpVer = str(snmpVer).lower()
        if snmpVer == 'v1':
            return SnmpV1(hostIp,
                          port=port,
                          communityData=communityData,
                          userDefineMibsDir=userDefineMibsDir,
                          timeout=timeout,
                          retries=retries)
        elif snmpVer == 'v2c':
            return SnmpV2C(hostIp,
                           port=port,
                           communityData=communityData,
                           userDefineMibsDir=userDefineMibsDir,
                           timeout=timeout,
                           retries=retries)
        elif snmpVer == 'v3':
            return SnmpV3(hostIp,
                          userName=userName,
                          port=port,
                          userDefineMibsDir=userDefineMibsDir,
                          timeout=timeout,
                          retries=retries,
                          authKey=authKey,
                          privKey=privKey,
                          authProtocol=authProtocol,
                          privProtocol=privProtocol)
        else:
            raise UnsupportedException('Unknown snmp version. Expected "v1/v2c/v3", but got "%s"' % snmpVer)
