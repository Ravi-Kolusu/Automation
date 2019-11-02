#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：SNMP协议组件的基类，封装各协议的公共方法
版权信息：华为技术有限公司，版本所有(C) 2008-2009
"""

import os
import struct
from pyasn1.type import univ
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi import builder

from Libs import Log
from Libs.Exception.CustomExceptions import InvalidParamException
from Libs.ApiBase import ApiBase

class SnmpBase(ApiBase):
    """封装所有SNMP协议的公共方法
    """
    def __init__(self, userDefineMibsDir=None):
        """SNMP基类的构造函数

        Args:
        userDefineMibDir (str) : (可选参数)用户自定义Mib文件的存放路径，识别文件夹中的*mib.py文件。默认：None

        Returns:
        None

        Raises:
        None

        Examples:
        None
        """
        super(SnmpBase, self).__init__()
        self.logger = Log.getLogger(str(self.__module__))
        self.snmpVersion = self.__class__.__name__
        self.cmdGen = cmdgen.CommandGenerator()
        self.mibBuilder = self.cmdGen.snmpEngine.msgAndPduDsp.mibInstrumController.mibBuilder
        self.__loadUserDefineMibs(userDefineMibsDir)

    def __loadUserDefineMibs(self, userDefineMibsDir):
        """加载用户自定义Mib文件
        Args:
        userDefineMibDir (str) : 用户自定义Mib文件的存放路径，识别文件夹中的*mib.py文件

        Returns:
        None

        Raises:

        Examples:
        None
        """
        self.logger.info('%s load user define mibs from dir:%s' % (self.snmpVersion, userDefineMibsDir))
        if userDefineMibsDir is None:
            return

        if not os.path.exists(userDefineMibsDir):
            raise InvalidParamException('Mibs directory %s not exist.' % userDefineMibsDir)

        modNames = []
        for mibFile in os.listdir(userDefineMibsDir):
            if mibFile.lower().endswith('mib.py'):
                modNames.append(os.path.splitext(mibFile)[0])

        mibSources = self.mibBuilder.getMibSources() + (builder.DirMibSource(userDefineMibsDir),)
        self.mibBuilder.setMibSources(*mibSources)
        self.mibBuilder.loadModules(*modNames)

    def __isTable(self, varBinds):
        """判断SNMP返回的结果是否是Table格式
        """
        return (len(varBinds) > 0 and isinstance(varBinds[0], list))

    def __prettyOutValue(self, value):
        """To fix bug of univ prettyPrint

        BugFix:
        1. prettyPrint() of univ.OctetString can not deal with \r,\n,\t and DateAndTime syntax
        """
        prettyValue = value.prettyPrint()
        # todo: should deal value with mib var syntax
        if isinstance(value, univ.OctetString) and prettyValue.startswith('0x'):
            valueString = univ.OctetString(hexValue=prettyValue[2:])
            if len(valueString) != 8: # DateAndTime value length is 8 or 11, this time deal with 8
                return str(valueString)
            try:
                dt = struct.unpack('>HBBBBBB', str(valueString))
                if len(dt) == 7:
                    return '%d-%02d-%02d/%02d:%02d:%02d' % dt[:-1]
            except:
                self.logger.warn('Unpack byte stream to DateAndTime failed')
        return prettyValue

    def __parseVarBindsToDict(self, varBinds):
        """Parse varBinds of pysnmp result to dict
        """
        result = {}
        for name, val in varBinds:
            modName, symName, suffix = self.oid2MibName(name.prettyPrint())
            value = self.__prettyOutValue(val)
            self.logger.cmdResponse('%s: %s::%s.%s = %s' % (self.snmpVersion, modName, symName, suffix, value))
            if suffix not in result.keys():
                result[suffix] = {}
            result[suffix][symName] = value
        return result

    def get(self, *mibNodeNames):
        """SNMP的Get操作，在子类中实现

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
        self.logger.cmd('%s Get:%s' % (self.snmpVersion, mibNodeNames))
        pass

    def getNext(self, *mibNodeNames):
        """SNMP的GetNext操作，在子类中实现

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
        self.logger.cmd('%s GetNext:%s' % (self.snmpVersion, mibNodeNames))
        pass

    def getBulk(self, nonRepeaters, maxRepetitions, *mibNodeNames):
        """SNMP的GetBulk操作，在子类中实现

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
        self.logger.cmd('%s GetBulk:%s' % (self.snmpVersion, mibNodeNames))
        pass

    def set(self, *mibNodeNameValuePairs):
        """SNMP的Set操作，在子类中实现

        Args:
        mibNodeNameValuePairs (list) : 待设置的节点名称及属性。如：[{'deviceType.0': 'xxx'}]
        注意每个Key的写法为：mibNodeName.suffix。.suffix用于确定具体的对象

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
        self.logger.cmd('%s Set:%s' % (self.snmpVersion, mibNodeNameValuePairs))
        pass

    def mibName2Oid(self, mibNodeName):
        """将Mib名称转换成OID

        Args:
        mibNodeName (str) : 待操作的Mib节点名称。如：deviceId

        Returns:
        oid (str) : 转换后的OID。如：1.3.6.1.4.1.34774.4.1.1.1

        Raises:
        NoSuchObjectError : 当查询不到指定的mibNodeName时

        Examples:
        oid = snmpObj.mibName2Oid('deviceId')
        """
        mibNodeNameItems = mibNodeName.split('.')
        symbol = mibNodeNameItems[0]
        mibNodeNameSuffix = mibNodeName.replace(symbol, '')
        oid, label, suffix = self.cmdGen.mibViewController.getNodeNameByDesc(symbol)
        new_oid = '.'.join(map(str, oid)) + mibNodeNameSuffix
        nodePath = '/'.join(label) + mibNodeNameSuffix
        self.logger.debug('%s convert mib node name:"%s" to oid:"%s", node path:"%s"' %
        (self.snmpVersion, mibNodeName, new_oid, nodePath))
        return new_oid

    def oid2MibName(self, oid):
        """将OID转换成Mib符号名

        Args:
        oid (str) : 转换后的OID。如：1.3.6.1.4.1.34774.4.1.1.1

        Returns:
        (modName, synName, suffix) (tuple) : oid对应的模块名，符号名，后缀信息。如：

        Raises:
        NoSuchObjectError : 当查询不到指定的oid时

        Examples:
        oid = snmpObj.oid2MibName('1.3.6.1.4.1.34774.4.1.1.1')
        > (ISM-STORAGE-SVC-MIB, deviceId, 0)

        """
        modName, symName, suffix = self.cmdGen.mibViewController.getNodeLocation(tuple(map(int, oid.split('.'))))
        return (modName, symName, '.'.join(map(str, suffix)))

    def parseResult(self, errorIndication, errorStatus, errorIndex, varBinds):
        """解析SNMP操作的返回结果

        Args:
        errorIndication (Exception) : SNMP引擎级错误指示信息
        errorStatus (pyasn1) : SNMP PDU级错误指示信息
        errorIndex (int) : SNMP PDU级错误信息在varBinds中的位置
        varBinds (list) : 返回结果的列表

        Returns:
        返回dict类型的结果。结构为：{oid_suffix: {symName1: value, symName2: value, ...}}
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
        None

        Examples:
        None
        """
        result = {}
        if self.rawResultHasError(errorIndication, errorStatus, errorIndex, varBinds):
            return result

        if not self.__isTable(varBinds):
            return self.__parseVarBindsToDict(varBinds)

        for varBindTableRow in varBinds:
            for key, val in self.__parseVarBindsToDict(varBindTableRow).items():
                if key not in result.keys():
                    result[key] = val
                else:
                    result[key].update(val)
        return result

    def rawResultHasError(self, errorIndication, errorStatus, errorIndex, varBinds):
        """判断SNMP的返回结果中是否包含错误信息

        Args:
        errorIndication (Exception) : SNMP引擎级错误指示信息
        errorStatus (pyasn1) : SNMP PDU级错误指示信息
        errorIndex (int) : SNMP PDU级错误信息在varBinds中的位置
        varBinds (list) : 返回结果的列表

        Returns:
        存在errorIndication或errorStatus信息时，返回True，否则返回False

        Raises:
        None

        Examples:
        None
        """
        if errorIndication:
            self.logger.error('%s error: %s' % (self.snmpVersion, str(errorIndication)))
            return True

        if errorStatus:
            try:
                self.logger.debug('rawResultHasError errorIndex: %s' % str(errorIndex))
                self.logger.debug('rawResultHasError varBinds type: %s' % type(varBinds))
                self.logger.debug('rawResultHasError varBinds length: %s' % len(varBinds))
                varBindsIsTable = self.__isTable(varBinds)
                if varBindsIsTable:
                    self.logger.error('%s: %s at %s' %
                    (self.snmpVersion,
                    errorStatus.prettyPrint(),
                    varBinds[-1][int(errorIndex)-1]))
                else:
                    self.logger.error('%s: %s at %s' % (self.snmpVersion,
                                                        errorStatus.prettyPrint(),
                                                        errorIndex and varBinds[int(errorIndex)-1] or '?'))
            except:
                pass
            return True
        return False

    def getAuthProtocolType(self, userInputAuthProtocolType):
        """认证密码的加密协议转换函数
        """
        protocolMap = {'MD5' : cmdgen.usmHMACMD5AuthProtocol,
                       'SHA' : cmdgen.usmHMACSHAAuthProtocol,
                       'NONE': cmdgen.usmNoAuthProtocol}
        userInputAuthProtocolType = str(userInputAuthProtocolType).upper()
        if protocolMap.has_key(userInputAuthProtocolType):
            return protocolMap[userInputAuthProtocolType]
        else:
            return cmdgen.usmNoAuthProtocol

    def getPrivProtocolType(self, userInputPrivProtocolType):
        """加密密码的加密协议转换函数
        """
        protocolMap = {'AES128' : cmdgen.usmAesCfb128Protocol,
                       'AES192' : cmdgen.usmAesCfb192Protocol,
                       'AES256' : cmdgen.usmAesCfb256Protocol,
                       'DES' : cmdgen.usmDESPrivProtocol,
                       '3DES' : cmdgen.usm3DESEDEPrivProtocol,
                       'NONE' : cmdgen.usmNoPrivProtocol}

        userInputPrivProtocolType = str(userInputPrivProtocolType).upper()
        if protocolMap.has_key(userInputPrivProtocolType):
            return protocolMap[userInputPrivProtocolType]
        else:
            return cmdgen.usmNoPrivProtocol