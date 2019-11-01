# coding:utf-8
import SocketServer
import threading
import traceback
import time
import logging
import subprocess
from xml.etree.ElementTree import Element,tostring
import os.path
from lxml import etree
from lxml.etree import ElementTree, SubElement
import re
import sys

from datetime import datetime
logger = logging.getLogger(__name__)

class CommandHander(object):
    GETFRAGMENT = 'xCloudAgent.getFragmentForRun'
    RUNFRAGMENT = 'xCloudAgent.runFragment'

    def __init__(self):
        self.projectPath = ''
        self.serverUrl = 'http://127.0.0.1:10090/server'
        self.taskId = ''
        self.testcaseId = ''
        self.subtestcaseid = ''
        self.requestURL = 'http://127.0.0.1:10091/agent'

        self.apmpath = os.path.join(self.projectPath, 'results')
        self.scriptName = 'test'
        self.fragmentURL = self.projectPath
        self.popen = None

        self.testCasename = ''

        self.startTime = int(time.time())

    def composeResponse(self, errorcode, content):
        resp = 'errcode=%d,desp=%s\r\n\r\n' % (errorcode, content)
        return resp

    def openprojectbypath(self, path):
        self.projectPath = os.path.normpath(path)
        if not os.path.exists(self.projectPath):
            return self.composeResponse(1, 'bad project path')
        return self.composeResponse(0, 'Operation succeed')

    def isrunning(self):
        logger.info("enter in to isrunning")
        if hasattr(self, "popen") and self.popen:
            status = self.popen.poll()
        else:
            status = 1
        if status != None:
            response = self.composeResponse(0, 'false') # not running
        else:
            response = self.composeResponse(0, 'true') # running
        return response

    def __getTestCaseFilePath(self, testcaseName):
        filePath = None
        for root, dirs, files in os.walk(self.projectPath):
            if "UniAutosScript.py" in files:
                filePath = root
                break
        return filePath

    def runtestcase(self, testcaseName):
        #bug must be unicode path, list report buffer overflow
        self.filepath = self.__getTestCaseFilePath(testcaseName)

        if "HUTAF_iTICC_UniAutos_xCloud_0001" == testcaseName:
            configfile = "mainConfig_Single.xml"
            testSetFileName = "testSetInfo_Single.xml"
            testBedFileName = "testBedInfo_Single.xml"
        elif "TC_ChangeLunName" == testcaseName:
            testSetFileName = "testSetInfo_Standard.xml"
            testBedFileName = "testBedInfo_Standard.xml"
            configfile = "mainConfig_Standard.xml"
        else:
            testSetFileName = "testSetInfo_Repeat.xml"
            testBedFileName = "testBedInfo_Repeat.xml"
            configfile = "mainConfig_Repeat.xml"

        envFilePath = ".."+os.sep+".."+os.sep+"ECM"+os.sep+"GTRECM"+os.sep+"tmp"+os.sep+"env.xml"
        generateTestSetFile(testcaseName, self.filepath+os.sep+"Config"+os.sep+testSetFileName)
        generateTestBedFile(envFilePath, self.filepath+os.sep+"Config"+os.sep+testBedFileName)
        #self.filepath = os.path.dirname(self.filepath.decode('GBK').encode('utf-8').replace('\\', '\\\\'))
        self.filepath = os.path.normpath(self.filepath.encode('utf-8') + os.sep + "UniAutosScript.py")
        logger.info('self.filepath now:')
        logger.info(self.filepath)

        if not self.filepath:
            return self.composeResponse(1, 'test case not found')

        logger.info('ProjectPath Analyze:')
        logger.info(self.filepath)

        self.startTime = int(time.time())
        self.testCasename = testcaseName
        command = "python "+self.filepath +" --configFile " + configfile
        command = command.encode("utf-8")
        stdinFile = open('stdin.txt', 'w')
        stdoutFile = open('stdout.txt', 'w')
        stderrFile = open('stderr.txt', 'w')
        try:
            logger.info("Execute cmd:" + command)
            self.popen = subprocess.Popen(command,
                                          shell=True,
                                          stdin=sys.stdin,
                                          stdout=sys.stdout,
                                          stderr=sys.stderr,
                                          universal_newlines=True)

        # self.popen = subprocess.Popen(command,
        # stdin=stdinFile,
        # stdout=stdoutFile,
        # stderr=stderrFile,
        # universal_newlines=True)

        # self.popen = subprocess.Popen(command,
        # stdin=subprocess.PIPE,
        # stdout=subprocess.PIPE,
        # stderr=subprocess.PIPE,
        # universal_newlines=True)
        except Exception, e:
            logger.info(str(e))
            return self.composeResponse(1, 'run test case failed')
        return self.composeResponse(0, 'Operation succeed')

    def getticcrunresult(self):
        result = {}
        status = self.popen.poll()
        if status != None:
            out = self.popen.communicate()
            result["stdout"] = out[0]
            result["stderr"] = out[1]
        result["rc"] = status

        if result["rc"] == 0:
            runResult = "PASS"
        else:
            runResult = "FAIL"

        endTime = int(time.time())
        timeEclapse = endTime - self.startTime

        executeTime = '00:00:01'
        if timeEclapse >= 0:
            m, s = divmod(timeEclapse, 60)
            h, m = divmod(m , 60)
            executeTime = '%02d:%02d:%02d' % (h, m, s)
        else:
            endTime = self.startTime + 1
        startTime = datetime.fromtimestamp(self.startTime).strftime("%Y-%m-%d %H'%M'%S")
        endTime = datetime.fromtimestamp(endTime).strftime("%Y-%m-%d %H'%M'%S")

        root = Element('Root', {'Title' : "xCloud Automation Test Report",'LogFileType' : "Index",'Version' : "3",\
        'StartTime' : startTime, 'EndTime' : endTime})

        child = Element('TestCase',
                        {'TestCaseName' : self.testCasename.encode('utf-8'),
                         'TestCaseID' : self.testcaseId,
                         'Level' : "1",
                         'IncludeID' : "0",
                         'Mode' : "NORMAL",
                         'TestSuite' : "0",
                         'DocumentID' : "1",
                         'LogFileType' : "File",
                         'TestCaseResult' : runResult,
                         'TestCaseStartTime' : startTime,
                         'TestCaseEndTime' : endTime,
                         'TestCaseExecuteTime' : str(executeTime),
                         'TestCaseFilePath' : r".\3499e6f1-7d39-3e78-9a00-cc4735c93433\log.html"})

        root.append(child)
        declare = ''
        res = declare + tostring(root, encoding="utf-8", method="xml")
        return self.composeResponse(0, res)

