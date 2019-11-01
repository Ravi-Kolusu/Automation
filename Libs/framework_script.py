#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: UniAutosScript.py ，测试执行入口程序, 使用 'python UniAutosScript.py -h' 查看详细参数信息.

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2015/4/25 胡伟 90006090 created
"""

import os
import sys
import re
import time
import imp
import argparse
import traceback
from argparse import RawDescriptionHelpFormatter
from xml.etree.ElementTree import ParseError


def __getLibAbsPath(currentPath, depth):
"""Get an absolute path relative depth

Args:
currentPath (str): current file's directory abs path.
depth (int): relative depth.

Returns:
an absolute path relative depth.
"""
libPath = currentPath
while depth:
libPath = os.path.split(libPath)[0]
depth -= 1
return libPath


def initLibPath():
"""init UniAutos Lib Path, append lib path into python path.
"""
# all lib directory name
# all lib directory relative parent path depth,
# current directory's parent directory depth is 1.
libHash = {'lib': 1,
'sample': 1,
"Tests": 3,
"scripts": 5, # 适配UniHutfAgent, UniJenkinsAgent
"UtilityLibraries": 3}

# uniAutosScript.py abs directory
binPath = os.path.split(os.path.realpath(__file__))[0]

# get parent directory and join it and import lib path
for key in libHash:
sys.path.append(os.path.join(__getLibAbsPath(binPath, libHash[key]), key))


# Initialize the library path of the current execution machine.
initLibPath()

import hashlib
import datetime
from UniAutos import Log
from UniAutos.Util.TestStatus import TEST_STATUS
from UniAutos.Util.XmlParser.XmlToDict import XmlToDict
from UniAutos.Resource import Resource
from UniAutos.TestEngine.Set import Set
from UniAutos.TestEngine.Engine import Engine, TestStatusData
from UniAutos.TestEngine.RatsEngine import RatsEngine
from UniAutos.TestEngine.BBTEngine import BBTEngine
from UniAutos.TestEngine.BBTRatsEngine import BBTRatsEngine
from UniAutos.TestEngine.RatsCase import RatsCase
from UniAutos.TestEngine.Group import Group
from UniAutos.Util.Units import Units
from UniAutos.Util.Codec import convertToUtf8
from UniAutos.Exception.TypeException import TypeException
import UniAutos

if sys.version_info >= (3, 0):
raise RuntimeError('You need python 2.7 for UniAutos.')

__author__ = "Automation Group, Unified Storage I&V Dept, IT"
__date__ = "21 Nov 2015"
__version__ = UniAutos.__version__
__license__ = "GNU Lesser General Public License (LGPL)"

# Defining global variables
__Args__ = None
uniLogger = None
__SET_PARALLEL__ = False
__SET_DURATION__ = '0S'


# Public method
def __setParam(toParamList, fromParam):
"""A public function that is used to pass arguments when the value is a dictionary or list.

Append the data from fromParam to toParam.

Args:
toParamList (list): a list of data before the data is added, a list of data to be returned,
toParam may be empty or it may be a list of existing values ​​that need to be appended.
fromParam (list|dict): The raw data that needs to be added to toParam, either dict or list.

Returns:
toParamList (list): Append the data list after fromParam.

Examples:
toParam = [{"A": "pizza"}]
fromParam = {"B": "cook"}
__setParam(toParam, fromParam)
output:
>> [{"A": "pizza"}, {"B": "cook"}]

"""

# The parameters passed in after parsing through the xml file can only be used for dictionary and list types.
if not isinstance(fromParam, list):
toParamList.append(fromParam)
else:
toParamList.extend(fromParam)

return toParamList


def configTmssFillBackInfo(mainConfigData, testSetIdentities):
"""Reconfigure TMSS information with specified parameters.
Args:
mainConfigData (dict): The T parameter information entered by console.
testSetIdentities (dict): The TMSS parameter information configured in the test suite.

