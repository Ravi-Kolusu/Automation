#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: 用于测试用例控制，测试用例执行，为并发执行用例的控制提供接口定义.

版权信息: 华为技术有限公司，版权所有(C) 2014-2015.

修改记录: 2015/4/25 胡伟 90006090 created

"""
import os
import sys
import datetime
import time
import yaml
import threading
import re
import traceback
import uuid
import hashlib

from UniAutos.Util.Threads import Threads
from UniAutos.Util.Units import Units
from UniAutos.Util.TypeCheck import validateParam
from UniAutos import Log
from UniAutos.TestEngine.Parameter import Parameter
from UniAutos.Exception.ValueException import ValueException
from UniAutos.Exception.TypeException import TypeException
from UniAutos.Exception.HookException import HookException
from UniAutos.TestEngine.Configuration import Configuration
from UniAutos.TestEngine.Base import Base
from UniAutos.Util.TestStatus import *
from UniAutos.TestEngine.Case import Case
from UniAutos.TestEngine.Group import Group
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Requirement.ConfigureEnv import applyConfig
from UniAutos.Util.HostMonitor import HostMonitor
from UniAutos.TestEngine import TestStatusData

# 修改默认编码模式, 避免ASCII编码字符流处理集太小导致的问题
try:
    reload(sys)
    sys.setdefaultencoding('utf-8')
except:
    pass


class Engine(object):
    """测试引擎.

    用于执行测试套，测试用例.

    Args:
    engineParam (dict): 测试引擎参数， 包含测试套对象、测试引擎在主配置文件中的配置数据, 键值对说明如下:
    test_set (UniAutos.TestEngine.Set.Set): 测试套实例对象.
    params (list) : 测试引擎参数, 在主配置文件中配置的全局参数, 默认为空列表.

    Attributes：
    self.testSet (instance) : 测试套对象.
    self.customParams (list) : 主配置文件中配置的Engine参数.
    self.parameter (dict) : Engine的parameter， 初始值为空，由setParameter()接口添加.
    self.testCase (list) : 测试套中配置的测试用例对象列表.
    self.logLevel (str) : 当前日志级别.
    self.stopOnError (bool) : 是否在测试执行遇到错误时停止.
    self.testSetId: (str) : 测试套的Id.
    self.logRotationSize: (str) : 单个日志文件最大Size.
    self.configStopOnError (bool) : 配置执行遇到错误时是否停止.
    self.monitorInterval (str) :监控间隔时间，UniAutos Size类型.
    self.logMaxSize (str) : 日志最大保存的容量.
    self.runTestsInParallelFlag (bool) : 是否单次并发执行.
    self.isTestSetError (bool) : 测试套执行错误标记.
    self.totalTestCounter (int) : 记录用例执行的次数.

    self.tidToTcName (dict) : 线程ID和TestCase名称的映射.
    self.tidToTcObject (dict) : 线程ID和TestCase对象的映射.
    self.globalTestStatus (dict) : TestCase对象全局状态.
    self.tidToTcLogs (dict) : 线程ID和TestCase日志文件名称的映射.

    self.timeLineLogFileHandler (fileHandler) : timeline.html文件句柄.
    self.EngineLogFileName (str) : Engine日志文件名称.
    self.currentRunningTestThreads (list) : 当前正在运行的测试用例线程列表.
    self.postTestSetExecuted (bool) : 测试套是否执行标记.
    self.statusLogFileHandler (fileHandler) : status.yaml文件句柄.

    self.logger (Log): 日志对象.

    Returns:
    Engine (instance): 测试引擎实例对象.

    Examples:
    engineObj = Engine(engineParam)

    """
    def __init__(self, engineParam):
        super(Engine, self).__init__()
        self.__uuid = hashlib.new('md5', Log.LogFileDir + 'Main_Rollup').hexdigest()
        self.statusDb = engineParam["statusdb"]
        self.testSet = engineParam["test_set"]
        self.testSetId = self.testSet.getIdentity("tmss_id")
        self.customParams = engineParam["params"]
        self.parameters = {}
        self.testCases = self.testSet.testCases
        self.startTime = None
        self.stopOnError = False
        self.logRotationSize = None
        self.configStopOnError = False
        self.monitorInterval = None
        self.logMaxSize = None
        self.runTestsInParallelFlag = False
        self.isTestSetError = False
        self.totalTestCounter = 0 # 记录用例执行的次数.
        self.tidToTcName = {} # 线程ID和TestCase名称的映射.
        self.tidToTcObject = {} # 线程ID和TestCase对象的映射.
        self.globalTestStatus = {} # TestCase对象全局状态.
        self.tidToTcLogs = {} # 线程ID和TestCase日志文件名称的映射.
        self.timeLineLogFileHandler = None
        self.EngineLogFileName = None
        self.currentRunningTestThreads = []
        self.currentlyRunningTest = None
        self.postTestSetExecuted = 0
        self.testSetStartTime = time.time()
        self.logger = Log.getLogger(self.__module__)
        self.setParameter(self.customParams)
        self.logLevel = self.getParameter("logging_level").get("logging_level")
        self.testSet.setEngine(self)
        # self.__initStatusLogFile()
        self.webUrl = self.testSet.getIdentity('uniweb_platform_url')

    def _initStatusLogFile(self):
        """初始化写入status.db
        遍历所有的测试用例、测试套， 初始化写入初始的用例和测试套状态.
        """
        # 写入测试用例状态.
        for tc in self.testCases:
            if isinstance(tc, Configuration):
                what = "configuration"
            elif isinstance(tc, Case):
                what = "case"
            elif isinstance(tc, Group):
                what = "group"
            else:
                what = None
            _uuid = hashlib.new('md5', Log.LogFileDir + tc.name).hexdigest()
            tc.statusUuid = _uuid
            _dbStatus = {"_uuid": _uuid,
                         "_status": TEST_STATUS.NOT_RUN,
                         "_what": what,
                         "_id": self._getIdentityOfTest(tc),
                         "_name": tc.name,
                         "_stage": 'init_case',
                         "_duration": '0S'}
        self.statusDb.save(**_dbStatus)

    def _initSpecStatusDb(self, name, _uuid):
        _uuid = str(_uuid)
        _dbStatus = {"_start": datetime.datetime.now(),
                     "_uuid": _uuid,
                     "_name": name,
                     "_duration": '0S'}
        self.statusDb.save(**_dbStatus)

    def _initTcStatusDb(self, tc, _uuid):
        if isinstance(tc, Configuration):
            what = "configuration"
        elif isinstance(tc, Case):
            what = "case"
        elif isinstance(tc, Group):
            what = "group"
        else:
            what = None

        _uuid = str(_uuid)
        tc.statusUuid = _uuid
        _dbStatus = {"_uuid": _uuid,
                     "_status": TEST_STATUS.NOT_RUN,
                     "_what": what,
                     "_id": self._getIdentityOfTest(tc),
                     "_name": tc.name,
                     "_stage": 'init_case',
                     "_duration": '0S'}
        self.statusDb.save(**_dbStatus)

    def applyRequirement(self, configObject, tcObject):
        """"""
        if not configObject.device:
            raise InvalidParamException("Have not Invalid Device to ApplyConfig.")
        applyConfig(configObject, tcObject)

    @staticmethod
    def serialLogResult(tc, postReason):
        """串行执行或者单次并发时记录测试数据到result.html中.
        Args:
        tc (Case): 测试用例.
        postReason (str): 测试用例postTestCase失败的原因.
        """
        Log.TestCaseStatusLogger.logTestCaseStatus(name=tc.name,
                                                   status=tc.caseStatus,
                                                   start=tc.startTime,
                                                   end=tc.endTime,
                                                   reason=tc.failureReason if tc.caseStatus not in [TEST_STATUS.COMPLETE,
                                                                                                    TEST_STATUS.CONFIGURED,
                                                                                                    TEST_STATUS.DE_CONFIGURED,
                                                                                                    TEST_STATUS.PASS] else '',
                                                   tmss_id=tc.getTmssId(),
                                                   post=postReason,
                                                   times=0)

    def _runTest(self, testCase, tcLogFile):
        """运行单个测试用例, 该函数主要用于执行用例中preTestCase、procedure、postTestCase中的测试步骤.

        Args:
        testCase (Case): 测试用例对象.
        tcLogFile (str): 测试用例日志文件名称.
        """
        _start = _end = datetime.datetime.now()
        postReason = ''

        _dbStatus = {'_end': _end,
                     '_start': _start,
                     '_stage': 'running',
                     '_post_status': TEST_STATUS.NOT_RUN,
                     '_status': TEST_STATUS.RUNNING}
        self.statusDb.update(testCase.statusUuid, **_dbStatus)

        # 打印测试用例开始日志，开始执行测试用例.
        self.logger.tcStart()
        # 2015/09/28 h90006090 Add test case startTime use to tmss fillback.
        testCase.setStartTime(_start.strftime('%Y-%m-%d %H:%M:%S'))
        testCase.setCaseStatus(TEST_STATUS.RUNNING)
        self.globalTestStatus[testCase.name]["status"] = testCase.caseStatus
        self.serialLogResult(testCase, postReason)
        testCase.logger.info("###PRE-TEST-CASE: %s ###" % testCase.name)

        # 执行preTestCase, 如果执行失败TestCase执行失败.
        _preTestCasePassFlag = False
        try:
            self.runHooks('beforePreTest')
            testCase.preTestCase()
            self.runHooks("afterPreTest")
        # 如果配置的hook设置了stop_on_error, hook会抛出HookException
        # 如果抛出异常后进行处理, 如果抛出的是Hook异常，证明没有用例异常
        except HookException, errorMsg:
            Log.MainLogger.fail("%s Run Hook Failed. \nError: %s" % (testCase.name, errorMsg))
            self._handleException(testCase, errorMsg, 'pre')
        except Exception, errorMsg:
            self._handleException(testCase, errorMsg, "pre")
            Log.MainLogger.fail("%s Pre Test Failed. " % testCase.name)
            # 非Hook失败，经过handle处理走到这一步骤，证明没有配置stopOnError， 故这里执行runHook需要捕获异常
            try:
                self.runHooks("afterPreTest", tc=testCase) # parameter tc for collect log.
            except HookException:
                self.logger.error("%s Run Hook Failed. \nError: %s" % (testCase.name, traceback.format_exc()))
        else:
            _preTestCasePassFlag = True
            testCase.logger.passInfo("%s Pre TestCase Passed. " % testCase.name)

        # 执行测试用例procedure, 如果preTestCase执行失败则直接跳过，同时mainTestCasePassFlag为False.
        if _preTestCasePassFlag:
            testCase.logger.info("###MAIN###")
            try:
                self.runHooks('beforeProcedure', tc=testCase)
                testCase.procedure()
                self.runHooks("afterProcedure")
            except HookException, errorMsg:
                Log.MainLogger.fail("%s Run Hook Failed. \nError: %s" % (testCase.name, errorMsg))
                self._handleException(testCase, errorMsg, 'main')
            except Exception, errorMsg:
                self._handleException(testCase, errorMsg, "main")
                Log.MainLogger.fail("%s Main Test Failed. " % testCase.name)
                # 非Hook失败，经过handle处理走到这一步骤，证明没有配置stopOnError， 故这里执行runHook需要捕获异常
                try:
                    self.runHooks("afterProcedure", tc=testCase) # parameter tc for collect log.
                except HookException:
                    self.logger.error("%s Run Hook Failed. \nError: %s" % (testCase.name, traceback.format_exc()))
            else:
                testCase.logger.passInfo("%s Main Test has Passed" % testCase.name)
                if not self.runTestsInParallelFlag:
                    Log.MainLogger.passInfo("%s Main Test Passed. " % testCase.name)
                    testCase.setCaseStatus(TEST_STATUS.PASS)

        # 不管preTestCase和procedure是否执行成功，都要执行postTestCase.
        self.logger.info("###POST-TEST-CASE###")
        try:
            # h90006090 2018/03/01 Add: Post运行情况记录，方便Hook或其他接口进行其他操作
            testCase.setPostStatus(TEST_STATUS.RUNNING)
            testCase.postTestCase()
            self.runHooks("afterPostTest", tc=testCase)
        except HookException, errorMsg:
            Log.MainLogger.fail("%s Run Hook Failed. \nError: %s" % (testCase.name, errorMsg))
            self._handleException(testCase, errorMsg, 'post')
        except Exception, errorMsg:
            self._handleException(testCase, errorMsg, "post")
            postReason = errorMsg.message
            # 非Hook失败，经过handle处理走到这一步骤，证明没有配置stopOnError， 故这里执行runHook需要捕获异常
            try:
                self.runHooks("afterPostTest", tc=testCase) # parameter tc for collect log.
            except HookException:
                self.logger.error("%s Run Hook Failed. \nError: %s" % (testCase.name, traceback.format_exc()))
        else:
            testCase.logger.passInfo("%s Post TestCase Passed" % testCase.name)
            _dbStatus = {'_post_status': TEST_STATUS.PASS,}
            if self.runTestsInParallelFlag:
                self.globalTestStatus[testCase.name]["status"] = testCase.caseStatus

        if self.runTestsInParallelFlag:
            duration = str(time.time() - self.globalTestStatus[testCase.name]["start_time"]) + "S"
        else:
            duration = str(time.time() - self.startTime) + "S"
        _end = datetime.datetime.now()
        _dbStatus.update({"_stage": 'done',
                          "_duration": duration,
                          "_end": _end,
                          "_status": testCase.caseStatus})
        self.statusDb.update(testCase.statusUuid, **_dbStatus)

        if self.runTestsInParallelFlag:
            self.globalTestStatus[testCase.name]["end_time"] = time.time()
        testCase.logger.tcEnd()
        # 2015/09/28 h90006090 Add test case end time use to tmss fill back.
        testCase.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
        self.serialLogResult(testCase, postReason)
        Log.releaseFileHandler(Log.LogType.TestCase, tcLogFile)

    def _runConfiguration(self, configuration, tcLogFile):
        """运行Configuration对象, 适用与串行执行的测试套.
        Args:
        configuration (UniAutos.TestEngine.Configuration.Configuration): 测试配置对象.
        """
        _start = _end = datetime.datetime.now()
        configuration.setStartTime(_start.strftime('%Y-%m-%d %H:%M:%S'))
        testName = configuration.name
        self.logger.tcStart('TestConfig %s starts' % testName)
        self.runHooks('beforeConfig')

        _status = {'_stage': 'running',
                   '_status': TEST_STATUS.RUNNING,
                   '_start': _start,
                   '_end': _end}
        self.statusDb.update(configuration.statusUuid, **_status)

        # 如果参数为Config执行Config
        if configuration.getParameter('Mode')['Mode'] == 'Config':
            self.logger.info('####CONFIGURATION MODE####')
            try:
                configuration.runConfiguration()
            except Exception, err:
                self.logger.error("Config Script failed: \n %s, \nDetail: %s" % (err.message, traceback.format_exc()))
                self._handleException(configuration, err, 'main')
            else:
                configuration.setCaseStatus(TEST_STATUS.CONFIGURED)
                self.logger.tcEnd('%s has been successfully configured' % testName)
        # 如果参数为DeConfig执行DeConfig
        elif configuration.getParameter('Mode')['Mode'] == 'DeConfig':
            self.logger.info('####DE-CONFIGURATION MODE####')
            try:
                configuration.deConfiguration()
            except Exception, err:
                self.logger.error("Config Script failed: \n %s, \nDetail: %s" % (err.message, traceback.format_exc()))
                self._handleException(configuration, err, 'main')
            else:
                configuration.setCaseStatus(TEST_STATUS.DE_CONFIGURED)
                self.logger.tcEnd('%s has been successfully de-configured' % testName)
        _end = datetime.datetime.now()
        _status = {'_duration': str(time.time() - self.startTime) + "S",
                   '_status': configuration.caseStatus,
                   '_stage': 'done',
                   '_end': _end}
        self.statusDb.update(configuration.statusUuid, **_status)
        configuration.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
        self.runHooks('afterConfig')
        Log.releaseFileHandler(Log.LogType.TestCase, tcLogFile)

    def _runTestParallel(self, testCase):
        """并发串行时，执行单个用例.
        Args:
        testCase (instance): 测试用例对象.
        """

        # 设置开始时间.
        self.globalTestStatus[testCase.name]["start_time"] = time.time()

        # 线程id与日志文件关联.
        tcLogFile = testCase.name
        self.tidToTcLogs[threading.current_thread().ident] = tcLogFile + "---0"
        Log.changeLogFile(Log.LogType.TestCase, tcLogFile)
        testCase.logCaseDetailInfo()
        testCase.logParameter()

        # 运行单个测试
        self.tidToTcObject[threading.current_thread().ident] = testCase
        self._runTest(testCase, tcLogFile)

    @staticmethod
    def createImageLinks():
        """创建timeline文件中图片的链接

        Returns:
        imageLink (dict): 图片链接的字典集合.

        Examples:
        imageLink = self.createImageLinks()

        """
        # 定义图片连接
        startPass = ''
        startFail = ''
        endPass = ''
        endFail = ''
        endKilled = ''
        containedPass = ''
        containedFail = ''
        empty = ''
        runningPass = ''
        runningFail = ''
        bigEmpty = ''
        return {"startPass": startPass, "startFail": startFail, "endPass": endPass,
                "endFail": endFail, "endKilled": endKilled, "containedPass": containedPass,
                "containFail": containedFail, "empty": empty, "runningPass": runningPass, "runningFail": runningFail,
                "bigEmpty": bigEmpty}

    def _checkTestCaseThreadStatus(self, timeSinceLastStatus):
        """轮询测试用例线程状态, 以便做出相应的动作

        遍历检查线程的状态，如果线程已经消亡, 检查线程对应的用例的状态，如果用例状态Fail，则终止线程.

        Args:
        timeSinceLastStatus (str): 最后一次轮询状态的时间.

        Examples:
        self._checkTestCaseThreadStatus(timeSinceLastStatus)

        """
        runningTestCount = len(self.currentRunningTestThreads)
        # 当线程数量大于0时轮询.
        while runningTestCount > 0:
            for index in range(len(self.currentRunningTestThreads) - 1, -1, -1):
                th = self.currentRunningTestThreads[index]
                # 线程消亡才执行状态检查.
                if not th.isAlive():
                    # 如果当前用例已经消亡，即从正在运行的Case中移除.
                    self.currentRunningTestThreads.pop(index)
                    # 线程消亡后，线程数量递减.
                    runningTestCount -= 1
                # 如果线程消亡，但是测试用例的状态为Not_Run证明，在运行前且在等待Dependency时发生错误.
                if re.match(r'' + str(TEST_STATUS.NOT_RUN) + '', self.tidToTcObject[th.ident].caseStatus) and th.errorMsg != '':
                    self.logger.error("Test case %s: [Thread ID: %s] threw an error, Maybe check case dependency error.\n, %s" % (self.tidToTcName[th.ident], th.ident, th.errorMsg))
                # 线程消亡. 用例状态只有PASS和失败，只要非PASS则证明用例失败.
                if re.match(r'' + str(TEST_STATUS.FAILED) + '|' + str(TEST_STATUS.CONFIG_ERROR) + '', self.tidToTcObject[th.ident].caseStatus):
                    self.logger.error("Test case %s: [Thread ID: %s] threw an error, please click the related link to see detail. \n" % (self.tidToTcName[th.ident], th.ident))
                    # 如果用例失败, 且配置了StopOnError, 且存在其他线程依然存活，则杀掉存活的线程，并设置用例状态.
                    if self.stopOnError:
                        self.logger.info("StopOnError is set so Controller is going to kill all the remaining tests")
                        for thChild in self.currentRunningTestThreads:
                            if thChild.isAlive():
                                # 如果当前用例为Group优先kill掉Group中正在执行的用例.
                                if isinstance(self.tidToTcObject[thChild.ident], Group):
                                    self.globalTestStatus[self.tidToTcName[thChild.ident]]["status"] = TEST_STATUS.FAILED
                                    self.globalTestStatus[self.tidToTcName[thChild.ident]]["end_time"] = time.time()
                                    self.tidToTcObject[thChild.ident].killAllAliveTestCases()
                                    # if current thread's case status is not fail or pass,
                                    # the case status will be set to killed
                                    self.killTestThread(self.tidToTcObject[thChild.ident], thChild)
                                    # update time line data
                                    self.globalTestStatus[self.tidToTcName[thChild.ident]].update({"status": self.tidToTcObject[thChild.ident].caseStatus,
                                                                                                   "end_time": time.time()})
                                    # if killed will be set result to result.html.
                                    self.serialLogResult(self.tidToTcObject[thChild.ident], '')

                        # 如果已经执行杀线程， 再次进行检测， 线程是否全部消亡.
                        for thChild in self.currentRunningTestThreads:
                            if thChild.isAlive():
                                thChild.join() # 如果没有消亡则等待消亡.
                        self.logger.debug('Finished Or Exit thread %s' % thChild.ident)

                        runningTestCount = 0 # 正在运行的线程直接赋值为0， 退出循环.
                        self.updateStatus()
                        break
                # 如果线程存活，则每隔5分钟记录以及Timeline.
                if (time.time() - 300) >= timeSinceLastStatus:
                    self.makeTimeLog()
                    timeSinceLastStatus = time.time()
            time.sleep(1)
        # 等待线程全部执行完成.
        self.waitAllTestComplete(self.currentRunningTestThreads)
        # 退出后打印最后的用例状态.
        for th in self.currentRunningTestThreads:
            logLink = "Log Link :: %s" % self.tidToTcLogs[th.ident]
            self.logger.info("Test case %s : %s. \n Thread Id: %s.\n %s" % (self.tidToTcName[th.ident],
                                                                            self.globalTestStatus[self.tidToTcName[th.ident]]["status"],
                                                                            th.ident,
                                                                            logLink))
    def writeCssStyleToTimeLog(self, durationStr, controllerLink, width, fh=None):
        """并发执行时, 将css样式写入TimeLine.html文件

        Args:
        durationStr (str): 运行总时长.
        controllerLink (str): controller日志文件链接.
        width (int): timeline表格中的单元格默认宽度.

        Examples:
        self.writeCssStyleToTimeLog(durationStr, controllerLink, width)
        """
        cssStr = """
        <!DOCTYPE html>
        <html>
        <style>
        .quick-nav {
        position: relative;
        background-color: #FFFFFF;
        font-size: 9px;
        -moz-border-radius: 0px;
        -webkit-border-radius: 0px;
        width: %spx;
        }
        .quick-nav table th.skew {
        height: 80px;
        width: 40px;
        position: relative;
        vertical-align: bottom;
        }
        .quick-nav table th.skew > div {
        position: relative;
        top: 0px;
        left: 30px;
        height: 100%%;
        transform:skew(-45deg,0deg);
        -ms-transform:skew(-45deg,0deg);
        -moz-transform:skew(-45deg,0deg);
        -webkit-transform:skew(-45deg,0deg);
        -o-transform:skew(-45deg,0deg);
        overflow: hidden;
        border-top: 1px solid #CCCCCC;
        border-left: 1px solid #CCCCCC;
        border-right: 1px solid #CCCCCC;
        }
        .quick-nav table th.skew span {
        transform:skew(45deg,0deg) rotate(315deg);
        -ms-transform:skew(45deg,0deg) rotate(315deg);
        -moz-transform:skew(45deg,0deg) rotate(315deg);
        -webkit-transform:skew(45deg,0deg) rotate(315deg);
        -o-transform:skew(45deg,0deg) rotate(315deg);
        position: absolute;
        bottom: 5px;
        left: 0px;
        display: inline-block;
        width: 15px;
        text-align: left;
        }
        .quick-nav table td {
        width: 15px;
        height: 15px;
        text-align: center;
        vertical-align: middle;
        border: 1px solid #CCCCCC;
        padding: 0px 0px;
        }
        </style>
        <body>
        <h4>PARALLEL Time Chart</h4>
        Total Runtime: %s
        <br>
        %s
        <br>
        <br>
        <div class='quick-nav>
        <table cellspacing="0">
        <thead>
        """ % (width, durationStr, controllerLink)
        if not fh:
            self.timeLineLogFileHandler.write(cssStr)
            return
        fh.write(cssStr)

    def _handleException(self, testCase, exceptionMsg, stage, **kwargs):
        """测试用例执行异常时的错误处理
        Args:
        testCase (Case): 测试用例对象.
        exceptionMsg (Exception): 用例异常错误信息.
        stage (str): 测试用例执行的阶段, 如：pre, main, post.
        """
        _now = time.time()
        _datetimeEnd = datetime.datetime.now()
        _end = _datetimeEnd.strftime('%Y-%m-%d %H:%M:%S')
        name = testCase.name
        what = None
        if isinstance(testCase, Case):
            what = "test_case"
        elif isinstance(testCase, Configuration):
            what = "configuration"
        # 设置用例失败原因.
        testCase.setFailureReason("""Test Stage: %s ; Status: Failed ; Reason: %s""" % (stage, exceptionMsg))
        # 用例对象为configuration.
        if what == "configuration":
            testCase.setCaseStatus(TEST_STATUS.FAILED)
            testCase.logError("%s Failed, Because an issue occurred while trying to run the test configuration: %s \n" % (name, exceptionMsg))
        # stage为pre.
        elif stage == "pre":
            if not isinstance(exceptionMsg, HookException):
                testCase.setCaseStatus(TEST_STATUS.CONFIG_ERROR)
            else:
                testCase.setCaseStatus(TEST_STATUS.NOT_RUN)
            if self.runTestsInParallelFlag:
                self.globalTestStatus[name]["status"] = TEST_STATUS.FAILED
            testCase.logError("An issue occurred while trying to run the preTestCase steps for %s : \n" % name, exceptionMsg)
        # stage为main.
        elif stage == "main":
            if not isinstance(exceptionMsg, HookException):
                testCase.setCaseStatus(TEST_STATUS.FAILED)
            if self.runTestsInParallelFlag:
                self.globalTestStatus[name]["status"] = TEST_STATUS.FAILED
            testCase.logError("%s Failed, Because an issue occurred while trying to run the test case: \n" % name, exceptionMsg)
            testCase.incrementErrorCount()
        # stage为post.
        elif stage == "post":
            testCase.logError("An issue occurred while trying to run the postTestCase steps for %s :\n." % name, exceptionMsg)
            # h90006090 2018/03/01 Add: Post运行情况记录，方便Hook或其他接口进行其他操作
            testCase.setPostStatus(TEST_STATUS.FAILED)
            _status = {'_post_status': TEST_STATUS.FAILED}
            self.statusDb.update(testCase.statusUuid, **_status)

    def _updateStatusIfDie():
        if self.runTestsInParallelFlag and isinstance(testCase, Case):
            duration = str(_now - self.globalTestStatus[testCase.name]["start_time"]) + "S"
        else:
            duration = str(_now - self.startTime) + "S"

        _status = {'_end': _datetimeEnd,
                   '_duration': duration,
                   '_stage': 'done',
                   '_status': testCase.caseStatus}
        self.statusDb.update(testCase.statusUuid, **_status)
        self.setTestSetError(True)
        # todo configuration in group, FOR BBT
        if (isinstance(testCase, Configuration) and self.configStopOnError) or self.stopOnError:
            def __die(errorType):
                # update current case status
                _updateStatusIfDie()
                # if exit ,must set end time first.
                testCase.setEndTime(_end)

                # 如果不是抛出的hook异常
                if not isinstance(exceptionMsg, HookException) or stage != 'post':
                # 可能会存在抛异常的hook，但是这里不能再抛出异常，需要记录数据
                    try:
                        self.runHooks('afterPostTest', tc=testCase)
                    except HookException:
                        self.logger.error("%s Run Hook Failed. \nError: %s" % (testCase.name, traceback.format_exc()))

                # h90006090 2017/05/28 http://10.183.61.55/oceanstor-autotest/UniAutos/issues/1653
                postReason = ''
                if stage == 'post':
                    postReason = exceptionMsg.message
                self.serialLogResult(testCase, postReason)

                self.logger.warn("Engine Told me %s!" % errorType)
                self.postTestSet()
                # self.runHooks('afterPostTestSet')

                _duration = time.time() - self.testSetStartTime
                msg = '\nTest Set Duration: %sS\nTest Set Result:\n' % _duration
                testCases = getattr(self, 'bbtTestCases') if hasattr(self, 'bbtTestCases') else self.testCases
                for tc in testCases:
                    if isinstance(tc, Group):
                        msg += "TestGroup: %s, Status: %s\n" % (tc.name, tc.caseStatus)
                    else:
                        msg += "TestCase: %s, Status: %s\n" % (tc.name, tc.caseStatus)

                self.logger.info(msg)

                self.logger.warn("TestSet Set %s, Now Exit UniAutos!" % errorType)
                self.updateStatus()
                Log.releaseResource()
                os._exit(1)

        if isinstance(testCase, Configuration) and self.configStopOnError:
            __die('configStopOnError')

        if self.runTestsInParallelFlag and isinstance(testCase, Case):
            self.globalTestStatus[testCase.name]["end_time"] = _now

        if not self.runTestsInParallelFlag:
            __die('StopOnError')

    def _getIdentityOfTest(self, tcObject, identityName="tmss_id"):
        """获取指定测试用例对象， 指定identity name的值.
        Args:
        tcObject (instance): 测试用例对象.
        identityName (str): 用例唯一标识的名称, 默认为"tmss_id".

        Returns:
        identity (str): 用例的唯一标识ID.

        Examples:
        tcId = self._getIdentityOfTest(tc)

        """
        identityDict = {"name": identityName}
        if tcObject.hasIdentity(identityDict):
            identities = tcObject.getIdentity(identityDict)
            for identity in identities:
                if identity["name"] == identityName:
                    return identity["id"]
        else:
            self.logger.trace("Identity %s does not exist for %s " % (identityName, tcObject.name))
            return ''

    def killTestThread(self, testCase, th):
        """杀死指定用例的线程

        Args:
        testCase (instance): 测试用例对象.
        th (thread Handle): 线程句柄.

        Examples:
        self.killTestThread(tc, th)

        """
        if th.ident in self.tidToTcLogs:
            Log.changeLogFile(Log.LogType.TestCase, re.sub(r'---0$', "", self.tidToTcLogs[th.ident]))
            self.logger.info("Controller Told me Stop! \nThread ID: %s" % th.ident)
            Log.releaseFileHandler(Log.LogType.TestCase, re.sub(r'---0$', "", self.tidToTcLogs[th.ident]))
            Log.changeLogFile(Log.LogType.Main, "Controller")

            # TestCase Kill的时候需要设置结束时间.
            testCase.setCaseEndTime(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            if isinstance(testCase, Group):
                testCase.setCaseStatus(TEST_STATUS.FAILED)
        else:
        # 如果为Case类的对象，需要判断当前Case对象的状态，如果已经失败或者成功则状态为成功或者失败，
        # 否则设置状态为Killed.
        status = TEST_STATUS.KILLED \
        if testCase.caseStatus not in [TEST_STATUS.FAILED,
        TEST_STATUS.CONFIG_ERROR,
        TEST_STATUS.NOT_RUN,
        TEST_STATUS.PASS] else testCase.caseStatus
        testCase.setCaseStatus(status)
        th.kill()

        def addExecutionParameters(self, **kwargs):
        """添加Engine的测试参数

        Args:
        kwargs : 测试引擎参数, 为关键字参数，键值对说明如下：
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

        Attributes:
        paramObj (instance): parameter对象.

        Raises:
        ValueException: 添加参数时，参数已经存在，或参数值未指定.

        Examples:
        self.addExecutionParameters(name='stop_on_error',
        description='If set to a true value, it will '
        'stop execution of all the tests '
        'in the test set when an error '
        'is encountered.',
        default_value=1,
        type='BOOLEAN',
        display_name='Stop on Error',
        )

        """
        paramObj = Parameter(kwargs)

        if paramObj.name in self.parameters:
        raise ValueException("Add parameter Fail, "
        "parameter: '%s' already exists. " % paramObj.name)

        if not paramObj.isOptional() and paramObj.getValue() is None:
        raise ValueException("Add parameter Fail, parameter: '%s' "
        "is optional parameter, must be set a value. " % paramObj.name)

        self.parameters[paramObj.name] = paramObj

        def setParameter(self, customParamList=None):
        """设置Engine测试参数

        Args:
        customParamList (list): 在测试床中配置的参数列表.

        Raises:
        ValueException: 添加测试床配置的参数失败.

        Examples:
        self.setParameter(self.customParams)

        Changes:
        2015-05-18 h90006090 优化设置Parameter值设置双重循环

        """
        # STOP_ON_ERROR
        self.addExecutionParameters(name='stop_on_error',
        description='If set to a true value, it will '
        'stop execution of all the tests '
        'in the test set when an error '
        'is encountered.',
        default_value=1,
        type='BOOLEAN',
        display_name='Stop on Error')
        # LOGGING_LEVEL
        self.addExecutionParameters(name='logging_level',
        description='Logging level for the messages to '
        'be displayed on the screen',
        default_value='INFO',
        validation={"valid_values": ['TRACE', 'DEBUG',
        'CMD', 'INFO', 'WARN', 'ERROR',
        'STATUS', 'FATAL', 'OFF'],
        },
        type='select',
        display_name='Logging Level')

        # LOG_ROTATION_SIZE
        self.addExecutionParameters(name='log_rotation_size',
        description='The size threshold for the log files'
        'beyond which the log files are rotated',
        default_value='60MB',
        type='SIZE',
        display_name='Log Rotation Size')

        # MAX_LOG_SIZE
        self.addExecutionParameters(name='max_log_size',
        description='The max size of the log files for a case',
        default_value='-1MB',
        type='SIZE',
        display_name='Max Log Size')

        # STOP_ON_CONFIG_ERROR
        # stop_on_config_error can be set in the main config xml file.
        # it will act as the test set level value (can be override by test config)
        self.addExecutionParameters(name='stop_on_config_error',
        description='If set to a true value, it will '
        'stop execution of all the tests '
        'in the test set when an error '
        'is encountered.',
        default_value=0,
        type='BOOLEAN',
        display_name='Stop on Config Error')

        # MONITOR_INTERVAL
        self.addExecutionParameters(name='monitor_interval',
        description='The interval in UniAuto time unit '
        'to specify how often to get the monitor sample',
        default_value='0S',
        type='time',
        display_name='Monitor Interval')

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
        logMessage = "Test Set Parameter: {name} has been set to " \
        "an invalid value. ".format(name=param["name"])
        self.logger.error(logMessage)
        hasInvalidParam = True

        # 如果值设置为空
        if parameterObj.isOptional() and parameterObj.getValue() is None:
        logMessage = "A value for Test Set Parameter: {name} " \
        "must be specified. ".format(name=param["name"])
        self.logger.error(logMessage)
        hasInvalidParam = True

        if hasInvalidParam:
        raise ValueException('One or more Test Set parameters are invalid, please check log '
        'for more information.')

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

        def createTestCaseLogFile(self, tcName):
        """创建测试用例的日志文件

        Args:
        tcName (str): 测试用例名称.

        Returns:
        testCaseLogFileName (str): 测试用例日志文件名称.

        Examples:
        logFileName = self.createTestCaseLogFile(TC_1)
        """

        return tcName + "-" + str(self.totalTestCounter)
        # return re.sub(r'-[0-9]*$', "", tcName) + "-" + str(self.totalTestCounter)

        @staticmethod
        def getTimeStamp():
        """按格式获取当前时间戳

        Returns:
        timeStamp (str): 当前时间的格式化时间字符串. 格式为: %Y_%m_%d_%H-%M-%S.

        Examples:
        timeStamp = self.getTimeStamp()

        """
        return datetime.datetime.now().strftime('%Y_%m_%d_%H-%M-%S-%f')

        @validateParam(status=bool)
        def setTestSetError(self, status):
        """设置测试套是否为Error

        Args:
        status (bool): 传入的测试套状态信息.

        Examples:
        self.setTestSetError(True)

        """
        self.isTestSetError = status

        def makeTimeLog(self, controllerFail=None):
        """创建Time Log HTML文件, 并写入TimeLine数据

        Args:
        controllerFail (bool): 引擎错误标记, 默认为空, 在Rats中使用.

        Examples:
        self.makeTimeLog()

        """
        # 默认设置Controller.html的连接为绿色，状态为空， 当存在用例执行失败时设置为红色，状态为Failed.
        color = "green"
        status = ""

        # globalTestStatus的遍历在线程创建，且globalTestStatus初始化后，并且size不会改变，仅值改变可以不用加锁.
        for tcName in self.globalTestStatus:
        if re.match(r'' + str(TEST_STATUS.FAILED) + '|' + str(TEST_STATUS.CONFIG_ERROR) + '',
        self.globalTestStatus[tcName]["status"]):
        color = "red"
        status = "---FAILED"
        break

        controllerLink = "" \
        "View Controller Log %s" % (color, status)

        # 遍历所有用例设置测试开始时间和结束时间
        earliest = None
        latest = None
        for tcName in self.globalTestStatus:
        if self.globalTestStatus[tcName]["status"] == TEST_STATUS.RUNNING:
        self.globalTestStatus[tcName]["end_time"] = time.time()
        if earliest is None or (self.globalTestStatus[tcName]["start_time"] < earliest):
        earliest = self.globalTestStatus[tcName]["start_time"]
        if latest is None or (self.globalTestStatus[tcName]["end_time"] > latest):
        latest = self.globalTestStatus[tcName]["end_time"]
        if not (earliest and latest):
        self.logger.debug("There is not enough runtime to generate the timeline log yet. "
        "\n startTime:%s \n latestTime: %s" % (str(earliest), str(latest)))
        return

        # 创建timeLine日志文件.
        self.setupTimeLog()

        # 设置用例执行时间
        duration = latest - earliest

        days = int(duration / (24 * 60 * 60))
        hours = int((duration / (60 * 60)) % 24)
        minutes = int((duration / 60) % 60)
        seconds = int(duration % 60)
        durationStr = "{Days},{HH}:{MM}:{SS}".format(Days=days,
        HH=hours,
        MM=minutes,
        SS=seconds)
        # 计算每个表格的元素长度.
        cellDuration = None # 单个单元格的宽度.
        numberOfCells = None # 单元格的个数.

        def hasMultipleDuration(startTime, endTime, tcDict):
        for tc in tcDict:
        durationCnt = 0
        if tcDict[tc]["start_time"] >= startTime and tcDict[tc]["end_time"] 1:
        return False
        return True

        def cDurationExc():

        for cDuration in range(1, 1200):
        if cDuration * cells >= duration:
        tmp = earliest
        while tmp

        =======================

        #!/usr/bin/python
        # -*- coding: UTF-8 -*-

        """
        
        功 能: 用于测试用例控制，测试用例执行，为并发执行用例的控制提供接口定义.
        
        版权信息: 华为技术有限公司，版权所有(C) 2014-2015.
        
        修改记录: 2015/4/25 胡伟 90006090 created
        
        """
        import os
        import sys
        import datetime
        import time
        import yaml
        import threading
        import re
        import traceback
        import uuid
        import hashlib

        from UniAutos.Util.Threads import Threads
        from UniAutos.Util.Units import Units
        from UniAutos.Util.TypeCheck import validateParam
        from UniAutos import Log
        from UniAutos.TestEngine.Parameter import Parameter
        from UniAutos.Exception.ValueException import ValueException
        from UniAutos.Exception.TypeException import TypeException
        from UniAutos.Exception.HookException import HookException
        from UniAutos.TestEngine.Configuration import Configuration
        from UniAutos.TestEngine.Base import Base
        from UniAutos.Util.TestStatus import *
        from UniAutos.TestEngine.Case import Case
        from UniAutos.TestEngine.Group import Group
        from UniAutos.Exception.InvalidParamException import InvalidParamException
        from UniAutos.Requirement.ConfigureEnv import applyConfig
        from UniAutos.Util.HostMonitor import HostMonitor
        from UniAutos.TestEngine import TestStatusData

        # 修改默认编码模式, 避免ASCII编码字符流处理集太小导致的问题
        try:
        reload(sys)
        sys.setdefaultencoding('utf-8')
        except:
        pass


        class Engine(object):
        """测试引擎.

        用于执行测试套，测试用例.

        Args:
        engineParam (dict): 测试引擎参数， 包含测试套对象、测试引擎在主配置文件中的配置数据, 键值对说明如下:
        test_set (UniAutos.TestEngine.Set.Set): 测试套实例对象.
        params (list) : 测试引擎参数, 在主配置文件中配置的全局参数, 默认为空列表.

        Attributes：
        self.testSet (instance) : 测试套对象.
        self.customParams (list) : 主配置文件中配置的Engine参数.
        self.parameter (dict) : Engine的parameter， 初始值为空，由setParameter()接口添加.
        self.testCase (list) : 测试套中配置的测试用例对象列表.
        self.logLevel (str) : 当前日志级别.
        self.stopOnError (bool) : 是否在测试执行遇到错误时停止.
        self.testSetId: (str) : 测试套的Id.
        self.logRotationSize: (str) : 单个日志文件最大Size.
        self.configStopOnError (bool) : 配置执行遇到错误时是否停止.
        self.monitorInterval (str) :监控间隔时间，UniAutos Size类型.
        self.logMaxSize (str) : 日志最大保存的容量.
        self.runTestsInParallelFlag (bool) : 是否单次并发执行.
        self.isTestSetError (bool) : 测试套执行错误标记.
        self.totalTestCounter (int) : 记录用例执行的次数.

        self.tidToTcName (dict) : 线程ID和TestCase名称的映射.
        self.tidToTcObject (dict) : 线程ID和TestCase对象的映射.
        self.globalTestStatus (dict) : TestCase对象全局状态.
        self.tidToTcLogs (dict) : 线程ID和TestCase日志文件名称的映射.

        self.timeLineLogFileHandler (fileHandler) : timeline.html文件句柄.
        self.EngineLogFileName (str) : Engine日志文件名称.
        self.currentRunningTestThreads (list) : 当前正在运行的测试用例线程列表.
        self.postTestSetExecuted (bool) : 测试套是否执行标记.
        self.statusLogFileHandler (fileHandler) : status.yaml文件句柄.

        self.logger (Log): 日志对象.

        Returns:
        Engine (instance): 测试引擎实例对象.

        Examples:
        engineObj = Engine(engineParam)

        """

        def __init__(self, engineParam):
        super(Engine, self).__init__()
        self.__uuid = hashlib.new('md5', Log.LogFileDir + 'Main_Rollup').hexdigest()
        self.statusDb = engineParam["statusdb"]
        self.testSet = engineParam["test_set"]
        self.testSetId = self.testSet.getIdentity("tmss_id")

        self.customParams = engineParam["params"]
        self.parameters = {}

        self.testCases = self.testSet.testCases

        self.startTime = None

        self.stopOnError = False
        self.logRotationSize = None
        self.configStopOnError = False
        self.monitorInterval = None
        self.logMaxSize = None
        self.runTestsInParallelFlag = False
        self.isTestSetError = False
        self.totalTestCounter = 0 # 记录用例执行的次数.

        self.tidToTcName = {} # 线程ID和TestCase名称的映射.
        self.tidToTcObject = {} # 线程ID和TestCase对象的映射.
        self.globalTestStatus = {} # TestCase对象全局状态.
        self.tidToTcLogs = {} # 线程ID和TestCase日志文件名称的映射.

        self.timeLineLogFileHandler = None
        self.EngineLogFileName = None
        self.currentRunningTestThreads = []
        self.currentlyRunningTest = None
        self.postTestSetExecuted = 0
        self.testSetStartTime = time.time()

        self.logger = Log.getLogger(self.__module__)
        self.setParameter(self.customParams)
        self.logLevel = self.getParameter("logging_level").get("logging_level")
        self.testSet.setEngine(self)
        # self.__initStatusLogFile()
        self.webUrl = self.testSet.getIdentity('uniweb_platform_url')

        def _initStatusLogFile(self):
        """初始化写入status.db
        遍历所有的测试用例、测试套， 初始化写入初始的用例和测试套状态.
        """
        # 写入测试用例状态.
        for tc in self.testCases:
        if isinstance(tc, Configuration):
        what = "configuration"
        elif isinstance(tc, Case):
        what = "case"
        elif isinstance(tc, Group):
        what = "group"
        else:
        what = None

        _uuid = hashlib.new('md5', Log.LogFileDir + tc.name).hexdigest()
        tc.statusUuid = _uuid
        _dbStatus = {
        "_uuid": _uuid,
        "_status": TEST_STATUS.NOT_RUN,
        "_what": what,
        "_id": self._getIdentityOfTest(tc),
        "_name": tc.name,
        "_stage": 'init_case',
        "_duration": '0S'
        }
        self.statusDb.save(**_dbStatus)

        def _initSpecStatusDb(self, name, _uuid):
        _uuid = str(_uuid)
        _dbStatus = {
        "_start": datetime.datetime.now(),
        "_uuid": _uuid,
        "_name": name,
        "_duration": '0S'
        }
        self.statusDb.save(**_dbStatus)

        def _initTcStatusDb(self, tc, _uuid):
        if isinstance(tc, Configuration):
        what = "configuration"
        elif isinstance(tc, Case):
        what = "case"
        elif isinstance(tc, Group):
        what = "group"
        else:
        what = None

        _uuid = str(_uuid)
        tc.statusUuid = _uuid
        _dbStatus = {
        "_uuid": _uuid,
        "_status": TEST_STATUS.NOT_RUN,
        "_what": what,
        "_id": self._getIdentityOfTest(tc),
        "_name": tc.name,
        "_stage": 'init_case',
        "_duration": '0S'
        }
        self.statusDb.save(**_dbStatus)

        def applyRequirement(self, configObject, tcObject):
        """"""
        if not configObject.device:
        raise InvalidParamException("Have not Invalid Device to ApplyConfig.")
        applyConfig(configObject, tcObject)

        @staticmethod
        def serialLogResult(tc, postReason):
        """串行执行或者单次并发时记录测试数据到result.html中.
        Args:
        tc (Case): 测试用例.
        postReason (str): 测试用例postTestCase失败的原因.
        """
        Log.TestCaseStatusLogger.logTestCaseStatus(
        name=tc.name,
        status=tc.caseStatus,
        start=tc.startTime,
        end=tc.endTime,
        # 2017/05/25 h90006090
        # fix http://10.183.61.55/oceanstor-autotest/UniAutos/issues/1541
        reason=tc.failureReason if tc.caseStatus not in [TEST_STATUS.COMPLETE,
        TEST_STATUS.CONFIGURED,
        TEST_STATUS.DE_CONFIGURED,
        TEST_STATUS.PASS] else '',
        tmss_id=tc.getTmssId(),
        post=postReason,
        times=0)

        def _runTest(self, testCase, tcLogFile):
        """运行单个测试用例, 该函数主要用于执行用例中preTestCase、procedure、postTestCase中的测试步骤.

        Args:
        testCase (Case): 测试用例对象.
        tcLogFile (str): 测试用例日志文件名称.
        """
        _start = _end = datetime.datetime.now()
        postReason = ''

        _dbStatus = {
        '_end': _end,
        '_start': _start,
        '_stage': 'running',
        '_post_status': TEST_STATUS.NOT_RUN,
        '_status': TEST_STATUS.RUNNING}
        self.statusDb.update(testCase.statusUuid, **_dbStatus)

        # 打印测试用例开始日志，开始执行测试用例.
        self.logger.tcStart()
        # 2015/09/28 h90006090 Add test case startTime use to tmss fillback.
        testCase.setStartTime(_start.strftime('%Y-%m-%d %H:%M:%S'))
        testCase.setCaseStatus(TEST_STATUS.RUNNING)
        self.globalTestStatus[testCase.name]["status"] = testCase.caseStatus
        self.serialLogResult(testCase, postReason)
        testCase.logger.info("###PRE-TEST-CASE: %s ###" % testCase.name)

        # 执行preTestCase, 如果执行失败TestCase执行失败.
        _preTestCasePassFlag = False
        try:
        self.runHooks('beforePreTest')
        testCase.preTestCase()
        self.runHooks("afterPreTest")
        # 如果配置的hook设置了stop_on_error, hook会抛出HookException
        # 如果抛出异常后进行处理, 如果抛出的是Hook异常，证明没有用例异常
        except HookException, errorMsg:
        Log.MainLogger.fail("%s Run Hook Failed. \nError: %s" % (testCase.name, errorMsg))
        self._handleException(testCase, errorMsg, 'pre')
        except Exception, errorMsg:
        self._handleException(testCase, errorMsg, "pre")
        Log.MainLogger.fail("%s Pre Test Failed. " % testCase.name)
        # 非Hook失败，经过handle处理走到这一步骤，证明没有配置stopOnError， 故这里执行runHook需要捕获异常
        try:
        self.runHooks("afterPreTest", tc=testCase) # parameter tc for collect log.
        except HookException:
        self.logger.error("%s Run Hook Failed. \nError: %s" % (testCase.name, traceback.format_exc()))

        else:
        _preTestCasePassFlag = True
        testCase.logger.passInfo("%s Pre TestCase Passed. " % testCase.name)

        # 执行测试用例procedure, 如果preTestCase执行失败则直接跳过，同时mainTestCasePassFlag为False.

        if _preTestCasePassFlag:
        testCase.logger.info("###MAIN###")
        try:
        self.runHooks('beforeProcedure', tc=testCase)
        testCase.procedure()
        self.runHooks("afterProcedure")
        except HookException, errorMsg:
        Log.MainLogger.fail("%s Run Hook Failed. \nError: %s" % (testCase.name, errorMsg))
        self._handleException(testCase, errorMsg, 'main')
        except Exception, errorMsg:
        self._handleException(testCase, errorMsg, "main")
        Log.MainLogger.fail("%s Main Test Failed. " % testCase.name)
        # 非Hook失败，经过handle处理走到这一步骤，证明没有配置stopOnError， 故这里执行runHook需要捕获异常
        try:
        self.runHooks("afterProcedure", tc=testCase) # parameter tc for collect log.
        except HookException:
        self.logger.error("%s Run Hook Failed. \nError: %s" % (testCase.name, traceback.format_exc()))
        else:
        testCase.logger.passInfo("%s Main Test has Passed" % testCase.name)
        if not self.runTestsInParallelFlag:
        Log.MainLogger.passInfo("%s Main Test Passed. " % testCase.name)
        testCase.setCaseStatus(TEST_STATUS.PASS)

        # 不管preTestCase和procedure是否执行成功，都要执行postTestCase.
        self.logger.info("###POST-TEST-CASE###")
        try:
        # h90006090 2018/03/01 Add: Post运行情况记录，方便Hook或其他接口进行其他操作
        testCase.setPostStatus(TEST_STATUS.RUNNING)
        testCase.postTestCase()
        self.runHooks("afterPostTest", tc=testCase)
        except HookException, errorMsg:
        Log.MainLogger.fail("%s Run Hook Failed. \nError: %s" % (testCase.name, errorMsg))
        self._handleException(testCase, errorMsg, 'post')
        except Exception, errorMsg:
        self._handleException(testCase, errorMsg, "post")
        postReason = errorMsg.message
        # 非Hook失败，经过handle处理走到这一步骤，证明没有配置stopOnError， 故这里执行runHook需要捕获异常
        try:
        self.runHooks("afterPostTest", tc=testCase) # parameter tc for collect log.
        except HookException:
        self.logger.error("%s Run Hook Failed. \nError: %s" % (testCase.name, traceback.format_exc()))
        else:
        testCase.logger.passInfo("%s Post TestCase Passed" % testCase.name)
        _dbStatus = {
        '_post_status': TEST_STATUS.PASS,
        }
        if self.runTestsInParallelFlag:
        self.globalTestStatus[testCase.name]["status"] = testCase.caseStatus

        if self.runTestsInParallelFlag:
        duration = str(time.time() - self.globalTestStatus[testCase.name]["start_time"]) + "S"
        else:
        duration = str(time.time() - self.startTime) + "S"
        _end = datetime.datetime.now()
        _dbStatus.update({
        "_stage": 'done',
        "_duration": duration,
        "_end": _end,
        "_status": testCase.caseStatus})
        self.statusDb.update(testCase.statusUuid, **_dbStatus)

        if self.runTestsInParallelFlag:
        self.globalTestStatus[testCase.name]["end_time"] = time.time()
        testCase.logger.tcEnd()
        # 2015/09/28 h90006090 Add test case end time use to tmss fill back.
        testCase.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
        self.serialLogResult(testCase, postReason)
        Log.releaseFileHandler(Log.LogType.TestCase, tcLogFile)

        def _runConfiguration(self, configuration, tcLogFile):
        """运行Configuration对象, 适用与串行执行的测试套.
        Args:
        configuration (UniAutos.TestEngine.Configuration.Configuration): 测试配置对象.
        """
        _start = _end = datetime.datetime.now()
        configuration.setStartTime(_start.strftime('%Y-%m-%d %H:%M:%S'))
        testName = configuration.name
        self.logger.tcStart('TestConfig %s starts' % testName)
        self.runHooks('beforeConfig')

        _status = {
        '_stage': 'running',
        '_status': TEST_STATUS.RUNNING,
        '_start': _start,
        '_end': _end
        }
        self.statusDb.update(configuration.statusUuid,
        **_status)

        # 如果参数为Config执行Config
        if configuration.getParameter('Mode')['Mode'] == 'Config':
        self.logger.info('####CONFIGURATION MODE####')
        try:
        configuration.runConfiguration()
        except Exception, err:
        self.logger.error("Config Script failed: \n %s, \nDetail: %s" %
        (err.message, traceback.format_exc()))
        self._handleException(configuration, err, 'main')
        else:
        configuration.setCaseStatus(TEST_STATUS.CONFIGURED)
        self.logger.tcEnd('%s has been successfully configured' % testName)

        # 如果参数为DeConfig执行DeConfig
        elif configuration.getParameter('Mode')['Mode'] == 'DeConfig':
        self.logger.info('####DE-CONFIGURATION MODE####')
        try:
        configuration.deConfiguration()
        except Exception, err:
        self.logger.error("Config Script failed: \n %s, \nDetail: %s" %
        (err.message, traceback.format_exc()))
        self._handleException(configuration, err, 'main')

        else:
        configuration.setCaseStatus(TEST_STATUS.DE_CONFIGURED)
        self.logger.tcEnd('%s has been successfully de-configured' % testName)

        _end = datetime.datetime.now()
        _status = {'_duration': str(time.time() - self.startTime) + "S",
        '_status': configuration.caseStatus,
        '_stage': 'done',
        '_end': _end}
        self.statusDb.update(configuration.statusUuid,
        **_status)

        configuration.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
        self.runHooks('afterConfig')
        Log.releaseFileHandler(Log.LogType.TestCase, tcLogFile)

        def _runTestParallel(self, testCase):
        """并发串行时，执行单个用例.
        Args:
        testCase (instance): 测试用例对象.
        """

        # 设置开始时间.
        self.globalTestStatus[testCase.name]["start_time"] = time.time()

        # 线程id与日志文件关联.
        tcLogFile = testCase.name
        self.tidToTcLogs[threading.current_thread().ident] = tcLogFile + "---0"
        Log.changeLogFile(Log.LogType.TestCase, tcLogFile)
        testCase.logCaseDetailInfo()
        testCase.logParameter()

        # 运行单个测试
        self.tidToTcObject[threading.current_thread().ident] = testCase
        self._runTest(testCase, tcLogFile)

        @staticmethod
        def createImageLinks():
        """创建timeline文件中图片的链接

        Returns:
        imageLink (dict): 图片链接的字典集合.

        Examples:
        imageLink = self.createImageLinks()

        """

        # 定义图片连接

        startPass = ''
        startFail = ''
        endPass = ''
        endFail = ''
        endKilled = ''
        containedPass = ''
        containedFail = ''
        empty = ''
        runningPass = ''
        runningFail = ''
        bigEmpty = ''

        return {"startPass": startPass, "startFail": startFail, "endPass": endPass,
        "endFail": endFail, "endKilled": endKilled, "containedPass": containedPass,
        "containFail": containedFail, "empty": empty, "runningPass": runningPass,
        "runningFail": runningFail, "bigEmpty": bigEmpty}

        def _checkTestCaseThreadStatus(self, timeSinceLastStatus):
        """轮询测试用例线程状态, 以便做出相应的动作

        遍历检查线程的状态，如果线程已经消亡, 检查线程对应的用例的状态，如果用例状态Fail，则终止线程.

        Args:
        timeSinceLastStatus (str): 最后一次轮询状态的时间.

        Examples:
        self._checkTestCaseThreadStatus(timeSinceLastStatus)

        """

        runningTestCount = len(self.currentRunningTestThreads)

        # 当线程数量大于0时轮询.
        while runningTestCount > 0:

        for index in range(len(self.currentRunningTestThreads) - 1, -1, -1):
        th = self.currentRunningTestThreads[index]
        # 线程消亡才执行状态检查.
        if not th.isAlive():
        # 如果当前用例已经消亡，即从正在运行的Case中移除.
        self.currentRunningTestThreads.pop(index)
        # 线程消亡后，线程数量递减.
        runningTestCount -= 1

        # 如果线程消亡，但是测试用例的状态为Not_Run证明，在运行前且在等待Dependency时发生错误.
        if re.match(r'' + str(TEST_STATUS.NOT_RUN) + '', self.tidToTcObject[th.ident].caseStatus) \
        and th.errorMsg != '':
        self.logger.error("Test case %s: [Thread ID: %s] threw an error, "
        "Maybe check case dependency error.\n, %s"
        % (self.tidToTcName[th.ident], th.ident, th.errorMsg))

        # 线程消亡. 用例状态只有PASS和失败，只要非PASS则证明用例失败.
        if re.match(r'' + str(TEST_STATUS.FAILED) + '|' + str(TEST_STATUS.CONFIG_ERROR) + '',
        self.tidToTcObject[th.ident].caseStatus):
        self.logger.error("Test case %s: [Thread ID: %s] threw an error, please click "
        "the related link to see detail. \n" % (self.tidToTcName[th.ident], th.ident))

        # 如果用例失败, 且配置了StopOnError, 且存在其他线程依然存活，则杀掉存活的线程，并设置用例状态.
        if self.stopOnError:
        self.logger.info("StopOnError is set so Controller is going to "
        "kill all the remaining tests")
        for thChild in self.currentRunningTestThreads:
        if thChild.isAlive():

        # 如果当前用例为Group优先kill掉Group中正在执行的用例.
        if isinstance(self.tidToTcObject[thChild.ident], Group):
        self.globalTestStatus[self.tidToTcName[thChild.ident]]["status"] = \
        TEST_STATUS.FAILED
        self.globalTestStatus[self.tidToTcName[thChild.ident]]["end_time"] = time.time()
        self.tidToTcObject[thChild.ident].killAllAliveTestCases()

        # if current thread's case status is not fail or pass,
        # the case status will be set to killed
        self.killTestThread(self.tidToTcObject[thChild.ident], thChild)
        # update time line data
        self.globalTestStatus[self.tidToTcName[thChild.ident]].update(
        {
        "status": self.tidToTcObject[thChild.ident].caseStatus,
        "end_time": time.time()
        })
        # if killed will be set result to result.html.
        self.serialLogResult(self.tidToTcObject[thChild.ident], '')

        # 如果已经执行杀线程， 再次进行检测， 线程是否全部消亡.

        for thChild in self.currentRunningTestThreads:
        if thChild.isAlive():
        thChild.join() # 如果没有消亡则等待消亡.
        self.logger.debug('Finished Or Exit thread %s' % thChild.ident)

        runningTestCount = 0 # 正在运行的线程直接赋值为0， 退出循环.
        self.updateStatus()
        break

        # 如果线程存活，则每隔5分钟记录以及Timeline.
        if (time.time() - 300) >= timeSinceLastStatus:
        self.makeTimeLog()
        timeSinceLastStatus = time.time()

        time.sleep(1)

        # 等待线程全部执行完成.
        self.waitAllTestComplete(self.currentRunningTestThreads)
        # 退出后打印最后的用例状态.
        for th in self.currentRunningTestThreads:
        logLink = "Log Link" \
        "" % self.tidToTcLogs[th.ident]

        self.logger.info("Test case %s : %s. \n Thread Id: %s.\n %s"
        % (self.tidToTcName[th.ident], self.globalTestStatus[self.tidToTcName[th.ident]]["status"],
        th.ident, logLink))

        def writeCssStyleToTimeLog(self, durationStr, controllerLink, width, fh=None):
        """并发执行时, 将css样式写入TimeLine.html文件

        Args:
        durationStr (str): 运行总时长.
        controllerLink (str): controller日志文件链接.
        width (int): timeline表格中的单元格默认宽度.

        Examples:
        self.writeCssStyleToTimeLog(durationStr, controllerLink, width)

        """
        cssStr = """
        
        
        
        .quick-nav {
        position: relative;
        background-color: #FFFFFF;
        font-size: 9px;
        -moz-border-radius: 0px;
        -webkit-border-radius: 0px;
        width: %spx;
        }
        .quick-nav table th.skew {
        height: 80px;
        width: 40px;
        position: relative;
        vertical-align: bottom;
        }
        .quick-nav table th.skew > div {
        position: relative;
        top: 0px;
        left: 30px;
        height: 100%%;
        transform:skew(-45deg,0deg);
        -ms-transform:skew(-45deg,0deg);
        -moz-transform:skew(-45deg,0deg);
        -webkit-transform:skew(-45deg,0deg);
        -o-transform:skew(-45deg,0deg);
        overflow: hidden;
        border-top: 1px solid #CCCCCC;
        border-left: 1px solid #CCCCCC;
        border-right: 1px solid #CCCCCC;
        }
        .quick-nav table th.skew span {
        transform:skew(45deg,0deg) rotate(315deg);
        -ms-transform:skew(45deg,0deg) rotate(315deg);
        -moz-transform:skew(45deg,0deg) rotate(315deg);
        -webkit-transform:skew(45deg,0deg) rotate(315deg);
        -o-transform:skew(45deg,0deg) rotate(315deg);
        position: absolute;
        bottom: 5px;
        left: 0px;
        display: inline-block;
        width: 15px;
        text-align: left;
        }
        .quick-nav table td {
        width: 15px;
        height: 15px;
        text-align: center;
        vertical-align: middle;
        border: 1px solid #CCCCCC;
        padding: 0px 0px;
        }
        
        
        PARALLEL Time Chart
        Total Runtime: %s
        
        %s
        
        
        
        
        
        """ % (width, durationStr, controllerLink)
        if not fh:
        self.timeLineLogFileHandler.write(cssStr)
        return
        fh.write(cssStr)

        def _handleException(self, testCase, exceptionMsg, stage, **kwargs):
        """测试用例执行异常时的错误处理
        Args:
        testCase (Case): 测试用例对象.
        exceptionMsg (Exception): 用例异常错误信息.
        stage (str): 测试用例执行的阶段, 如：pre, main, post.
        """
        _now = time.time()
        _datetimeEnd = datetime.datetime.now()
        _end = _datetimeEnd.strftime('%Y-%m-%d %H:%M:%S')
        name = testCase.name

        what = None
        if isinstance(testCase, Case):
        what = "test_case"
        elif isinstance(testCase, Configuration):
        what = "configuration"

        # 设置用例失败原因.
        testCase.setFailureReason("""Test Stage: %s ; Status: Failed ; Reason: %s""" % (stage, exceptionMsg))

        # 用例对象为configuration.
        if what == "configuration":
        testCase.setCaseStatus(TEST_STATUS.FAILED)
        testCase.logError("%s Failed, Because an issue occurred while "
        "trying to run the test configuration: %s \n" % (name, exceptionMsg))
        # stage为pre.
        elif stage == "pre":
        if not isinstance(exceptionMsg, HookException):
        testCase.setCaseStatus(TEST_STATUS.CONFIG_ERROR)
        else:
        testCase.setCaseStatus(TEST_STATUS.NOT_RUN)

        if self.runTestsInParallelFlag:
        self.globalTestStatus[name]["status"] = TEST_STATUS.FAILED

        testCase.logError("An issue occurred while trying to run the "
        "preTestCase steps for %s : \n" % name, exceptionMsg)

        # stage为main.
        elif stage == "main":
        if not isinstance(exceptionMsg, HookException):
        testCase.setCaseStatus(TEST_STATUS.FAILED)

        if self.runTestsInParallelFlag:
        self.globalTestStatus[name]["status"] = TEST_STATUS.FAILED

        testCase.logError("%s Failed, Because an issue occurred while "
        "trying to run the test case: \n" % name, exceptionMsg)
        testCase.incrementErrorCount()

        # stage为post.
        elif stage == "post":
        testCase.logError("An issue occurred while trying to run the "
        "postTestCase steps for %s :\n." % name, exceptionMsg)
        # h90006090 2018/03/01 Add: Post运行情况记录，方便Hook或其他接口进行其他操作
        testCase.setPostStatus(TEST_STATUS.FAILED)
        _status = {'_post_status': TEST_STATUS.FAILED}
        self.statusDb.update(testCase.statusUuid, **_status)

        def _updateStatusIfDie():
        if self.runTestsInParallelFlag and isinstance(testCase, Case):
        duration = str(_now - self.globalTestStatus[testCase.name]["start_time"]) + "S"
        else:
        duration = str(_now - self.startTime) + "S"

        _status = {'_end': _datetimeEnd,
        '_duration': duration,
        '_stage': 'done',
        '_status': testCase.caseStatus}
        self.statusDb.update(testCase.statusUuid, **_status)

        self.setTestSetError(True)
        # todo configuration in group, FOR BBT
        if (isinstance(testCase, Configuration) and self.configStopOnError) or self.stopOnError:
        def __die(errorType):
        # update current case status
        _updateStatusIfDie()
        # if exit ,must set end time first.
        testCase.setEndTime(_end)

        # 如果不是抛出的hook异常
        if not isinstance(exceptionMsg, HookException) or stage != 'post':
        # 可能会存在抛异常的hook，但是这里不能再抛出异常，需要记录数据
        try:
        self.runHooks('afterPostTest', tc=testCase)
        except HookException:
        self.logger.error("%s Run Hook Failed. \nError: %s" % (testCase.name, traceback.format_exc()))

        # h90006090 2017/05/28 http://10.183.61.55/oceanstor-autotest/UniAutos/issues/1653
        postReason = ''
        if stage == 'post':
        postReason = exceptionMsg.message
        self.serialLogResult(testCase, postReason)

        self.logger.warn("Engine Told me %s!" % errorType)
        self.postTestSet()
        # self.runHooks('afterPostTestSet')

        _duration = time.time() - self.testSetStartTime
        msg = '\nTest Set Duration: %sS\nTest Set Result:\n' % _duration
        testCases = getattr(self, 'bbtTestCases') if hasattr(self, 'bbtTestCases') else self.testCases
        for tc in testCases:
        if isinstance(tc, Group):
        msg += "TestGroup: %s, Status: %s\n" % (tc.name, tc.caseStatus)
        else:
        msg += "TestCase: %s, Status: %s\n" % (tc.name, tc.caseStatus)

        self.logger.info(msg)

        self.logger.warn("TestSet Set %s, Now Exit UniAutos!" % errorType)
        self.updateStatus()
        Log.releaseResource()
        os._exit(1)

        if isinstance(testCase, Configuration) and self.configStopOnError:
        __die('configStopOnError')

        if self.runTestsInParallelFlag and isinstance(testCase, Case):
        self.globalTestStatus[testCase.name]["end_time"] = _now

        if not self.runTestsInParallelFlag:
        __die('StopOnError')

        def _getIdentityOfTest(self, tcObject, identityName="tmss_id"):
        """获取指定测试用例对象， 指定identity name的值.
        Args:
        tcObject (instance): 测试用例对象.
        identityName (str): 用例唯一标识的名称, 默认为"tmss_id".

        Returns:
        identity (str): 用例的唯一标识ID.

        Examples:
        tcId = self._getIdentityOfTest(tc)

        """
        identityDict = {"name": identityName}
        if tcObject.hasIdentity(identityDict):
        identities = tcObject.getIdentity(identityDict)

        for identity in identities:
        if identity["name"] == identityName:
        return identity["id"]
        else:
        self.logger.trace("Identity %s does not exist for %s " % (identityName, tcObject.name))
        return ''

        def killTestThread(self, testCase, th):
        """杀死指定用例的线程

        Args:
        testCase (instance): 测试用例对象.
        th (thread Handle): 线程句柄.

        Examples:
        self.killTestThread(tc, th)

        """
        if th.ident in self.tidToTcLogs:
        Log.changeLogFile(Log.LogType.TestCase, re.sub(r'---0$', "", self.tidToTcLogs[th.ident]))
        self.logger.info("Controller Told me Stop! \nThread ID: %s" % th.ident)
        Log.releaseFileHandler(Log.LogType.TestCase, re.sub(r'---0$', "", self.tidToTcLogs[th.ident]))
        Log.changeLogFile(Log.LogType.Main, "Controller")

        # TestCase Kill的时候需要设置结束时间.
        testCase.setCaseEndTime(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        if isinstance(testCase, Group):
        testCase.setCaseStatus(TEST_STATUS.FAILED)
        else:
        # 如果为Case类的对象，需要判断当前Case对象的状态，如果已经失败或者成功则状态为成功或者失败，
        # 否则设置状态为Killed.
        status = TEST_STATUS.KILLED \
        if testCase.caseStatus not in [TEST_STATUS.FAILED,
        TEST_STATUS.CONFIG_ERROR,
        TEST_STATUS.NOT_RUN,
        TEST_STATUS.PASS] else testCase.caseStatus
        testCase.setCaseStatus(status)
        th.kill()

        def addExecutionParameters(self, **kwargs):
        """添加Engine的测试参数

        Args:
        kwargs : 测试引擎参数, 为关键字参数，键值对说明如下：
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

        Attributes:
        paramObj (instance): parameter对象.

        Raises:
        ValueException: 添加参数时，参数已经存在，或参数值未指定.

        Examples:
        self.addExecutionParameters(name='stop_on_error',
        description='If set to a true value, it will '
        'stop execution of all the tests '
        'in the test set when an error '
        'is encountered.',
        default_value=1,
        type='BOOLEAN',
        display_name='Stop on Error',
        )

        """
        paramObj = Parameter(kwargs)

        if paramObj.name in self.parameters:
        raise ValueException("Add parameter Fail, "
        "parameter: '%s' already exists. " % paramObj.name)

        if not paramObj.isOptional() and paramObj.getValue() is None:
        raise ValueException("Add parameter Fail, parameter: '%s' "
        "is optional parameter, must be set a value. " % paramObj.name)

        self.parameters[paramObj.name] = paramObj

        def setParameter(self, customParamList=None):
        """设置Engine测试参数

        Args:
        customParamList (list): 在测试床中配置的参数列表.

        Raises:
        ValueException: 添加测试床配置的参数失败.

        Examples:
        self.setParameter(self.customParams)

        Changes:
        2015-05-18 h90006090 优化设置Parameter值设置双重循环

        """
        # STOP_ON_ERROR
        self.addExecutionParameters(name='stop_on_error',
        description='If set to a true value, it will '
        'stop execution of all the tests '
        'in the test set when an error '
        'is encountered.',
        default_value=1,
        type='BOOLEAN',
        display_name='Stop on Error')
        # LOGGING_LEVEL
        self.addExecutionParameters(name='logging_level',
        description='Logging level for the messages to '
        'be displayed on the screen',
        default_value='INFO',
        validation={"valid_values": ['TRACE', 'DEBUG',
        'CMD', 'INFO', 'WARN', 'ERROR',
        'STATUS', 'FATAL', 'OFF'],
        },
        type='select',
        display_name='Logging Level')

        # LOG_ROTATION_SIZE
        self.addExecutionParameters(name='log_rotation_size',
        description='The size threshold for the log files'
        'beyond which the log files are rotated',
        default_value='60MB',
        type='SIZE',
        display_name='Log Rotation Size')

        # MAX_LOG_SIZE
        self.addExecutionParameters(name='max_log_size',
        description='The max size of the log files for a case',
        default_value='-1MB',
        type='SIZE',
        display_name='Max Log Size')

        # STOP_ON_CONFIG_ERROR
        # stop_on_config_error can be set in the main config xml file.
        # it will act as the test set level value (can be override by test config)
        self.addExecutionParameters(name='stop_on_config_error',
        description='If set to a true value, it will '
        'stop execution of all the tests '
        'in the test set when an error '
        'is encountered.',
        default_value=0,
        type='BOOLEAN',
        display_name='Stop on Config Error')

        # MONITOR_INTERVAL
        self.addExecutionParameters(name='monitor_interval',
        description='The interval in UniAuto time unit '
        'to specify how often to get the monitor sample',
        default_value='0S',
        type='time',
        display_name='Monitor Interval')

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
        logMessage = "Test Set Parameter: {name} has been set to " \
        "an invalid value. ".format(name=param["name"])
        self.logger.error(logMessage)
        hasInvalidParam = True

        # 如果值设置为空
        if parameterObj.isOptional() and parameterObj.getValue() is None:
        logMessage = "A value for Test Set Parameter: {name} " \
        "must be specified. ".format(name=param["name"])
        self.logger.error(logMessage)
        hasInvalidParam = True

        if hasInvalidParam:
        raise ValueException('One or more Test Set parameters are invalid, please check log '
        'for more information.')

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

        def createTestCaseLogFile(self, tcName):
        """创建测试用例的日志文件

        Args:
        tcName (str): 测试用例名称.

        Returns:
        testCaseLogFileName (str): 测试用例日志文件名称.

        Examples:
        logFileName = self.createTestCaseLogFile(TC_1)
        """

        return tcName + "-" + str(self.totalTestCounter)
        # return re.sub(r'-[0-9]*$', "", tcName) + "-" + str(self.totalTestCounter)

        @staticmethod
        def getTimeStamp():
        """按格式获取当前时间戳

        Returns:
        timeStamp (str): 当前时间的格式化时间字符串. 格式为: %Y_%m_%d_%H-%M-%S.

        Examples:
        timeStamp = self.getTimeStamp()

        """
        return datetime.datetime.now().strftime('%Y_%m_%d_%H-%M-%S-%f')

        @validateParam(status=bool)
        def setTestSetError(self, status):
        """设置测试套是否为Error

        Args:
        status (bool): 传入的测试套状态信息.

        Examples:
        self.setTestSetError(True)

        """
        self.isTestSetError = status

        def makeTimeLog(self, controllerFail=None):
        """创建Time Log HTML文件, 并写入TimeLine数据

        Args:
        controllerFail (bool): 引擎错误标记, 默认为空, 在Rats中使用.

        Examples:
        self.makeTimeLog()

        """
        # 默认设置Controller.html的连接为绿色，状态为空， 当存在用例执行失败时设置为红色，状态为Failed.
        color = "green"
        status = ""

        # globalTestStatus的遍历在线程创建，且globalTestStatus初始化后，并且size不会改变，仅值改变可以不用加锁.
        for tcName in self.globalTestStatus:
        if re.match(r'' + str(TEST_STATUS.FAILED) + '|' + str(TEST_STATUS.CONFIG_ERROR) + '',
        self.globalTestStatus[tcName]["status"]):
        color = "red"
        status = "---FAILED"
        break

        controllerLink = "" \
        "View Controller Log %s" % (color, status)

        # 遍历所有用例设置测试开始时间和结束时间
        earliest = None
        latest = None
        for tcName in self.globalTestStatus:
        if self.globalTestStatus[tcName]["status"] == TEST_STATUS.RUNNING:
        self.globalTestStatus[tcName]["end_time"] = time.time()
        if earliest is None or (self.globalTestStatus[tcName]["start_time"] < earliest):
        earliest = self.globalTestStatus[tcName]["start_time"]
        if latest is None or (self.globalTestStatus[tcName]["end_time"] > latest):
        latest = self.globalTestStatus[tcName]["end_time"]
        if not (earliest and latest):
        self.logger.debug("There is not enough runtime to generate the timeline log yet. "
        "\n startTime:%s \n latestTime: %s" % (str(earliest), str(latest)))
        return

        # 创建timeLine日志文件.
        self.setupTimeLog()

        # 设置用例执行时间
        duration = latest - earliest

        days = int(duration / (24 * 60 * 60))
        hours = int((duration / (60 * 60)) % 24)
        minutes = int((duration / 60) % 60)
        seconds = int(duration % 60)
        durationStr = "{Days},{HH}:{MM}:{SS}".format(Days=days,
        HH=hours,
        MM=minutes,
        SS=seconds)
        # 计算每个表格的元素长度.
        cellDuration = None # 单个单元格的宽度.
        numberOfCells = None # 单元格的个数.

        def hasMultipleDuration(startTime, endTime, tcDict):
        for tc in tcDict:
        durationCnt = 0
        if tcDict[tc]["start_time"] >= startTime and tcDict[tc]["end_time"] 1:
        return False
        return True

        def cDurationExc():

        for cDuration in range(1, 1200):
        if cDuration * cells >= duration:
        tmp = earliest
        while tmp = 0 else False
        elif Units.isPercentage(str(a)) and Units.isPercentage(str(b)):
        return True if Units.comparePercentage(a, b) >= 0 else False
        return True if a >= b else False

        def __isMatch(self, a, b):
        return True if re.search(a, b) else False

        def __isNotMatch(self, a, b):
        return True if re.search(a, b) else False

        if __name__ == "__main__":
        pass