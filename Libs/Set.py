#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: Set类，测试套接口定义, 测试用例管理

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

"""

import re
from random import choice
from threading import Semaphore, Lock

from Libs import Parameter
from UniAutos import Log
from Libs.TypeCheck import validateParam
from Libs.Exception.CustomExceptions import ValueException
from Libs.Exception.CustomExceptions import TypeException
from Libs.ParamUtil import TYPE
from Libs.TEST_STATUS import TEST_STATUS


class Set(object):
    """测试套类

    功能说明：定义测试套接口.

    Args：
    testSetParameter (dict): 测试控制器传入的test set的参数.

    Attributes:
    self.caseData (dict) : 测试套中测试用例保存的测试数据.
    self.controller (instance) : 测试控制器.
    self.customParams (list) : 测试套XML文件中配置的参数.
    self.parameters (dict) : 测试套的参数, 字典元素为Parameter对象.
    self.identities (dict) : 一组测试套的ID信息.
    self.logDir (str) : 测试套日志存放的目录.
    self.name (str) : 测试套名称.
    self.testCases (list) : 测试套中的测试用例对象集合列表.
    self.postSetActions (list) : 测试套测试完成后需要执行的操作集合列表.
    self.preSetActions (list) : 测试套测试前需要执行的操作集合列表.
    self.runningTest (instance) : 正在执行的测试用例对象.
    self.runHistory (list) : 测试套中已经执行过的测试用例对象集合列表.
    self.status (str) : 测试套状态.

    Returns:
    Set (instance): Set对象实例.

    Notes:
    testSetParameter参数格式如下定义：
    testSetParameter = {"name": {type: str, optional => 1},
    "identity": {type: dict},
    "hooks": {type: list}, # 暂存
    "tests": {type: list},
    "log_dir": {type: str},
    "test_set_params": {type: dict, optional => 1},
    };

    Examples:
    testSetParams = {"name": "Common Test",
    "identities": {"name": "code", "id": "TS_S_01"},
    "hooks": None,
    "tests": ["Test1", "Test2", "Test3"],
    "log_dir": "C:\/",
    "test_set_params": {},
    }

    testSetObj = Set(testSetParams)

    Changes：
    2015-4-23 h90006090 1、增加属性self.setParams 用于存放测试套xml文件中配置的参数.
    2、self.parameters用于存放测试套参数对象，修改为默认为空.

    """
    @validateParam(testSetParameter=dict)
    def __init__(self, testSetParameter):
        self.caseData = {}
        self.engine = None
        self.testCaseMutex = Lock() # case互斥锁，用于case并发时通信.

        self.customParams = testSetParameter["test_set_params"]
        self.parameters = {}
        if self.customParams:
            self.setParameter(self.customParams)

        self.identities = testSetParameter["identities"]
        self.logDir = testSetParameter["log_dir"]
        self.name = testSetParameter["name"]
        self.testCases = testSetParameter["tests"]
        self.hooks = testSetParameter["hooks"]
        self.deps = testSetParameter.get("deps", None)
        for hook in self.hooks:
            hook.setTestSet(self)
        self.postSetActions = []
        self.preSetActions = []
        self.runningTest = None
        self.runHistory = []
        self.status = TEST_STATUS.NOT_RUN
        self.startTime = '1990-01-01 01:01:01'
        self.endTime = '1990-01-01 01:01:01'
        self.__id = testSetParameter.get('id')
        self.__detail = testSetParameter.get('detail')
        # use to uniAutos web platform, execute by jenkins e2e flow
        self.guid = testSetParameter.get('guid')
        self.reachedMaximumTcNumber = 0
        for tc in self.testCases:
            tc.setTestSet(self)

        self.logger = Log.getLogger(self.__class__.__name__)
        self.caseDataSemaphore = Lock()
        if self.getParameter('parallel')['parallel'] is True:
            Log.setConfig(isMultithreading=True)

        # random fault data
        self.__randomFaults = {}
        self.__randomFaultLock = Lock()
        self.__currentRandomFault = None

    @property
    def detail(self):
        return self.__detail

    @property
    def id(self):
        return self.__id

    @property
    def randomFaults(self):
        """Get all random faults.
        """
        return self.__randomFaults

    def setRandomFault(self, faultName, faultCount):
        """Set specify random fault.
        """
        self.__randomFaultLock.acquire()
        self.__randomFaults[faultName] = faultCount
        self.__randomFaultLock.release()

    def setRandomFaults(self, randomFault):
        """Set all random faults
        """
        self.__randomFaultLock.acquire()
        self.__randomFaults = randomFault
        self.__randomFaultLock.release()

    def __setCurrentRandomFault(self):
        """Set current fault, if current fault is None.
        """
        if self.__currentRandomFault is not None:
            return
        faults = []
        for _fault in self.__randomFaults:
            if self.__randomFaults[_fault] > 0:
                faults.append(_fault)
        if faults:
            self.__currentRandomFault = choice(faults)
            self.__reduceRandomFaultCount(self.__currentRandomFault)

    def __reduceRandomFaultCount(self, faultName):
        """current fault count reduce.
        """
        self.__randomFaultLock.acquire()
        self.__randomFaults[faultName] -= 1
        self.__randomFaultLock.release()

    @property
    def currentRandomFault(self):
        """generate current fault and return.
        """
        self.__setCurrentRandomFault()
        return self.__currentRandomFault

    def resetCurrentRandomFault(self):
        """just for current fault have been used.
        """
        self.__currentRandomFault = None

    def caseMutexAcquire(self):
        """申请case互斥锁.

        Examples:
        在用例中使用self.testSet.caseMutexAcquire()
        """
        self.testCaseMutex.acquire()

    def caseMutexRelease(self):
        """释放case互斥锁

        Examples:
        在用例中使用self.testSet.caseMutexRelease()
        """
        self.testCaseMutex.release()

    def setEngine(self, testEngine):
        """设置test set的controller

        Args:
        testEngine (instance): 测试对象.

        Examples:
        testSetObj.setEngine(EngineObj)

        """
        self.engine = testEngine
        from Libs import Group
        for case in self.testCases:
            if isinstance(case, Group):
                case.setEngine(testEngine)

    @validateParam(history=list)
    def setRunHistory(self, history):
        """设置test set中已经运行的test

        Args:
        runHistory (list): 测试套中已经运行的, 需要记录的测试用例集合列表.

        Examples:
        testSetObj.setRunHistory([Test1Obj, Test2Obj])

        """
        self.runHistory.extend(history)

    @validateParam(testSetStatus=str)
    def setStatus(self, testSetStatus):
        """设置test set的状态

        Args:
        testSetStatus (str): 测试套状态

        Raises:
        ValueException: 传入的状态错误.

        Examples:
        testSetObj.setStatus(Complete)

        """
        if not re.match(r'^(Running|NotRun|Complete|Incomplete)', testSetStatus, re.IGNORECASE):
            raise ValueException("Set test set Status Fail. input status(%s) Error. " % testSetStatus)

        self.status = testSetStatus

    def setParameter(self, customParamList=None):
        """设置test set的parameter

        Args:
        paramList (list): 传入的test set的参数， 列表元素是key为"name"和"value"组成的字典, 默认为None.
        paramList 通常为self.setParams.

        Raises:
        ValueException: Parameter由于参数值不合法、类型错误导致设置失败，抛出异常.

        Notes:
        传入参数的key，验证传入前验证.

        Examples:
        testSetObj.setParameter()

        Changes:
        2015-04-23 h90006090 增加默认参数设置.
        2015-05-18 h90006090 优化设置Parameter值设置双重循环

        """
        # DURATION - Used by UniAuto::Controller::RatsEngine
        self.addParameter(name='duration',
                          description='Duration to run for',
                          default_value='0H',
                          type=TYPE.TIME,
                          display_name='Duration',)

        # PARALLEL - Indicates whether to run tests in parallel
        self.addParameter(name='parallel',
                          description='If to run tests in parallel',
                          default_value=False,
                          type=TYPE.BOOLEAN,
                          display_name='Parallel',)

        self.addParameter(name='random',
                          description='If to run tests in parallel, Use cases run out of order.',
                          default_value=False,
                          type=TYPE.BOOLEAN,
                          display_name='Random',)

        # BBT - Indicates whether to run tests in bbt
        self.addParameter(name='bbt',
                          description='If to run tests in bbt',
                          default_value=False,
                          type=TYPE.BOOLEAN,
                          display_name='bbt',)

        self.addParameter(name='wait_between_cases',
                          description='Wait time between bbt cases with dependency',
                          default_value=60,
                          type='number',
                          display_name='wait seconds betwwen bbt case',)

        # 传入的参数为空
        if not customParamList:
            return

        hasInvalidParam = False

        for param in customParamList:
            if param["name"] in self.parameters:
                parameterObj = self.parameters[param["name"]]
                try:
                    parameterObj.setValue(param["value"])
                except (ValueException, TypeException):
                    logMessage = "Test Set Parameter: {name} has been set to an invalid value. ".format(name=param["name"])
                    self.logger.error(logMessage)
                    hasInvalidParam = True

                # 如果值设置为空
                if parameterObj.isOptional() and parameterObj.getValue() is None:
                    logMessage = "A value for Test Set Parameter: {name} must be specified. ".format(name=param["name"])
                    self.logger.error(logMessage)
                    hasInvalidParam = True

        if hasInvalidParam:
            raise ValueException('One or more Test Set parameters are invalid, please check log for more information.')

    def getParameter(self, *args):
        """获取指定名字的parameter 的value，未指定名字时返回全部.

        Args:
        args (list or None): 1个或多个需要获取value的parameter的name，或者不指定返回全部.

        Return:
        paramValue (dict): key为指定的name， value为parameter value的字典。

        Raises:
        ValueException: 需要获取的parameter不存在.

        Examples:
        1、返回全部的parameter：
        getParameter();

        2、返回指定名称的parameter:
        getParameter("name1", "name2")
        """
        paramValue = {}

        # 如果未指定需要返回value的parameter name
        if not args:
            for key in self.parameters:
                paramValue[key] = self.parameters[key].getValue()
            return paramValue

        for reqName in args:
            if reqName not in self.parameters:
                raise ValueException("parameter name: '%s' does not exist. " % reqName)

            paramValue[reqName] = self.parameters[reqName].getValue()
        return paramValue

    def addParameter(self, **kwargs):
        """添加test set的parameter

        Args:
        **kwargs : 测试套参数，为关键字参数，键值对说明如下：
        name (str): parameter的名称, 必选参数.
        display_name (str): parameter的显示名称, 可选参数.
        description (str): parameter的描述信息，可选参数.
        default_value (parameterType): parameter的默认值，可选参数，优先级最低.
        type (str): parameter的值类型，由ParameterType定义，必选参数取值范围为:
        -Boolean、IpAddress、List、Number、Select、Size、Text、
        -Time、Multiple_(Boolean、IpAddress、List、Number、
        -Select、Size、Text、Time).
        identity (str): parameter的标识.
        assigned_value (parameterType): parameter设置值，优先级高于default_value，可选参数.
        optional (bool): parameter的值是否时可选的，可选参数，不传入值时默认为False.

        Notes:
        1、传入参数的格式必须为：
        name='fs_type', # 必要参数.
        display_name='filesystem type',
        description='ext3 or ext2 or mixed',
        default_value='ext3',
        validation={'valid_values': ['ext3, ext2']},
        type='select', # 必要参数.
        identity='id1',
        assigned_value='ext2',
        optional=True # 必须是布尔型，不给定时默认为True.

        Examples:
        addParameter(name='fs_type',
        display_name='filesystem type',
        description='ext3 or ext2 or mixed',
        default_value='ext3',
        validation={'valid_values': ['ext3', 'ext2']},
        type='select',
        identity='id1',
        assigned_value='ext2',
        optional=True)
        """
        paramObj = Parameter(kwargs)

        if paramObj.name in self.parameters:
            raise ValueException("%s: add parameter Fail, parameter: '%s' already exists. " % (self.name, paramObj.name))

        if not paramObj.isOptional() and paramObj.getValue() is None:
            raise ValueException("%s: add parameter Fail, parameter: '%s' is optional parameter, must be set a value. " % (self.name, paramObj.name))

        self.parameters[paramObj.name] = paramObj

    @validateParam(identityName=str)
    def getIdentity(self, identityName):
        """获取指定类型的identities值

        Args:
        identityName (str): 需要检索的ID类型, 一般建议指定identities取名为如下值：

        ax_id: TestSet的ID, 用于TestSet数据更新关联.
        cycle_id:
        project: 项目名称.
        domain: 域名.
        team_name: 组名.
        user_email: 邮箱.

        Returns:
        self.identities[idType] (int|str|list|dict): 指定ID类型的值.

        Examples:
        testSetObj.getIdentity("ax_id")

        Changes:
        2015-05-12 h90006090 增加self.identities为None时的处理.

        """
        if self.identities is None:
            return None
        elif identityName in self.identities:
            return self.identities[identityName]
        else:
            self.logger.trace("Requested identity: %s does not exist in the test set. " % identityName)
            return None

    def getTmssId(self):
        """get case tmss id.
        Returns:
        tmssId (str): case tmss id.
        """
        return self.getIdentity('tmss_id')

    def getTmssUri(self):
        """get case tmss Uri.
        Returns:
        tmssUri (str): case tmss Uri.
        """
        return self.getIdentity('uri')

    @validateParam(saveData=dict)
    def saveData(self, savedData):
        """保存test case的测试数据，test case中调用.

        Args:
        caseData (dict): 需要保存的测试用例的数据, 为任意值, 参考Examples.

        Examples:
        testSetObj.saveData("lunData": {"lunType": "thick", "size": "12GB"})

        """

        # saveData 控制Case保存caseData， 同一时间只允许一个Case保存数据.
        self.caseDataSemaphore.acquire()
        try:
            for key in savedData:
                self.caseData[key] = savedData[key]
        except Exception:
            self.logger.info("Save Test Set Data Error, data: %s" % savedData)
        finally:
            self.caseDataSemaphore.release()

    def getData(self, dataNames=None):
        """获取caseData中指定名称(key)的数据.

        Args:
        dataNames (list): 保存的测试数据的key列表.

        Returns:
        tmpData (dict): 获取的caseData中指定名称(key)的数据， 包括key和value.

        Examples:
        testSetObj.getData(["LunData"])
        """
        tmpData = {}
        self.caseDataSemaphore.acquire()
        try:
            if dataNames is None:
                tmpData = self.caseData
            else:
                for key in dataNames:
                    if key in self.caseData:
                        tmpData[key] = self.caseData[key]
        except Exception:
            self.logger.error("Get Test Set data error, dataNames: %s" % dataNames)
        finally:
            self.caseDataSemaphore.release()
        return tmpData

    @validateParam(postActions=list)
    def addPostSetActions(self, postActions):
        """添加需要在test set结束时执行的操作

        Args:
        postActions (list): test set结束时执行的操作的集合列表， 列表的元素为function或可执行的代码段（str）.

        Notes:
        1、若postActions中的列表元素为function, 则不能传入参数，需要的参数操作处理在function定义中实现.
        2、postActions中的操作执行的顺序为: 从最后一个列表元素依次向前执行.如：
        postActions = [Action1, Action2, Action3, ], 先执行Action3, 其次为Action2，最后为Action1.

        Examples:
        def createLun():
        pass

        func = "print 'This is PostTest' "
        postActions = [createLun, func]
        self.addPostSetActions(postActions)

        """
        self.postSetActions.extend(postActions)

    @validateParam(preActions=list)
    def addPreSetActions(self, preActions):
        """添加需要在test set开始时执行的操作

        Args:
        preActions (list): test set开始时执行的操作的集合列表， 列表的元素为function或可执行的代码段(str).

        Notes:
        1、若preActions中的列表元素为function, 则不能传入参数，需要的参数操作处理在function定义中实现.
        2、preActions中的操作执行的顺序为: 从最后一个列表元素依次向前执行.如：
        preActions = [Action1, Action2, Action3, ], 先执行Action3, 其次为Action2，最后为Action1.

        Examples:
        def deleteLun():
        pass

        func = "print 'This is PreTest' "
        preActions = [deleteLun, func]
        self.addPreSetActions(preActions)

        """
        self.preSetActions.extend(preActions)

    def runPreSetActions(self):
        """执行test set执行前需要执行的操作

        函数执行是一个堆栈操作，最后添加到PreSetActions的第一个执行.

        Examples:
        testSetObj.runPreSetActions()

        """
        # todo 执行前的其他操作
        # 执行preSetActions
        if self.preSetActions:
            self.logger.info("Performing Test Defined Pre Test Set Actions. ")
        else:
            self.logger.info("Test Set have not Pre Test Set Actions. ")
            return

        while len(self.preSetActions):
            preAction = self.preSetActions.pop()
            # preAction为函数
            if hasattr(preAction, '__call__'):
                # 没有具体的Exception可以捕获.
                try:
                    preAction()
                except Exception, error:
                    self.logger.error("Pre Test Action threw an exception: %s" % error)
            # preAction为可执行的代码段
            elif isinstance(preAction, str):
                # 没有具体的Exception可以捕获.
                try:
                    exec preAction
                except Exception, error:
                    self.logger.error("Pre Test Action threw an exception: %s" % error)

    def runPostSetActions(self):
        """执行test set执行后需要执行的操作

        函数执行是一个堆栈操作，最后添加到PreSetActions的第一个执行.

        Examples:
        testSetObj.runPostSetActions()

        """
        # todo 执行前的其他操作
        # 执行preSetActions
        if self.postSetActions:
            self.logger.info("Performing Test Defined Post Test Set Actions. ")
        else:
            self.logger.info("Test Set have not Post Test Set Actions. ")
            return

        while len(self.postSetActions):
            postAction = self.postSetActions.pop()
            # postAction为函数
            if hasattr(postAction, '__call__'):
                # 没有具体的Exception可以捕获.
                try:
                    postAction()
                except Exception, error:
                    self.logger.error("Post Test Action threw an exception: %s" % error)
            # postAction为可执行的代码段
            elif isinstance(postAction, str):
                # 没有具体的Exception可以捕获.
                try:
                    exec postAction
                except Exception, error:
                    self.logger.error("Post Test Action threw an exception: %s" % error)

    def setCurrentlyRunningTest(self):
        """设置当前测试套中正在执行的测试用例
        Examples:
        self.setCurrentlyRunningTest()

        """
        self.runningTest = self.engine.currentlyRunningTest

    def addHooks(self, hookObjectList):
        """添加hook对象到测试套对象中.

        Args:
        hookObjectList (list): Hook对象列表.

        """
        for hook in hookObjectList:
            hook.setTestSet(self)
            if hook not in self.hooks:
                self.hooks.append(hook)

if __name__ == "__main__":
    pass