Returns:
testSetIdentities (dict): Updated TMSS parameter information.
"""
from UniAutos.Util.Tmss import TMSS
tmss = TMSS()

# If the value in mainconfig is not the default value, the user has entered the parameter on the command line. The parameter is subject to the command line.
if 'tmssServer' in mainConfigData and mainConfigData['tmssServer'] != "ctutms04-wb":
testSetIdentities['tmss_server'] = mainConfigData['tmssServer']

elif not testSetIdentities['tmss_server']:
testSetIdentities['tmss_server'] = mainConfigData['tmssServer']

if 'tmssPort' in mainConfigData and mainConfigData['tmssPort'] != "8082":
testSetIdentities['tmss_port'] = mainConfigData['tmssPort']

elif not testSetIdentities['tmss_port']:
testSetIdentities['tmss_port'] = mainConfigData['tmssPort']

if 'username' in mainConfigData:
testSetIdentities['tmss_username'] = mainConfigData['username']

if 'password' in mainConfigData:
testSetIdentities['tmss_password'] = mainConfigData['password']

# Parameter incoming information
tmssVersionName = mainConfigData.get('testVersionName')
tmssParentName = mainConfigData.get('testVersionParentName')
testScenesName = mainConfigData.get('testScenesName')
product = mainConfigData.get('product')

# Xml configuration information.
tmssVersionUri = testSetIdentities.get('test_version_uri')
xmlParentName = testSetIdentities.get('test_parent_name')
xmlProductName = testSetIdentities.get('product')

if product == '01 Unified Storage Product Integration and Verification' and xmlProductName is not None \
and xmlProductName != '01 Unified Storage Product Integration and Verification':
product = xmlProductName

if tmssParentName is None and xmlParentName:
tmssParentName = xmlParentName

# If tmssVersionName is passed in, log in to tmss to query the information.
if tmssVersionName:
tmss.login(testSetIdentities['tmss_server'], testSetIdentities['tmss_port'],
testSetIdentities['tmss_username'], testSetIdentities['tmss_password'])

# If both the parent path and the version name are specified.
if tmssParentName and tmssVersionName:
# Priority to look up from cached data.
tmssVersionUri = tmss.searchVersionUriFromCache(tmssParentName, tmssVersionName, product)

# If the parent path is not found in the cache, it is searched through the specified parent path in the server.
if not tmssVersionUri:
parentUri = tmss.compareVersion(tmssParentName, product)
childVersionDict = tmss.getChildVersion(parentUri, tmssVersionName)
tmssVersionUri = tmss.getVersionUri(tmssVersionName, childVersionDict)
# If it finds the value found using the value, otherwise the value in the test suite is set by default.
if tmssVersionUri:
testSetIdentities['test_version_uri'] = tmssVersionUri
else:
testSetIdentities['test_version_uri'] = tmssVersionUri
# If only the version name is specified.
elif tmssVersionName:
versionName = tmssVersionName.decode('utf-8')
tmssVersionUri = tmss.searchVerUriFromCacheByName(versionName, product=product)
if tmssVersionUri:
testSetIdentities['test_version_uri'] = tmssVersionUri
else:
# TODO 模糊查询查找父路径
tmssVersionUri = tmss.compareVersion(tmssVersionName)
testSetIdentities['test_version_uri'] = tmssVersionUri

if testScenesName:
testScenesUri = tmss.getScenesUri(tmssVersionUri, testScenesName)
testSetIdentities['test_scenes_uri'] = testScenesUri
return testSetIdentities


############## Scheduling Portal ######################

def _updateOptions(args):
"""Parse and update mainConfig data

Get the data in mainConfig, and use the parameters obtained by the command line to update the dictionary data parsed from the mainConfig file and verify the incoming parameters.

Args:
Args (argparse.Namespace): The namespace of the user input parameter, input by the usage() function. For details, refer to the parameter list defined by usage.

Returns:
mainConfig (dict): updated mainConfig dictionary data

Notes:
This method is only used for the usage of the usage() interface.
"""

# mainConfig initialization.
_main = {}
args.workspace = re.sub(r'(/|\\)$', "", args.workspace)
global __Args__
__Args__ = args
if args.configFile and args.workspace:
try:
# get main config file path.
args.configFile = os.path.join(args.workspace, args.configFile)
# parser main config data.
_mainRaw = XmlToDict.getConfigFileRawData(args.configFile)
# get main config opt data.
_main = XmlToDict.getSpecificKeyRawData(_mainRaw, 'opt')

if 'testbed_file' in _main:
_main['testbed_file'] = os.path.join(args.workspace, _main['testbed_file'])

_main.update(
{'test_set_file':
os.path.join(args.workspace, _main['test_set_file']),
'local_base_log_path':
os.path.join(args.workspace, _main.get('local_base_log_path', 'standard_logs')),
'local_execution_log_path':
os.path.join(args.workspace, _main.get('local_execution_log_path', 'standard_execution_logs'))
})

except (TypeException, IOError, AttributeError, ParseError):
print ("ERROR: The Specified Main Configuration File: '%s'\n"
"Does Not Exist Or File Is Not The Correct Xml File! Detail: "
"%s" % (args.configFile, traceback.format_exc()))
sys.exit(1)
else:
# If the mainConfig.xml file is not specified
print "WARNING: Please Specify The MainConfig File! " \
"Use 'python UniAutosScript.py -h' To Show Detail Information. "
sys.exit(1)

# Update mainConfig configuration
for key in ['guid', 'tmssServer', 'tmssPort', 'username', 'password', 'testVersionName', 'testVersionParentName',
'testScenesName', 'product', 'task_id', 'elk', 'console_loglevel']:
if hasattr(args, key) and getattr(args, key):
_main[key] = getattr(args, key)

if 'workspace' not in _main and args.workspace:
_main['workspace'] = args.workspace

if args.workspace:
if hasattr(args, 'testBedFile') and getattr(args, 'testBedFile'):
_main['testbed_file'] = os.path.join(args.workspace, args.testBedFile)
if hasattr(args, 'testSetFile') and getattr(args, 'testSetFile'):
_main['test_set_file'] = os.path.join(args.workspace, args.testSetFile)
if hasattr(args, 'localBaseLogPath') and getattr(args, 'localBaseLogPath'):
_main['local_base_log_path'] = os.path.join(args.workspace + args.localBaseLogPath)
if hasattr(args, 'localExecutionLogPath') and getattr(args, 'localExecutionLogPath'):
_main['local_execution_log_path'] = os.path.join(args.workspace, args.localExecutionLogPath)

if 'testbed_file' in _main and not os.path.isfile(_main['testbed_file']):
print ("ERROR: The Specified Testbed File: '%s' Not Be Found!" % _main['testbed_file'])
sys.exit(1)

if 'test_set_file' in _main and not os.path.isfile(_main['test_set_file']):
print ("ERROR: The Specified TestSet File: '%s' Not Be Found!" % _main['test_set_file'])
sys.exit(1)

if 'testVersionParentName' in _main:
if 'testVersionName' not in _main:
print('ERROR: If Specified test version parent name, must specified test version name.')
sys.exit(1)

if 'testScenesName' in _main:
if 'testVersionName' not in _main:
print('ERROR: If Specified test Scenes name, must specified test version name.')
sys.exit(1)

# Log path check, created if it does not exist.
if 'local_base_log_path' in _main and not os.path.exists(
_main['local_base_log_path']):
print ("WARNING: The Specified Local Base Log Path: '%s' Not Be Found!"
% _main['local_base_log_path'])

os.makedirs(_main['local_base_log_path'])
print ("INFO: Create Specified Local Base Log Path: '%s' Success. "
% _main['local_base_log_path'])

if 'local_execution_log_path' in _main \
and not os.path.exists(_main['local_execution_log_path']):
print ("WARNING: The Specified Local Execution Log Path: '%s' Not Be Found!"
% _main['local_execution_log_path'])

os.makedirs(_main['local_execution_log_path'])
print ("INFO: Create Specified Local Execution Log Path: '%s' Success. "
% _main['local_execution_log_path'])

if os.path.isabs(args.configFile):
args.workspace = os.path.dirname(args.configFile)

return _main


def execute(mainConfig):
"""Test execution main function