class RequestHandler(SocketServer.StreamRequestHandler):
    clientsCache = {}
    "Handles one request to mirror some text"
    def parseCommand(self, data):
        logger.info(data)
        args = data.strip('\r\n')

        index = args.find(' ')
        if -1 == index:
            return args, ''

        command = args[:index]
        argument = args[index+1:]

        logger.info("command:[%s] argument:[%s]" % (command, argument))

        return command, argument

    def command_openprojectbypath(self, args):
        return self.commandHandler.openprojectbypath(args)

    def command_isrunning(self, args):
        return self.commandHandler.isrunning()

    def command_getticcrunresult(self, args):
        return self.commandHandler.getticcrunresult()

    def command_runtestcase(self, args):
        testcaseName = args
        return self.commandHandler.runtestcase(testcaseName)

    def handle(self):

        self.commandHandler = CommandHander()
        client_cache_key = self.client_address[0]

        if RequestHandler.clientsCache.has_key(client_cache_key):
            self.commandHandler = self.clientsCache[client_cache_key]
        else:
            RequestHandler.clientsCache[client_cache_key] = self.commandHandler

        while True:
            try:
                data = self.request.recv(1024)

                if not data:
                    break

                logger.info('--%r--: %s' % (self.client_address, data.strip('\r\n')))

                command, args = self.parseCommand(data)
                try:
                    commandHandle = getattr(self, 'command_' + command)
                except:
                    resp = 'errcode=1,desp=unhandled command\r\n\r\n'
                    continue
                resp = commandHandle(args)
                logger.info('--%r--:%s' % (self.client_address, resp.strip('\r\n')))
                self.request.sendall(resp)
            except Exception:
                logger.error(traceback.format_exc())
                error_resp = 'errcode=1,desp=internel error'
                self.request.sendall(error_resp)
                break


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

    def generateTestSetFile(testCaseName, testSetFilePath):
        logger.info("enter into generateTestSetFile method.")
        testSetTree = etree.ElementTree()
        root = etree.Element("opt", {"doc_type": "TC_CFG", "version":"2"})
        testSetTree._setroot(root)

        test_set = etree.Element("test_set", {"name":"TestSet"})
        test_set_parameters = etree.Element("test_set_parameters")
        SubElement(test_set_parameters, "parameter", {"name": "duration", "value": "1H"})
        SubElement(test_set_parameters, "parameter", {"name": "parallel", "value": "True"})

        tests = etree.Element("tests")
        test = etree.Element("test", {"type": "case", "name": testCaseName})
        identities = etree.Element("identities")
        SubElement(identities, "identity", {"name":"ax_id", "id":"275"})
        SubElement(test, "location").text="Unified/OceanStor/Standard/"+testCaseName
        test.append(identities)

        tests.append(test)

        test_set.append(test_set_parameters)
        test_set.append(tests)

        root.append(test_set)
        indent(root)
        testSetTree.write(testSetFilePath, encoding="utf-8", xml_declaration=True, standalone=False)
        logger.info("generate testsetfile success")

    def generateTestBedFile(envFilePath, testBedFilePath):
        logger.info("enter in generateTestBedFile method.")
        chgEncode(envFilePath)
        devices, links = parserEnvFile(envFilePath)
        logger.info("parser env file success.")
        testBedTree = ElementTree()
        root = etree.Element("testbedinfo", {"doc_type": "testbed"})
        testBedTree._setroot(root)

        global_environment_info = etree.Element("global_environment_info")
        SubElement(global_environment_info,
                   "active_directory",
                   {"domain":"win8adserver.drm.lab.huawei.com",
                    "cifs_user":"CustomAdmin",
                    "cifs_password":"Password1!",
                    "net_bios_name":"BCD1020DM3",
                    "workgroup":"Standalone"})
        SubElement(global_environment_info,
                   "ldap",
                   {"domain":"LdapDomain",
                    "server":"10.4.4.4",
                    "user":"LdapAdmin",
                    "password":"LdapPass!",
                    "port":"389",
                    "secure":"1",
                    "user_id_attribute":"sAMAccountName",
                    "user_object_class":"user",
                    "user_search_path":"",
                    "group_member_attribute":"member",
                    "group_name_attribute":"sAMAccountName",
                    "group_object_class":"group",
                    "group_search_path":"cn=Users,dc=Fake"
                    })
        SubElement(global_environment_info, "nis", {"workgroup":"unix", "server":"10.5.5.5,10.8.8.8"})
        SubElement(global_environment_info, "ntp", {"server":"10.7.7.7,ntpserver.drm.lab.huawei.com"})
        SubElement(global_environment_info, "dns", {"server":"10.1.1.2,10.1.2.2"})
        SubElement(global_environment_info, "unisphere_central", {"server":"mozzoserver.lab.huawei.com"})
        root.append(global_environment_info)

        if devices["Server"]:
            hostsNode = etree.Element("hosts")
            hosts = devices["Server"]
            for host in hosts:
                hostNode = etree.Element("host", {"id": host["id"]})
                SubElement(hostNode,
                           "communication",
                           {"ipv4_address":host["ip"],
                            "username":host["username"],
                            "password":host["password"],
                            "port":"22","type":"standSSH"})
                SubElement(hostNode,
                           "detail",
                           {"os":"linux",
                            "python":"2.7.9",
                            "failover":"powerpath v 5.3",
                            "hba":"emulex"})
            hostsNode.append(hostNode)
        root.append(hostsNode)
        if devices["Storage"]:
            unified_devices = etree.Element("unified_devices")
            unifieds = devices["Storage"]
            unifiedID = 1
            for unified in unifieds:
                unifiedNode = etree.Element("unified", {"id":str(unifiedID)})
                environmentInfoNode = etree.Element("environment_info")
                SubElement(environmentInfoNode,
                           "active_directory",
                           {"domain":"win8adserver.lab.huawei.com",
                            "cifs_user":"CustomAdmin",
                            "cifs_password":"Pa ssword1!",
                            "net_bios_name":"BCD1020DM3",
                            "workgroup":"Standalone"})
                SubElement(environmentInfoNode,
                           "interface",
                           {"ipv4_address":"10.108.26.220",
                            "ipv4_netmask":"255.255.254.0",
                            "ipv4_gateway":"10.108.26.1",
                            "ipv6_address":"2620:0:170:741a:260:1600:8e0:96",
                            "ipv6_netmask":"24",
                            "vlan":"2",
                            "port_id":"spa_eth2"})
                SubElement(environmentInfoNode,
                           "interface",
                           {"ipv4_address":"10.108.26.222",
                            "ipv4_netmask":"255.255.254.0",
                            "ipv4_gateway":"10.108.26.1",
                            "port_id":"spa_iom_0_eth1",
                            "hostname":"BC-D1020-DM2"})
                SubElement(environmentInfoNode,
                           "network",
                           {"name":"BC-D1020-mgmt",
                            "location":"durham lab6",
                            "contact":"user name"})
                SubElement(environmentInfoNode, "remote_logging", {"host":"BC-D1021.lab.huawei.com"})
                unifiedNode.append(environmentInfoNode)

                if "IPList" in unified:
                    ips = unified["IPList"].split(",")
                    controllerNames = ["A", "B"]
                else:
                    ips = [unified["ip"]]
                    controllerNames = ["A"]
                hostIDs = {}
                for ip in ips:
                    controllerName = controllerNames.pop()
                    controllerNode = etree.Element("controller", {"name":controllerName})
                    SubElement(controllerNode,
                               "communication",
                               {"ipv4_address":ip,
                                "ipv6_address":"",
                                "username":unified["username"],
                                "password":unified["password"],
                                "port":"",
                                "type":"storSSH"})
                    managementNode = etree.Element("management")
                    toolsNode = etree.Element("tools")
                    SubElement(toolsNode,
                               "tool",
                               {"type":"adminCli", "priority":'1', "controller":controllerName})
                    hostID = getHostID(devices, links, unified["id"])
                    if hostID:
                        hostIDs[hostID] = 1
                        SubElement(managementNode, "host", {"id":hostID})
                    managementNode.append(toolsNode)
                    controllerNode.append(managementNode)
                    unifiedNode.append(controllerNode)
                hostNode = None
                if hostIDs:
                    hostNode = etree.Element("hosts")
                    unifiedNode.append(hostNode)
                for hostID in hostIDs:
                    SubElement(hostNode, "host", {"id": hostID,"type":"fc"})
            unified_devices.append(unifiedNode)
        root.append(unified_devices)
        indent(root)
        testBedTree.write(testBedFilePath, encoding="utf-8", xml_declaration=True)
        logger.info("generate testbedfile success")

    def getHostID(devices, links, deviceID):
        if "Server" not in devices:
            return None
        if not links:
            hosts = devices["Server"]
            return hosts[0]["id"]
        hostIDs = {}
        for link in links:
            if deviceID in link:
                hostIDs[link[deviceID]] = 1
        if not hostIDs:
            return None
        hosts = devices["Server"]
        keys = hostIDs.keys()
        for hostID in keys:
            for host in hosts:
                if host["id"] == hostID:
                    return hostID
        else:
            return None

    def indent(elem, level=0):
        i ="\n"+level*" "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + " "
            for e in elem:
                indent(e,level+1)
            if not e.tail or not e.tail.strip():
                e.tail =i
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail =i
        return elem

    def getTargetNode(parentNode, path):
        return parentNode.findall(path)

    def getHostInfo(properties):
        host = {}
        for prop in properties:
            attrName = prop.get("name")
            if re.match("id|ip|username|password", attrName, re.IGNORECASE):
                if prop.text:
                    host[attrName] = prop.text.strip()
        return host

    def chgEncode(filePath):
        fp1 = open(filePath, 'r')
        info1 = fp1.read()
        tmp = info1.decode('GBK')

        fp2 = open(filePath, 'w')
        info2 = tmp.encode('UTF-8')
        fp2.write(info2)
        fp2.close()

    def getController(properties):
        controller = {}
        for prop in properties:
            attrName = prop.get("name")
            if re.match("id|ip|username|password|IPList", attrName, re.IGNORECASE):
                if prop.text and len(prop.text.strip()) > 0:
                    controller[attrName] = prop.text.strip()
        return controller

    def parserEnvFile(envFilePath):
        logger.info("enter into parserEnvFile method.")
        devicesInfo = {}
        document = etree.ElementTree(file=envFilePath)
        root = document.getroot()

        # 1 parser devices
        devices = getTargetNode(root, "devices/device")
        for device in devices:
            properties = device.findall("properties/property")
            for prop in properties:
                if prop.text == "Server":
                    host = getHostInfo(properties)
                    if "Server" in devicesInfo:
                        devicesInfo["Server"].append(host)
                    else:
                        devicesInfo["Server"]=[host]
                    break
                if prop.text == "Storage":
                    conterller = getController(properties)
                    if "Storage" in devicesInfo:
                        devicesInfo["Storage"].append(conterller)
                    else:
                        devicesInfo["Storage"] = [conterller]
                    break
                pass

        # 2 parser links
        links = getTargetNode(root, "links/link")
        linkInfo = []
        for link in links:
            properties = link.findall("properties/property")
            tmp = {}
            key = None
            value = None
            for prop in properties:
                attrName = prop.get("name")
                if attrName == "sourceDeviceId":
                    key = prop.text.strip()
                if attrName == "targetDeviceId":
                    value = prop.text.strip()
                if key and value:
                    break
            tmp[key] = value
            linkInfo.append(tmp)

        # 3 generate testbedfile
        return devicesInfo, linkInfo

if __name__ == '__main__':
    aaa = '''[%(thread)d] time[%(asctime)s] --file[%(filename)s %(module)s %(lineno)d] %(message)s'''
    logging.basicConfig(level=logging.DEBUG,
                        format=aaa,
                        filename="xcloud.log",
                        filemode='a')
    import sys
    if len(sys.argv) < 3:
        print 'Usage: %s [hostname] [port number]' % sys.argv[0]
        sys.exit(1)
    hostname = sys.argv[1]
    port = int(sys.argv[2])

    print '------------' + str(hostname) + ':' + str(port) + '----------------'
    server = ThreadedTCPServer((hostname, port), RequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    # reportServer = HTTPReportServer.ThreadedReportHTTPServer((hostname, 10090), HTTPReportServer.HTTPRequsestHandler)
    # reportServer_thread = threading.Thread(target=reportServer.serve_forever)
    # reportServer_thread.start()