# -*- coding: utf-8 -*-

"""
功 能: SNMP V3版本基本操作接口

版权信息: 华为技术有限公司，版权所有(C) 2014-2015
"""

from pysnmp.entity.rfc3413.oneliner import cmdgen
from Libs.SnmpBase import SnmpBase

class SnmpV3(SnmpBase):
    """
    SNMPv3
    """
    def __init__(self,
                 hostIp,
                 userName=None,
                 port=161,
                 userDefineMibsDir=None,
                 timeout=3,
                 retries=5,
                 authKey=None,
                 privKey=None,
                 authProtocol=None,
                 privProtocol=None):
        """SNMP V3版本构造函数

        Args:
        hostIp (str) : 阵列IP地址
        port (int) : (可选参数)阵列开放的SNMP通信端口。默认：161
        userName (str) : (可选参数)SNMP V3版本中需要设置的用户名
        userDefineMibDir (str) : (可选参数)用户自定义Mib文件的存放路径，识别文件夹中的*mib.py文件。默认：None
        timeout (int) : (可选参数)超时时间。单位：秒。默认：3
        retries (int) : (可选参数)重试次数。默认：5次
        authKey (str) : (可选参数)认证密码，认证运算时所需的密钥。默认：None
        privKey (str) : (可选参数)加密密码，加密运算时需要用到的参数。默认：None
        authProtocol (str) : (可选参数)认证运算时使用的加密算法。取值：MD5/SHA/NONE。默认：NONE
        privProtocol (str) : (可选参数)加密运算时使用的加密算法。取值：AES128/AES192/AES256/DES/3DES/NONE。默认：NONE

        Returns:
        返回SNMP对象

        Raises:
        None

        Examples:
        None
        """
        super(SnmpV3, self).__init__(userDefineMibsDir=userDefineMibsDir)

        self.usmUserData = cmdgen.UsmUserData(userName,
                                              authKey=authKey,
                                              privKey=privKey,
                                              authProtocol=self.getAuthProtocolType(authProtocol),
                                              privProtocol=self.getPrivProtocolType(privProtocol))
        self.target = cmdgen.UdpTransportTarget((hostIp, port), timeout=timeout, retries=retries)

    def get(self, *mibNodeNames):
        """SNMP的Get操作

        Args:
        *mibNodeName (tuple) : 待操作的Mib节点名称列表。如：deviceId

        Returns:
        返回dict类型的结果。结构为：{oid1_suffix: {symName1: value, symName2: value, ...}, ...}
        如：{'0': {'deviceId': '21023598260000000107'}}

        Raises:
        NoSuchObjectError : 当查询不到指定的mibNodeName时

        Examples:
        snmpObj.get('deviceId', 'deviceType')
        """
        super(SnmpV3, self).get(*mibNodeNames)
        oids = []
        for mibNodeName in mibNodeNames:
            oids.append(self.mibName2Oid(mibNodeName) + '.0')

        errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.getCmd(self.usmUserData,
                                                                                self.target,
                                                                                *oids)
        return self.parseResult(errorIndication, errorStatus, errorIndex, varBinds)

    def getNext(self, *mibNodeNames):
        """SNMP的GetNext操作

        Args:
        mibNodeNames (tuple) : 待操作的Mib节点名称列表。如：hwIsmActiveAlarmInfoTable

        Returns:
        返回dict类型的结果。结构为：{oid1_suffix: {symName1: value, symName2: value, ...}, ...}
        如： {'5.65.114.114.97.121.179':
        {'hwIsmActiveAlarmInfoType' : '2',
        'hwIsmActiveAlarmInfoNodeCode' : 'Array',
        'hwIsmActiveAlarmInfoAddtionInfo' : 'The license feature (HyperLock) has expired and entered the trial period. It will become invalid the day after 2015-10-05.',
        'hwIsmActiveAlarmInfoOccurTime' : '0x07df080a11341000',
        'hwIsmActiveAlarmInfoLocationInfo' : 'FeatureName=HyperLock,Trial-Date=2015-10-05',
        'hwIsmActiveAlarmInfoLevel' : '2',
        'hwIsmActiveAlarmInfoAlarmID' : '4039704578',
        'hwIsmActiveAlarmInfoLocalAlarmID' : '4039704578',
        'hwIsmActiveAlarmInfoTitle' : 'License Has Expired',
        'hwIsmActiveAlarmInfoCategory' : '1',
        'hwIsmActiveAlarmInfoRestoreAdvice': 'Purchase and import required license files.',
        'hwIsmActiveAlarmInfoSerialNo' : '179'
        },
        ...
        }

        Raises:
        NoSuchObjectError : 当查询不到指定的mibNodeName时

        Examples:
        1. 获取单个节点
        snmpObj.getNext('hwIsmActiveAlarmInfoTable')
        2. 一次获取多个节点
        snmpObj.getNext('hwIsmActiveAlarmInfoTable', 'hwIsmTrapTargetAddrTable')
        """
        super(SnmpV3, self).getNext(*mibNodeNames)
        oids = []
        for mibNodeName in mibNodeNames:
            oids.append(self.mibName2Oid(mibNodeName))

        errorIndication, errorStatus, errorIndex, varBindTable = self.cmdGen.nextCmd(self.usmUserData,
                                                                                     self.target,
                                                                                     *oids)
        return self.parseResult(errorIndication, errorStatus, errorIndex, varBindTable)

    def getBulk(self, nonRepeaters, maxRepetitions, *mibNodeNames):
        """SNMP的GetBulk操作

        Args:
        nonRepeaters (int) : mibNodeName中的前nonRepeaters个变量，当作普通的getNext报文来处理
        maxRepetitions (int) : mibNodeName中的前nonRepeaters个变量之外的变量，当作重复maxRepeatitions次的getNext报文来处理
        mibNodeNames (tuple) : 待操作的Mib节点名称列表。如：hwIsmActiveAlarmInfoTable

        Returns:
        返回dict类型的结果。结构为：{oid1_suffix: {symName1: value, symName2: value, ...}, ...}
        如： {'5.65.114.114.97.121.179':
        {'hwIsmActiveAlarmInfoType' : '2',
        'hwIsmActiveAlarmInfoNodeCode' : 'Array',
        'hwIsmActiveAlarmInfoAddtionInfo' : 'The license feature (HyperLock) has expired and entered the trial period. It will become invalid the day after 2015-10-05.',
        'hwIsmActiveAlarmInfoOccurTime' : '0x07df080a11341000',
        'hwIsmActiveAlarmInfoLocationInfo' : 'FeatureName=HyperLock,Trial-Date=2015-10-05',
        'hwIsmActiveAlarmInfoLevel' : '2',
        'hwIsmActiveAlarmInfoAlarmID' : '4039704578',
        'hwIsmActiveAlarmInfoLocalAlarmID' : '4039704578',
        'hwIsmActiveAlarmInfoTitle' : 'License Has Expired',
        'hwIsmActiveAlarmInfoCategory' : '1',
        'hwIsmActiveAlarmInfoRestoreAdvice': 'Purchase and import required license files.',
        'hwIsmActiveAlarmInfoSerialNo' : '179'
        },
        ...
        }

        Raises:
        NoSuchObjectError : 当查询不到指定的mibNodeName时

        Examples:
        1. 获取单个节点
        snmpObj.getBulk(0, 1, 'hwIsmActiveAlarmInfoTable')
        2. 一次获取多个节点
        snmpObj.getBulk(0, 1, 'hwIsmActiveAlarmInfoTable', 'hwIsmTrapTargetAddrTable')
        """
        super(SnmpV3, self).getBulk(nonRepeaters, maxRepetitions, *mibNodeNames)
        oids = []
        for mibNodeName in mibNodeNames:
            oids.append(self.mibName2Oid(mibNodeName))

        errorIndication, errorStatus, errorIndex, varBindTable = self.cmdGen.bulkCmd(self.usmUserData,
                                                                                     self.target,
                                                                                     nonRepeaters,
                                                                                     maxRepetitions,
                                                                                     *oids)
        return self.parseResult(errorIndication, errorStatus, errorIndex, varBindTable)

    def set(self, *mibNodeNameValuePairs):
        """SNMP的Set操作

        Args:
        mibNodeNameValuePairs (list) : 待设置的节点名称及属性。如：[{'deviceType.0': 'xxx'}]
        注意每个Key的写法为：mibNodeName.suffix。'.suffix'用于确定具体的对象

        Returns:
        存在errorIndication或errorStatus信息时，即操作失败，返回False，否则返回True

        Raises:
        None

        Examples:
        1. 设置单节点属性
        snmpObj.set({'hwPerformanceSwitch.0': 0})
        2. 设置多个单节点属性
        snmpObj.set({'hwPerformanceSwitch.0': 0}, {'hwIsmClearedAlarmConfirm.0': 168})
        3. 设置Table
        对于表来说，RowStatus一列较为特殊，用于表示行的状态，取值1(Active)表示执行修改操作，4(CreateAndGo)表示添加操作，6(Destroy)表示删除
        snmpObj.set({'hwIsmTrapTargetAddrIPAddr.1.48': '100.148.105.108'},
        {'hwIsmTrapTargetAddrPort.1.48': 168},
        {'hwIsmTrapTargetAddrRowStatus.1.48': 1}, #这一行很重要
        {'hwIsmTrapTargetAddrIndex.1.48': 0})
        """
        super(SnmpV3, self).set(mibNodeNameValuePairs)
        valuePairs = []
        for mibNodeNameValuePair in mibNodeNameValuePairs:
            for key, val in mibNodeNameValuePair.items():
                valuePairs.append((self.mibName2Oid(key), val))

        errorIndication, errorStatus, errorIndex, varBindTable = self.cmdGen.setCmd(self.usmUserData,
                                                                                    self.target,
                                                                                    *valuePairs)
        return not self.rawResultHasError(errorIndication, errorStatus, errorIndex, varBindTable)

    def snmpGet(self, index='0',*mibNodeNames):
        """SNMP的Get操作-针对Table表包含多个子节点的OID查询
        index为Table表的索引，先通过getNext方法获取表的index值
        Args:
        *mibNodeName (tuple) : 待操作的Mib节点名称列表。如：hwInfoFileSysID

        Returns:
        返回dict类型的结果。结构为：{oid1_suffix: {symName1: value, symName2: value, ...}, ...}
        如：{'2.54.53': {'hwInfoFileSysID': '65'}}

        Raises:
        NoSuchObjectError : 当查询不到指定的mibNodeName时

        Examples:
        snmpObj.snmpGet(index,'hwInfoFileSysID')
        """
        super(SnmpV3, self).get(*mibNodeNames)
        oids = []
        for mibNodeName in mibNodeNames:
            oids.append(self.mibName2Oid(mibNodeName) + '.' +index)

        errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.getCmd(self.usmUserData,
                                                                                self.target,
                                                                                *oids)
        return self.parseResult(errorIndication, errorStatus, errorIndex, varBinds)