Args:
mainConfig (dict): The updated main configuration parameters, the key-value pairs are described as follows:
{
Local_base_log_path (str): Test log base path.
Local_execution_log_path (str): Test the log path.
Test_set_file (str): Test suite configuration file path.
Testbed_file (str): Test bed configuration file path.
Workspace (str): The absolute path of the main configuration file, ie the working path.
}
Examples:
execute(mainConfig)

"""

# The devices in the test bed file are configured in the "testbedinfo" tab.
testBedInfo = {}
if "testbed_file" in mainConfig:
testBedInfo = XmlToDict.getConfigFileRawData(mainConfig["testbed_file"])["testbedinfo"]

# The devices in the test bed file are configured in the "test_set" tag.
testSetRawData = XmlToDict.getConfigFileRawData(mainConfig["test_set_file"])
testSetInfo = testSetRawData["opt"]["test_set"]
# TODO identity testBed

testSetName = __setTestSetName(testSetInfo)
buildParameters = []

# Test parameters
executionParams = __setExecutionParams(mainConfig)

# Set log parameters
customLogParam = __createLogParam(executionParams, mainConfig, testSetInfo, testSetName)

# Start log module
console_loglevel = mainConfig.get('console_loglevel')
if console_loglevel:
import logging
Log.changeConsoleLogLevel(logging.getLevelName(console_loglevel))
Log.setupLogger(customLogParam["logPath"], count=customLogParam["count"], size=customLogParam["size"],
localExecution=False, style=customLogParam["style"], level=customLogParam['logging_level'],
taskId=mainConfig.get("task_id", ""), elkUri=mainConfig.get("elk", "").rstrip('/'),
testSetInfo=testSetInfo.get("tests", {}), logCommandUri=mainConfig.get('command_log_uri'))
global uniLogger
uniLogger = Log.getLogger("UniAutoScript")
_statusDb = TestStatusData(Log.LogFileDir)

_MainRollupUUID = hashlib.new('md5', Log.LogFileDir + 'Main_Rollup').hexdigest()
_start = _end = datetime.datetime.now()
_dbStatus = {
"_uuid": _MainRollupUUID,
"_what": 'set',
"_name": 'Main_Rollup',
"_status": TEST_STATUS.NOT_RUN,
"_start": _start,
"_end": _end,
"_duration": '0S'
}
_statusDb.save(**_dbStatus)

_preTestSetUUID = hashlib.new('md5', Log.LogFileDir + 'Pre_TestSet').hexdigest()
_dbStatus = {
"_uuid": _preTestSetUUID,
"_start": datetime.datetime.now(),
"_status": TEST_STATUS.RUNNING,
"_name": 'Pre_TestSet',
"_duration": '0S'
}
_statusDb.save(**_dbStatus)

# Create a Resource object
try:
uniLogger.info("Start Creating All The Device Objects Defined In The Testbed.....")
resourceObject = None
# Simulation deployment skips initialization directly
temps = testSetInfo.get("tests", {}).get("test")
if isinstance(temps, dict):
if "os_setup_simulation" in temps.get("location", "") or "TC_FORCE_OSSETUP" in temps.get("location", ""):
resourceObject = Resource(testBedInfo, skip=True)
if isinstance(temps, list):
for temp in temps:
if "os_setup_simulation" in temp.get("location", "") or "TC_FORCE_OSSETUP" in temp.get("location", ""):
resourceObject = Resource(testBedInfo, skip=True)
break
if resourceObject is None:
resourceObject = Resource(testBedInfo)
resourceObject.setBedLocation(mainConfig.get('testbed_file'))
resourceObject.setSetLocation(mainConfig.get('test_set_file'))
except Exception, errorMsg:
uniLogger.error("Create Device Objects Defined In The Testbed Failed. \n", errorMsg)
sys.exit(1)

if resourceObject.getInitErrors():
uniLogger.warn('There have some error in init resource.')
# sys.exit(1)

# TODO Set the test bed file to the resource object.
uniLogger.passInfo("Create Resource Success Complete.")
# Create a test case object

uniLogger.info("Start Creating All The Test Case Objects Defined In The TestSet.....")
tcObjects = __createTestCases(testSetInfo, resourceObject)
uniLogger.passInfo("Create Test Case Success Complete.")

# 2015/09/30 h90006090 Adjust the hook creation order for calling test set data when hook is constructed
hookObjects = []
# Create a test suite object
try:
uniLogger.info("Start Create Test Set Object.....")
testSetObject = __createTestSetObject(testSetInfo, testSetName,
tcObjects, buildParameters, hookObjects, mainConfig)
except Exception, errorMsg:
uniLogger.trace("Create Test Set Failed: ", errorMsg)
sys.exit(1)
uniLogger.passInfo("Create Test Set Success Complete. ")

# Create a controller object
try:
uniLogger.info("Start Create Test Engine Object.....")
engineObject = __createTestEngine(tcObjects, testSetObject, executionParams, _statusDb)
except Exception, errorMsg:
uniLogger.error("Unable to create the Test Engine. "
"object:", errorMsg)
sys.exit(1)
uniLogger.passInfo("Create Test Engine Success Complete. ")

# Set Test Engine Object to Resource object
resourceObject.setTestEngine(engineObject)

# 2015/09/30 h90006090 Adjust the hook creation order for calling test set data during hook construction
hookObjects = __createHookObject(testSetInfo, resourceObject, testSetObject)
testSetObject.addHooks(hookObjects)
# Execution test
testFailFlag = False

if engineObject:
try:
uniLogger.info("Start Run Test Set.....")
engineObject.runTestSet()
except Exception, errorMsg:
testFailFlag = True
engineObject.postTestSet()
uniLogger.error("Error Occurred While Running The Test Set: ", errorMsg)
Log.releaseResource()
# sys.exit(1)-
os._exit(1)

if not testFailFlag:
if mainConfig.get('elk'):
info = _statusDb.getValue(primary='*')
if info:
msg = 'View logs on Heaven, please click links below:\n'
for item in info:
msg = '%s\t%s: \thttp://taas.inhuawei.com/heaven/#/log?log_id=%s\t%s\n' \
% (msg, item[10], item[0], str(item[12]).upper())
print(msg)

uniLogger.passInfo("Test Running Complete.")
failed = False

# Check if the use case fails. If the use case status is non-PASS, the frame exit code is 1, otherwise it is 0.
for test in testSetObject.testCases:
if re.match(r'Fail|ConfigError|Kill|Incomplete|NotRun', test.caseStatus):
failed = True
break
_duration = time.time() - engineObject.testSetStartTime
msg = '\nTest Set Duration: %sS\nTest Set Result:\n' % _duration
testCases = getattr(engineObject, 'bbtTestCases') if hasattr(engineObject, 'bbtTestCases') \
else testSetObject.testCases
for tc in testCases:
if isinstance(tc, Group):
msg += "TestGroup: %s, Status: %s\n" % (tc.name, tc.caseStatus)
else:
msg += "TestCase: %s, Status: %s\n" % (tc.name, tc.caseStatus)

if not failed:
uniLogger.info("All Test Cases Passed. ")
uniLogger.info(msg)
Log.releaseResource()
# sys.exit(0)
os._exit(0)
else:
uniLogger.warn("Part of Test Cases Failed, Please Check Log message.")
uniLogger.info(msg)
Log.releaseResource()
# sys.exit(1)
os._exit(1)


def usage():
"""Parameter definition of UniAutosScript.py file, parameter receiving

Returns:
mainConfig (dict): The mainConfig dictionary data updated by the __updateOptions() function, the key-value pairs are described as follows:
{
Local_base_log_path (str): Test log base path.
Local_execution_log_path (str): Test the log path.
Test_set_file (str): Test suite configuration file path.
Testbed_file (str): Test bed configuration file path.
Workspace (str): The absolute path of the main configuration file, ie the working path.
Execution_parameters (dict): Test global parameters.
{
Param (dict|list): Tests a global parameter dictionary or list, one parameter is dict and multiple are list.
{
Name (str): The name of the parameter.
Value (str): The value of the parameter.
}
}
}

eg:
{'doc_type': 'MAIN_CFG',
'execution_parameters': {'param': [{'name': 'stop_on_error',
'value': '1'},
{'name': 'logging_level',
'value': 'INFO'}]},
'local_base_log_path': 'single_logs',
'local_execution_log_path': 'single_execution_logs',
'test_instance_id': '124',
'test_set_file': 'Config\\testSetInfo_Single.xml',
'testbed_file': 'Config\\testBedInfo_Single.xml',
'tms': {'ip': '10.23.66.45'},
'version': '1',
'workspace': "D:\\UniAutos"}

Examples:
mainConfigInfo = usage()

"""
msg = """
***********************************************************************

* U n i A u t o s *

***********************************************************************

UniAuto is a testing framework. Please see the below switches which
can be used to execute UniAuto.
"""
workPath = os.path.split(os.path.realpath(__file__))[0]

parser = argparse.ArgumentParser(description=msg, formatter_class=RawDescriptionHelpFormatter)

parser.add_argument("-c", "--configFile", dest="configFile", help="- (required) The main test configuration file.")
parser.add_argument("-tb", "--testBedFile", dest="testBedFile", help="- The TestBed xml file.")
parser.add_argument("-ts", "--testSetFile", dest="testSetFile", help="- The TestSet xml file.")
parser.add_argument("-lb", "--localBaseLogPath", dest="localBaseLogPath", help="- The local base log path.")
parser.add_argument("-le", "--localExecutionLogPath", dest="localExecutionLogPath",
help="- The local execution log path.")
parser.add_argument("-v", "--version", help="- The version of UniAuto installed.", action="store_true")
parser.add_argument("-u", "--useCryptoLock", dest="useCryptoLock",
help="- Force Command::Ssh to lock around all Net::SSH2 API calls.")
parser.add_argument("-nu", "--noUseCryptoLock", dest="noUseCryptoLock", help="- Opposite of above.")
parser.add_argument("-w", "--workspace", dest="workspace", default=workPath,
help="- The workspace path, Default is path of UniAutosScript.py. "
"This path as the absolute path of above files is used to specify ")
parser.add_argument('-TS', "--tmssServer", dest="tmssServer", default='ctutms04-wb',
help="- tmss server, use to fill back test case result.")
parser.add_argument('-TP', "--tmssPort", dest="tmssPort", default='8082',
help="- tmss server port, use to fill back test case result.")
parser.add_argument('-U', "--username", dest="username",
help="- tmss server username, use to fill back test case result.")
parser.add_argument('-P', "--password", dest="password",
help="- tmss server password, use to fill back test case result.")
parser.add_argument('-TV', "--testVersionName", dest="testVersionName",
help="- tmss test version Name, use to fill back test case result.")
parser.add_argument('-TC', "--testScenesName", dest="testScenesName",
help="- tmss test Scenes Name, use to fill back test case result.")
parser.add_argument('-PN', "--parentName", dest="testVersionParentName",
help="- tmss test version parent path Name.")
parser.add_argument('-PC', "--product", dest="product",
help="- tmss test version product name.",
default='01 统一存储产品集成与验证')
parser.add_argument('-g', "--guid", dest="guid",
help="- use to uniAutos web platform, execute by jenkins e2e flow.")
parser.add_argument('-t', "--task_id", dest="task_id",
help="- Used to identity current task execution")
parser.add_argument('-e', "--elk", dest="elk",
help="- Elk server for collect log message")

parser.add_argument('-CL', '--console_loglevel', dest='console_loglevel',
help='- Console log level')

args = parser.parse_args()

if args.version:
print("UniAuto Version:%s" % __version__)
sys.exit(0)

return _updateOptions(args)


############## Test case ###################

def __createCCTGroup(cctInfo, resource, globalTestCaseParams, groupOrder):
"""Create a use case in the test bed of type cct as Group.
Args:
cctInfo (dict): Tests the information of type cct.
Resource (Resource): Resource resource object information.
globalTestCaseParams (dict): Tests the global parameters of the test case in the test suite.
groupOrder (int): The order of the current group.
Returns:
Group (list): A list of Group objects generated by cct information.
"""
global __Args__
global uniLogger

# h90006090 2017/05/31 all character '\' must replace to '/', used to support linux.
if cctInfo.get('location'):
cctInfo['location'] = re.sub(r'\\', '/', cctInfo['location'])

_workspaces = re.split(r'/|\\', __Args__.workspace)
_locations = re.split(r'/|\\', cctInfo['location'])

_base = []
for _w in _workspaces:
if _w == _locations[0]:
break
_base.append(_w)
_base.extend(_locations)
location = os.path.join(_base[0] + os.sep, *_base[1:])
if not os.path.exists(location):
location = os.path.join(__Args__.workspace, cctInfo['location'])
if not os.path.exists(location):
# The path of the cct xml file is a relative path, which can be relative to the workspace (default), and can be relative to the library path of the test case library.
# When the path is combined with the relative address into a path, if the path file exists, it is represented as location.

paths = sys.path + [__Args__.workspace]
for path in paths:
if os.path.exists(os.path.join(path, cctInfo['location'])):
location = os.path.join(path, cctInfo['location']) # The first path found is the default location.
break
uniLogger.info('Create CCT Test Group, Xml File location: %s' % location)
try:
cctRawInfo = XmlToDict.getConfigFileRawData(location)
testsData = cctRawInfo['opt']['test_set']['tests']
except Exception as ex:
uniLogger.error(traceback.format_exc())
raise ex
cctInfo.update(testsData)
cctInfo['relative_path'] = cctInfo['location']
cctInfo['location'] = location
if not cctInfo.get('name') and cctRawInfo['opt']['test_set'].get('name'):
cctInfo['name'] = cctRawInfo['opt']['test_set'].get('name')

if not cctInfo.get('id') and cctRawInfo['opt']['test_set'].get('id'):
cctInfo['id'] = cctRawInfo['opt']['test_set'].get('id')

if not cctInfo.get('detail') and cctRawInfo['opt']['test_set'].get('detail'):
cctInfo['detail'] = cctRawInfo['opt']['test_set'].get('detail')
return __createTestGroup(cctInfo, resource, globalTestCaseParams, groupOrder)


def __createTestGroupParam(testGroupInfo, resource, globalTestCaseParams, groupOrder):
"""Create a parameter for the use case of type cCT in the test bed.
Args:
testGroupInfo (dict): Tests information of type test_group.
Resource (Resource): Resource resource object information.
globalTestCaseParams (dict): Tests the global parameters of the test case in the test suite.
groupOrder (int): The order of the current group.
"""
global uniLogger
parallel = True if testGroupInfo.get('parallel') == 'True' else False
__xmlTests = testGroupInfo.get('test', [])
testsData = []
# 3. If the test data obtained is a dictionary, it proves that there is only one use case.
if isinstance(__xmlTests, dict):
testsData.append(__xmlTests)

elif isinstance(__xmlTests, list):
testsData.extend(__xmlTests)

# 3. If there is no test case, exit directly.
if len(testsData) 1:
objectNum = 0
for tmpTc in tmp[name]:
tmpTc.setName(tmpTc.name + "-" + str(objectNum))
objectNum += 1
# Check and set identities, set the group's tmss id and uri and other information.
identities = {"identity": []}
if "identities" in testGroupInfo and "identity" in testGroupInfo["identities"]:
identities["identity"] = __setParam(identities["identity"], testGroupInfo["identities"]["identity"])
else:
idString = "TEST_ID_" + str(testId)
identities["identity"] = [{"name": "tmss_id", "id": idString}]

# Check and set the test parameters.
customParams = []
if 'parameters' in testGroupInfo and 'param' in testGroupInfo['parameters']:
customParams = __setParam(customParams, testGroupInfo['parameters']['param'])
customParams = convertToUtf8(customParams)
_group = {'parallel': parallel,
'testCases': testCases,
'id': testGroupInfo.get('id'),
'name': testGroupInfo.get('name'),
'detail': testGroupInfo.get('detail'),
'resource': resource,
'identities': identities,
'order': groupOrder,
'times': testGroupInfo.get('times'),
'params': customParams}

return _group


def __createTestGroup(testGroupInfo, resource, globalTestCaseParams, groupOrder):
"""Create a use case in the test bed of type cct as Group.
Args:
testGroupInfo (dict): Tests information of type test_group.
Resource (Resource): Resource resource object information.
globalTestCaseParams (dict): Tests the global parameters of the test case in the test suite.
groupOrder (int): The order of the current group.
Returns:
Group (list): A list of Group objects generated by cct information.
"""
# if parallel is False and have 'times' in test parameter
# If the currently running test suite is configured as serial, or a single concurrent, and the case is configured with the number of executions, the corresponding execution instance should be cloned here.
groups = []
if Units.isNumber(testGroupInfo.get('times')) and \
(__SET_PARALLEL__ is False or (__SET_PARALLEL__ and re.match(r'^0\w?', __SET_DURATION__))):
for i in xrange(int(testGroupInfo.get('times'))):
groups.append(Group(__createTestGroupParam(testGroupInfo,
resource,
globalTestCaseParams,
groupOrder)))

_handle_parallel_between_groups(groups,testGroupInfo)

else:
groups.append(Group(__createTestGroupParam(testGroupInfo,
resource,
globalTestCaseParams,
groupOrder)))
return groups


def _handle_parallel_between_groups(groups, testGroupInfo):
# here to support interdependence between groups
parallel_between_groups = testGroupInfo.get("parallel_between_groups")
# Only handles scenes where the group default is false, because if it is concurrent, but the test suite is not concurrent, here is not fixed, if the test suite is concurrent, then the default is concurrent.
if parallel_between_groups == "False":
# First rename, then each GROUP depends on,
for i in range(len(groups)):
Group = groups[i]
Group.name += "-" + str(i)
if i > 0:
# From the second group, configure the dependencies in turn
group.parameters.get("dependency").parameter["assigned_value"] = [
{
"test_name": groups[i - 1].name,
"status": "pass"
}
]

def __createTestCase(test, resource, globalTestCaseParams, testId, order):
""" Create a test bed with the type cct as a use case.
Args:
Test (dict): Tests the information of type case or configuration.
Resource (Resource): Resource resource object information.
globalTestCaseParams (dict): Tests the global parameters of the test case in the test suite.
Order (int): The order of the current test.
testId (int): The identifier of the current test data.

Returns:
testCases (list): List of generated Case objects.
"""
# test name is the file name of the test case, which is also equal to the test class name. The test path is equal to the test module path. These two variables are used when creating the object.
global uniLogger
testLocation = test['location']
testCaseModule = re.sub(r'[\\|/]', ".", testLocation)

# Check and set the test parameters.
customParams = []
if 'parameters' in test and 'param' in test['parameters']:
__setParam(customParams, test['parameters']['param'])
if 'parameters' in test and 'parameter' in test['parameters']:
__setParam(customParams, test['parameters']['parameter'])

# Used for Test case global parameter assignment.
for globalParam in globalTestCaseParams:
for customParam in customParams:
if isinstance(customParam, dict):
if globalParam["name"] == customParam['name'] and \
('override' not in customParam or re.match(r'0|false|no', customParam['override'], re.I)):
customParam['value'] = globalParam['value']

# Configuration configuration parameters.
configParams = []
if "config_params" in test and 'param' in test["config_params"]:
configParams = __setParam(configParams, test["config_params"]['param'])

# Configuration deConfiguration configuration parameters.
deConfigParams = []
if "deConfig_params" in test and 'param' in test["deConfig_params"]:
deConfigParams = __setParam(deConfigParams, test["deConfig_params"]['param'])

# Check and set identities.
testIdentities = {"identity": []}
if "identities" in test and "identity" in test["identities"]:
testIdentities["identity"] = __setParam(testIdentities["identity"], test["identities"]["identity"])
else:
idString = "TEST_ID_" + str(testId)
testIdentities["identity"] = [{"name": "tmss_id", "id": idString}]

testTags = []
if "tags" in test and test["tags"]:
if "tag" in test["tags"] and test["tags"]["tag"]:
testTags = test["tags"]["tag"]

# Check if the test case/config module is accessible.
# try:
customParams = convertToUtf8(customParams)
# Create test object
param = {"name": test['name'],
"location": testLocation,
"params": customParams,
"instance_id": test.get('instance_id'),
"identities": testIdentities,
# "dependencies": testDependencies,
"order": order,
"resource": resource,
"description": test.get('description'),
"tags": testTags,
"deConfig_params": deConfigParams,
"config_params": configParams,
"steps_to_perform": test.get('steps_to_perform', []),
"required_equipment": test.get('required_equipment', []),
"shareable_equipment": test.get('shareable_equipment'),
"times": test.get("times"),
'alias': test.get('alias', None)}
tcObjCreateFailedFlag = False
errorMsg = None
testCases = []
try:
__import__(testCaseModule)
# if parallel is False and have 'times' in test parameter
if Units.isNumber(test.get('times')) and \
(__SET_PARALLEL__ is False or (__SET_PARALLEL__ and re.match(r'^0\w', __SET_DURATION__))):
for i in xrange(int(test.get('times'))):
tcObj = getattr(sys.modules[testCaseModule], test['name'])(param)
testCases.append(tcObj)
else:
tcObj = getattr(sys.modules[testCaseModule], test['name'])(param)
testCases.append(tcObj)
except Exception, errorMsg:
tcObjCreateFailedFlag = True

if tcObjCreateFailedFlag is True:
uniLogger.error("Unable To Create The Test Case Object For: %s \n" % test['name'], errorMsg)
sys.exit(1)
return testCases


def __createTestCases(testSetInfo, resource):
"""Create a test case object

Create all the test cases configured in the test suite as test objects.
Args:
Resource (instance): resource instance object.
testSetInfo (dict): Test suite information obtained from the test suite xml file.

Returns:
testCaseObjects (list): A list of test case objects.

Raises:
ObjectNotFoundException: Returns when the test case object fails to be created.
"""
testsData = [] # Define a list of test cases, which is empty by default.
__xmlTests = None

# Reference global variable
global uniLogger
global __SET_DURATION__
global __SET_PARALLEL__

# 1. Gets whether the current test suite is executed concurrently.
testSetParallel = None
if "test_set_parameters" in testSetInfo and "parameter" in testSetInfo["test_set_parameters"]:
for param in testSetInfo["test_set_parameters"]["parameter"]:
if param["name"] == "parallel" and param["value"]:
__SET_PARALLEL__ = True if param['value'].lower() in ['1', 'true', 'yes', 'y'] else False
if param["name"] == 'duration' and param["value"]:
__SET_DURATION__ = param["value"]

globalTestCaseParams = __generateGlobalTestCaseParameter(testSetInfo)

# 2. Get the test case configured in the test suite file.
if 'tests' in testSetInfo and 'test' in testSetInfo['tests'] and testSetInfo['tests']['test']:
__xmlTests = testSetInfo['tests']['test']

# 3. If the test data obtained is a dictionary, it proves that there is only one use case.
if isinstance(__xmlTests, dict):
testsData.append(__xmlTests)
elif isinstance(__xmlTests, list):
testsData.extend(__xmlTests)

# 3. If there is no test case, exit directly.
if len(testsData) 1:
objectNum = 0
for tmpTc in tmp[name]:
tmpTc.setName(tmpTc.name + "-" + str(objectNum))
objectNum += 1

# The name of the Case in the Group is renamed, using the Group name as a prefix.
for test in tcObjects:
if isinstance(test, Group):
for case in test.testCases:
case.name = test.name + '_' + case.name

# Create a test set Parameter
testSetParams = []
if "test_set_parameters" in testSetInfo and "parameter" in testSetInfo["test_set_parameters"]:
testSetParams = __setParam(testSetParams, testSetInfo["test_set_parameters"]["parameter"])

# If duration is 0, it is converted to a Time type with units.
for param in testSetParams:
if param.get('name') == 'duration' and param.get('value') == '0':
param['value'] = '0S'
break

# Save dependency dependency data in test suite
dep_params = {}
try:
for case in tcObjects:
if case.dependency:
for deps in case.dependency:
first_key = 'test_name' if 'test_name' in deps else 'test_alias' if 'test_alias' in deps else None
second_key = 'status' if 'status' in deps else 'inner' if 'inner' in deps else None
if not first_key or not second_key or not deps[first_key] or not deps[second_key]:
dep_params = {}
raise Exception('Dependency data error in testset, pls have a check')
full_name = deps[first_key] + '_' + deps[second_key]

if not full_name in dep_params:
dep_params[full_name] = []
dep_params[full_name].append(case)

except Exception, err:
uniLogger.warn('Create dependency data error, error msg: %s' % err)

testSetDir = Log.LogFileDir
testSetCustomParams = {"name": testSetName,
"identities": testSetIds,
"test_set_params": testSetParams,
"tests": tcObjects,
"hooks": hookObjects,
"log_dir": testSetDir,
"build_params": buildParameters,
'guid': mainConfig.get('guid'),
'id': testSetInfo.get('id'),
'detail': testSetInfo.get('detail'),
'deps': dep_params}
return Set(testSetCustomParams)


def __generateGlobalTestCaseParameter(testSetInfo):
"""Get the global parameter of the test case

Args:
testSetInfo (dict): The test suite information dictionary parsed by xml.

Returns:
globalTestCaseParameters (dict): Global parameter information obtained from the test suite.

"""
globalTestCaseParameters = []
if "general_test_case_parameters" in testSetInfo and "param" in testSetInfo['general_test_case_parameters']:
globalTestCaseParameters = __setParam(globalTestCaseParameters,
testSetInfo["general_test_case_parameters"]['param'])
return globalTestCaseParameters


def __setTestSetName(testSetInfo):
"""Set the test suite name

Args:
testSetInfo (dict): The test set information read in the testSet xml file.

Returns:
testSetName (str): Test suite name, return None if it does not exist.

Examples:
testSetName = __setTestSetName(testSetInfo)

"""
if "name" in testSetInfo and testSetInfo["name"]:
testSetName = testSetInfo["name"]
return testSetName
else:
return None


def __setExecutionParams(mainConfigData):
"""Set test execution parameters
Args:
mainConfigData (dict): The information read in the mainConfig xml file.
Returns:
executionParams (dict): The data under the "execution_parameters" tag in the mainConfig xml file.
"""
executionParams = []
if "execution_parameters" in mainConfigData and mainConfigData["execution_parameters"] \
and "param" in mainConfigData["execution_parameters"] and mainConfigData["execution_parameters"]["param"]:
executionParams = __setParam(executionParams, mainConfigData["execution_parameters"]["param"])

return executionParams


def __createTestEngine(tcObjects, testSetObject, executionParams, statusdb):
"""Create a test engine

Args:
testSetObject (instance): Test set object.
tcObjects (list): A list of test case objects.
executionParams (dict): The log configuration raw data in the mainConfig file, the key-value pairs are described as follows:
{
Execution_parameters (dict): Test global parameters.
{
Param (dict|list): Tests a global parameter dictionary or list, one parameter is dict and multiple are list.
{
Name (str): The name of the parameter.
Value (str): The value of the parameter.
}
}
}

Returns:
engineObject (instance): Test engine instance object.

Raises:
ObjectNotFoundException: Returns when the test engine object fails to create.

"""
engineObject = None
engineType = "standard"
parallel = testSetObject.getParameter('parallel')['parallel']
duration = testSetObject.getParameter('duration')['duration']
bbt = testSetObject.getParameter('bbt')['bbt']
durationNumber = Units.getNumber(duration)

if bbt and not parallel:
engineType = 'bbt'

if parallel:
for tc in tcObjects:
if isinstance(tc, RatsCase):
engineType = "rats"
break
if not durationNumber:
engineType = "standard"

if bbt and durationNumber == 0:
engineType = 'bbt'

if bbt and durationNumber > 0:
engineType = 'bbt_rats'

if engineType == "standard":
uniLogger.info("Running Test Set With the Standard Engine. ")
engineParams = {"test_set": testSetObject,
"params": executionParams,
"statusdb": statusdb}
engineObject = Engine(engineParams)

if engineType == "rats":
uniLogger.info("Running Test Set With the Rats Engine. ")
engineParams = {"test_set": testSetObject,
"params": executionParams,
"statusdb": statusdb}
engineObject = RatsEngine(engineParams)
Log.setConfig(isMultithreading=True)

if engineType == 'bbt':
uniLogger.info("Running Test Set With the BBT Engine. ")
engineParams = {"test_set": testSetObject,
"params": executionParams,
"statusdb": statusdb}
engineObject = BBTEngine(engineParams)
# Log.setConfig(isMultithreading=True)

if engineType == 'bbt_rats':
uniLogger.info("Running Test Set With the BBT Rats Engine. ")
engineParams = {"test_set": testSetObject,
"params": executionParams,
"statusdb": statusdb}
engineObject = BBTRatsEngine(engineParams)
Log.setConfig(isMultithreading=True)

return engineObject


def __createHookObject(testSetInfo, resourceObject, testSet):
"""Create a hook object configured in the test suite

Args:
resourceObject (instance): The resource object to which the hook belongs.
testSetInfo (dict): The test set information read in the testSet xml file.
Returns:
hookObjects (list): list of hook objects.
"""
global uniLogger
tmpHooks = []
if "hooks" in testSetInfo and "hook" in testSetInfo["hooks"]:
tmpHooks = __setParam(tmpHooks, testSetInfo["hooks"]["hook"])

tmpTestCaseGeneralParam = []
if "general_test_case_parameters" in testSetInfo \
and "param" in testSetInfo["general_test_case_parameters"]["param"]:
tmpTestCaseGeneralParam = __setParam(tmpTestCaseGeneralParam,
testSetInfo["general_test_case_parameters"]["param"])

hookObjects = []
hookFailed = False
for hookInfo in sorted(tmpHooks, key=lambda hook: hook["id"]):
location = hookInfo.get("location")
hookName = hookInfo.get("name")
hookModule = re.sub(r'[\\|/]', ".", location)
params = []
if "parameters" in hookInfo and "param" in hookInfo["parameters"]:
params = __setParam(params, hookInfo["parameters"]["param"])

localParamDict = {}
for localParam in params:
localParamDict[localParam["name"]] = localParam

for globalParam in tmpTestCaseGeneralParam:
if globalParam["name"] not in localParamDict:
localParamDict[globalParam["name"]] = globalParam
elif "override" in globalParam and globalParam["override"]:
tmpDict = globalParam
tmpDict.pop("override")
localParamDict[tmpDict["name"]] = tmpDict
params = localParamDict.itervalues()

try:
__import__(hookModule)
hookObj = getattr(sys.modules[hookModule], hookName)({"resource": resourceObject,
"params": params,
"test_set": testSet})
hookObjects.append(hookObj)
except Exception, errorMsg:
hookFailed = True
uniLogger.error("Unable to import %s module or Unable to create the Hook object for %s.\n%s"
% (hookModule, hookModule, traceback.format_exc()))
if hookFailed:
uniLogger.error("Unable to import module or Unable to create the Hook object, \n"
"Please check the log file for further details..")
uniLogger.warn("UniAutos will be Exit Now.")
sys.exit(1)

return hookObjects


if __name__ == '__main__':
# Main program entry
if sys.version_info >= (3, 0):
raise RuntimeError('You need python 2.7 for UniAutos.')

mainConfigInfo = usage()
execute(mainConfigInfo)
