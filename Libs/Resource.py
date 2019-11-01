
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

Function: Test resources for creating and managing devices configured in the test bed.

"""

import re
import sys
import traceback
from collections import OrderedDict

from UniAutos.Util.TypeCheck import validateParam, validateDict
from UniAutos.Util.XmlParser.XmlToDict import XmlToDict
from UniAutos.Device.Host.Controller.OceanStor import OceanStor
from UniAutos.Device.Host.IPenclosure.IPenclosure import IPenclosure
from UniAutos.Device.Host.Simuenclosure.Simuenclosure import Simuenclosure
from UniAutos.Device.Host.Controller.DockerControllerHost import DockerControllerHost
from UniAutos.Device.Host.HostBase import HostBase
from UniAutos.Device.Storage.Huawei.Unified import Unified
from UniAutos.Device.Storage.Huawei.DockerUnified import DockerUnified
from UniAutos.Exception.ValueException import ValueException
from UniAutos.Device.Host.Svp import Svp
from UniAutos.Device.Host.SvpMaster import SvpMaster
from UniAutos.Device.Host.SvpIpmi import SvpIpmi
from UniAutos import Log
from UniAutos.Device.Switch.SwitchBase import SwitchBase
from UniAutos.Command import CommandBase
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Device.Host.Hypervisor.Esx import Esx
from UniAutos.Common import *
from UniAutos.Device.Host.Hypervisor.Vsphere import VSphere
from UniAutos.Device.Host.Hypervisor.HyperV import HyperV
from UniAutos.Device.Host.OpenStack import OpenStack
from UniAutos.Device.Host.Windows import Windows
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Device.Host.NasNode.OceanStor import OceanStor as OceanStorNas
from UniAutos.Device.Storage.Huawei.NasCluster import NasCluster
from UniAutos.Device.Storage.Fusion.AvailableZone import AvailableZone
from UniAutos.Device.Storage.Fusion.FusionStorageNode import FusionStorageNode
from UniAutos.Device.Storage.Fusion.Region import Region
from UniAutos.Device.Storage.DSware.DSware import DSware
from UniAutos.Device.Storage.DSware.DSwareNode import DSwareNode
from UniAutos.Device.Storage.Roc.RocNode import RocNode
from UniAutos.Device.Storage.Roc.Region import Region as RocRegion
from UniAutos.Device.Storage.Roc.AvailableZone import AvailableZone as RocAvailableZone


class Resource(object):
    """Test the resources you need to execute.

    - Create a test bed to configure the device and create it as a Resource object.
    Args:

    testBedData (dict): All the data obtained from the test bed. The value is obtained by XmlToDict.getConfigFileRawData(path) to obtain the test bed file.

    1. testBedData contains: all the data configured in the test bed to test the tags in the bed configuration, the attribute is
    Key, the value of other values ​​or attributes of the tag block is value;
    2. The following example: where "testbedinfo" is the largest block label, it is key; it contains all the data of the entire xml, so
    - its value is the other attributes and values ​​of the entire xml;
    3. "doc_type" is a property of "testbedinfo", so it is a value of "testbedinfo" and it is also a "key".
    - its value is the value of the property;
    4. When there are multiple sub-labels under the same label, and the sub-labels have the same name, the sub-label name is key, and all sub-tag values ​​form a list.
    - As the value of the tag, when there is only one same subtag, the value is dict.
    5. The root of testBedData is "testbedinfo", and the root contains: "global_environment_info", "hosts",
    Device and network configuration information required for testing such as "unified_devices".

    Attributes：
    self.hosts = {}
    self.unifiedDevices = {}
    self.switches = {}
    self.openStacks = {}
    self.srms = {}
    self.bmcDevices = {}
    self.kvms = {}
    self.esxes = {}
    self.vspheres = {}
    self.hypervs = {}
    self.connectionServers = {}
    self.svps = {}
    self.controllers = {}
    self.testbedFile = ""
    self.initState = ""
    self.initErrors = list
    self.testEngine = None

    Returns:
    Resource (instance): Instance object.

    Examples:
    resourceObject = Resource(testBedData)

    """

    # Default definition of WRAPPER type
    WRAPPERS = {
    "adminCli": {
    "unified": "UniAutos.Wrapper.Tool.AdminCli.AdminCli",
    "class": "AdminCli"},
    "mmlCli": {
    "unified": "UniAutos.Wrapper.Tool.Mml.MmlCli",
    "class": "MmlCli"},
    "diagnoseCli": {
    "unified": "UniAutos.Wrapper.Tool.Diagnose.DiagnoseCli",
    "class": "DiagnoseCli"},
    "debugCli": {
    "unified": "UniAutos.Wrapper.Tool.Debug.DebugCli",
    "class": "DebugCli"},
    "developerCli": {
    "unified": "UniAutos.Wrapper.Tool.Developer.DeveloperCli",
    "class": "DeveloperCli"},
    "restOceanStor": {
    "unified": "UniAutos.Wrapper.Api.Rest.OceanStorRestV300R003C10",
    "class": "OceanStorRest"},
    "ism": {
    "unified": "UniAutos.Wrapper.Tool.Selenium.DeviceManager.Ism",
    "class": "Ism"},
    "minisystemCli": {
    "unified": "UniAutos.Wrapper.Tool.Minisystem.MinisystemCli",
    "class": "MinisystemCli"},
    "dev_diagnoseCli": {
    "unified": "UniAutos.Wrapper.Tool.DevDiagnose.DevDiagnoseCli",
    "class": "DevDiagnoseCli"},
    "upgradeCli": {
    "unified": "UniAutos.Wrapper.Tool.Upgrade.UpgradeCli",
    "class": "UpgradeCli"}}

    @validateParam(testBedData=dict, skip=bool)
    def __init__(self, testBedData, skip=False):
        self.logger = Log.getLogger(str(self.__module__))
        # Add the pcie data in the test bed to the associated array data, the key is , and the data structure is list
        # pcie and array are n to 1 relationship
        if 'switches' in testBedData and testBedData['switches'] \
        and 'switch' in testBedData['switches'] \
        and testBedData['switches']['switch'] \
        and 'unified_devices' in testBedData and testBedData['unified_devices'] \
        and 'unified' in testBedData['unified_devices'] \
        and testBedData['unified_devices']['unified']:
            if isinstance(testBedData['switches']['switch'], dict):
                switchTemp = [testBedData['switches']['switch']]
            else:
                switchTemp = testBedData['switches']['switch']
            for switch in switchTemp:
                if switch['type'] == 'Pcie' and switch['array_id'] is not None:
                    if isinstance(testBedData['unified_devices']['unified'], list):
                        for index in xrange(len(testBedData['unified_devices']['unified'])):
                            if testBedData['unified_devices']['unified'][index]['id'] == switch['array_id']:
                                if 'pcies' not in testBedData['unified_devices']['unified'][index]:
                                    testBedData['unified_devices']['unified'][index]['pcies'] = []
                                testBedData['unified_devices']['unified'][index]['pcies'].append(switch)
                    elif isinstance(testBedData['unified_devices']['unified'], dict):
                        if testBedData['unified_devices']['unified']['id'] == switch['array_id']:
                            if 'pcies' not in testBedData['unified_devices']['unified']:
                                testBedData['unified_devices']['unified']['pcies'] = []
                            testBedData['unified_devices']['unified']['pcies'].append(switch)

        self.testBedMetaData = testBedData
        self.rawResourceData = {}
        for devType in DEVICESPEC:
            if devType in testBedData:
                self.rawResourceData[devType] = testBedData[devType]
        self.globalEnvironmentInfo = testBedData.get('global_environment_info', {})
        # defined the variables
        self.initState = "incomplete"
        self.initErrors = list()
        self.testEngine = None
        self.unifiedInitError = 0
        self.dockerUnifiedInitError = 0
        self.hostInitError = 0
        self.switcheInitError = 0
        self.regionInitError = 0
        self.dswareInitError = 0
        self.rocInitError = 0
        # Set the device arrays to empty arrays by default
        self.hosts = {} # The host object dictionary, key is the id configured by the host in the test bed, and the value is the host object corresponding to the id.
        self.unifiedDevices = {} # The key of the dictionary is the ID of the unifiedDevice, and the value is the dictionary of the unifiedDevice object.
        self.dockerUnifiedDevices = {} # The key of the dictionary is the ID of dockerunifiedDevice, and the value is the dictionary of the unifiedDevice object.
        self.switches = {} # Switch object dictionary, key is the id configured by the switch in the test bed, and the value is the object corresponding to the id.
        self.openStacks = {}
        self.srms = {}
        self.bmcDevices = {}
        self.kvms = {}
        self.esxes = []
        self.vspheres = []
        self.hypervs = []
        self.connectionServers = {}
        self.svps = {}
        self.controllers = {}
        self.ipenclosures = {}
        self.simuenclosures = {}
        self.dockerControllers = {}
        self.nasClusters = {}
        self.__nasNodes = {}
        self.regions = {}
        self.__available_zones = {}
        self.__rocNodes = {}
        self.dswares = {}
        self.__dswareNodes = {}
        self.rocs = {}
        self.__rocNodes = OrderedDict()
        self.__testBedLocation = None
        self.__testSetLocation = None

        # initialize here
        if skip:
            self.logger.warn("simulation depoy skip initialize")
        else:
            self.initialize()

        # The controller of a single Unified device saves the controller information when creating the specified Unified Device, used to create a Wrapper.
        #Controller object saved controller object can not be used.
        self.setDeviceResource()

    @property
    def testBedLocation(self):
        """Test bed file path """
        return self.__testBedLocation

    @property
    def testSetLocation(self):
        """Test suite file path """
        return self.__testSetLocation

    def setBedLocation(self, location):
        """Set test bed file path
        Args:
        Location (str): test bed file path
        """
        self.__testBedLocation = location

    def setSetLocation(self, location):
        """Set the test suite file path
        Args:
        Location (str): test suite file path
        """
        self.__testSetLocation = location

    def initialize(self, supportAbnormalController=False):
        """Attemps to create the object representation of the Testbed XML.
        Any errors are captured, saved, and are accessible via the getInitErrors()
        method

        Args:
        supportAbnormalController (Bool) - (Optional) if supporting abnormal Controller
        default is False
        """

        params = self.getRawResourceData()

        initErrors = []

        # create hosts
        if 'hosts' in params and params['hosts'] and 'host' in params['hosts'] and params['hosts']['host']:
            rawHosts = self.__changeParamToList(params['hosts']['host'])
            try:
                hostErrorMsg = self.__createHosts(rawHosts)
                if self.hostInitError > 0 and len(hostErrorMsg) > 0 :
                    initErrors.extend(hostErrorMsg)
                self.__registerWrappresToVsphereHosts()
            except Exception, e:
                initErrors.append(e.message + "\n" + traceback.format_exc())

        # create unified devices
        if 'unified_devices' in params and params['unified_devices'] and 'unified' in params['unified_devices'] and params['unified_devices']['unified']:
            rawUnifieds = self.__changeParamToList(params['unified_devices']['unified'])
            try:
                # Only one svp exists in a single Unified device, and the svp information when the specified Unified Device is temporarily created is saved for creating a Wrapper.
                # resource object saved svp object can not be used.
                controllerdata = rawUnifieds[0]["controller"]
                controllerdata = self.__changeParamToList(controllerdata)
                if len(controllerdata) and "communication" in controllerdata[0] and controllerdata[0]["communication"].get('type') == 'DockerSSH':
                    unifiedErrorMsg = self.__createDockerUnifiedDevices(rawUnifieds, supportAbnormalController)
                else:
                    unifiedErrorMsg = self.__createUnifiedDevices(rawUnifieds, supportAbnormalController)
                if self.unifiedInitError > 0 and len(unifiedErrorMsg) > 0:
                    initErrors.extend(unifiedErrorMsg)
            except Exception, e:
                initErrors.append(e.message + "\n" + traceback.format_exc())

        # create switches
        if 'switches' in params and params['switches'] and 'switch' in params['switches'] and params['switches']['switch']:
            rawSwitches = self.__changeParamToList(params['switches']['switch'])
            try:
                switchErrorMsg = self.__createSwitches(rawSwitches)
                if self.switcheInitError > 0 and len(switchErrorMsg) > 0:
                    initErrors.extend(switchErrorMsg)
            except Exception as e:
                    initErrors.append(e.message + "\n" + traceback.format_exc())

        # create nas clusters
        if 'nas_devices' in params and params['nas_devices'] and 'nas_cluster' in params['nas_devices'] and params['nas_devices']['nas_cluster']:
            rawNases = self.__changeParamToList(params['nas_devices']['nas_cluster'])
            try:
                self.nasClusters = self.__createNasClusters(rawNases)
            except Exception as e:
                initErrors.append(e.message + "\n" + traceback.format_exc())

        # For Roc
        if params.get('regions') and params['regions'].get('version') == '8':
            if params['regions'].get('region') is not None:
                rawRegions = self.__changeParamToList(params['regions']['region'])
                try:
                    rocErrorMsg = self.__createRocRegions(rawRegions)
                    if self.rocInitError > 0 and len(rocErrorMsg) > 0:
                        initErrors.extend(rocErrorMsg)
                except Exception as e:
                        initErrors.append(e.message + "\n" + traceback.format_exc())

        # The configuration information of the Regions in the test bed, and the specific Regions, create the Regions
        if 'regions' in params and params['regions'] and 'version' not in params['regions'] and 'region' in params['regions'] and params['regions']['region']:
            rawRegions = self.__changeParamToList(params['regions']['region'])
            try:
                regionErrorMsg = self.__createRegions(rawRegions)
                if self.regionInitError > 0 and len(regionErrorMsg) > 0:
                    initErrors.extend(regionErrorMsg)
            except Exception as e:
                    initErrors.append(e.message + "\n" + traceback.format_exc())

        # Dswares configuration information in the test bed, and specific dswares, create dswares
        if 'dswares' in params and params['dswares'] and 'dsware' in params['dswares'] and params['dswares']['dsware']:
            rawDswares = self.__changeParamToList(params['dswares']['dsware'])
            try:
                dswareErrorMsg = self.__createDswares(rawDswares)
                if self.dswareInitError > 0 and len(dswareErrorMsg) > 0:
                    initErrors.extend(dswareErrorMsg)
            except Exception as e:
                initErrors.append(e.message + "\n" + traceback.format_exc())

        # Roc Temporary plan temporarily deleted
        # if params.get('rocs') and params.get('rocs', {}).get('roc'):
        # rawRocs = self.__changeParamToList(params.get('rocs', {}).get('roc'))
        # try:
        # rocErrorMsg = self.__createRocs(rawRocs)
        # if self.rocInitError > 0 and len(rocErrorMsg) > 0:
        # initErrors.extend(rocErrorMsg)
        # except Exception as e:
        # initErrors.append(e.message + '\n' + traceback.format_exc())

        self.initErrors = initErrors

        if len(initErrors) > 0:
            self.initState = 'failed'
            # repeat log, delete it.
            # errors = "\n".join(initErrors)
            # self.logger.error("There were errors creating the resource object:\n %s" % errors)

            # Because of there were errors during the resource initialization, just return
            return

        if self.globalEnvironmentInfo:
            allDevices = self.getAllDevices()
            for device in allDevices:
                if device.environmentInfo:
                    for envItem in self.globalEnvironmentInfo:
                        if envItem not in device.environmentInfo:
                            device.environmentInfo[envItem] = self.globalEnvironmentInfo[envItem]
                else:
                    device.environmentInfo = self.globalEnvironmentInfo

        self.initState = 'complete'

    def getRawResourceData(self):
        """Gets the raw Dict of the testbed xml info

        Returns:
        rawResourceData (dict) : Absolute path to the testbed XML file.

        """
        if self.rawResourceData:
            return self.rawResourceData
        else:
            self.logger.info("testbed is not specified")
            return {}

    def setTestbedFile(self, testbedFile):
        """Sets the absolute path to the testbed XML file

        Args:
        testbedFile (str) : Absolute path to the testbed XML file

        """
        self.testbedFile = testbedFile

    def getTestbedFile(self):
        """Gets the absolute path to the testbed XML file
        Returns:
        path (str) : Absolute path to the testbed XML file

        """
        return self.testbedFile

    def getInitState(self):
        """Gets the absolute path to the testbed XML file
        Returns:
        path (str) : Absolute path to the testbed XML file

        """
        return self.initState

    def getInitErrors(self):
        """If the initialize() call failed intiState='failed', the error message list
        would be returned
        Returns:
        initErrors (List) : List of initialize errors

        """
        return self.initErrors

    def setTestEngine(self, testEngine):
        """Sets the UniAutos.Test.Engine being used with this Resource object

        Args:
        testEngine (Engine) : Engine Object
        """
        self.testEngine = testEngine

    def getTestEngine(self):
        """gets the UniAutos.Test.Engine being used with this Resource object

        Returns:
        testZEngine (UniAutos.Test.Engine) : Engine Object

        """
        return self.testEngine

    def __registerWrappresToVsphereHosts(self):
        """Tries to consturct and register powerCLI wrapper to
        the vSphere hosts if there is any vSphere host.

        """
        vSphereHosts = []
        windowsHosts = []
        for hostObj in self.getSpecifiesTypeDevices("host"):
            if isinstance(hostObj, VSphere):
                vSphereHosts.append(hostObj)
            elif isinstance(hostObj, Windows):
                windowsHosts.append(hostObj)
        if len(vSphereHosts) == 0:
            self.logger.debug('There is no vSphere host')
            return
        if len(windowsHosts) == 0:
            self.logger.debug('There is no PowerCLI tool wrapper registered to vSphere hosts.')
            return
        powcliHost = None

        for winHost in windowsHosts:
            if winHost.isPowercliInstalled():
                powcliHost = winHost
                break

        if not powcliHost:
            self.logger.debug('There is no PowerCLI tool wrapper registered to vSphere hosts.')
            return

        for vHost in vSphereHosts:
            vHost.registerPowerCliWrapper(powcliHost)
        pass

    def __createHostObject(self, host):
        """Create a host object
        - Get configuration data for a single host from __createHosts() and then create a single host object.

        Args:
        hostRawData (dict): Configuration data for a single host.

        Returns:
        hostObject (instance): A single host object.

        Raises:
        DictKeyException: There is no 'communication' configuration in a single host configuration data.
        UniAutosException: Failed to create host object.
        """
        template = {"id" : {"types": str, "optional": True},
                    "communication" : {"types": dict, "optional": True},
                    "detail" : {"types": dict, "optional": True},
                    "virtualized" : {"types": dict, "optional": True},
                    "monitor" : {"types": dict, "optional": True},
                    "environment_info" : {"types": dict, "optional": True},
                    "openstack" : {"types": dict, "optional": True},
                    "vCenter" : {"types": dict, "optional": True}}
        host = validateDict(host, template)
        hostDict = {}
        for paramKey in ['username', 'password', 'ipv4_address',
                         'ipv6_address', 'port', 'type', 'ssh_private_key', 'ssh_public_key',
                         'max_session']:
            if 'communication' in host and paramKey in host['communication']:
                hostDict[paramKey] = host['communication'][paramKey]
        if 'detail' in host and 'os' in host['detail']:
            hostDict['os'] = host['detail']['os']
        if 'detail' in host and host['detail']:
            hostDict['detail'] = host['detail']
        if 'vCenter' in host and host['vCenter']:
            hostDict['vCenter'] = host['vCenter']
        if 'monitor' in host:
            hostDict['monitor_processes'] = []
            if 'process' in host['monitor'] and type(host['monitor']['process']) == 'dict':
                hostDict['monitor_processes'].append(host['monitor']['process']['name'])
            elif 'process' in host['monitor']:
                for process in host['monitor']['process']:
                    if 'name' in process:
                        hostDict['monitor_processes'].append(process['name'])
        # If the user indicated this is a hypervisor, we try to create an object
        # of the indicated type (currently only ESX) is supported
        if 'virtualized' in host and 'hypervisor' in host['virtualized']:
            paramsDict = {'type' : None, 'persistent_connection' : None,
                          'ip_address' : None,
                          'username' : None,
                          'password' : None,
                          'port' : None}
            if 'ipv4_address' in hostDict:
                paramsDict['ip_address'] = hostDict['ipv4_address']
            elif 'ipv6_address' in hostDict:
                paramsDict['ip_address'] = hostDict['ipv6_address']
            for paramKey in ['username', 'password', 'type', 'port']:
                if paramKey in hostDict:
                    paramsDict[paramKey] = hostDict[paramKey]
            if not re.search('vsphere', host['virtualized']['hypervisor'], re.I):
                hostDict['command'] = CommandBase.discover(paramsDict['type'],
                                                           paramsDict['ip_address'],
                                                           paramsDict['username'],
                                                           paramsDict['password'],
                                                           paramsDict['persistent_connection'],)
            vHost = None
            if re.search('ESX', host['virtualized']['hypervisor'], re.I):
                vHost = Esx(hostDict['username'], hostDict['password'], hostDict)
                self.esxes.append(vHost)
            if re.search('vsphere', host['virtualized']['hypervisor'], re.I):
                if 'username' in host['virtualized'] and 'password' in host['virtualized']:
                    hostDict['tool_username'] = host['virtualized']['username']
                    hostDict['tool_password'] = host['virtualized']['password']
                vHost = VSphere(hostDict['username'], hostDict['password'], hostDict)
                self.vspheres.append(vHost)
            # the last code is not use.
            if re.search('hyperv', host['virtualized']['hypervisor'], re.I):
                hostDict['cluster_name'] = host['virtualized'].get('cluster_name')
                vHost = HyperV(hostDict['username'], hostDict['password'], hostDict)
                self.hypervs.append(vHost)
            if re.search('srm', host['virtualized']['hypervisor'], re.I):
                # TODO SRM hypervisor will be supported soon
                raise UniAutosException('SRM hypervisor will be supported soon')
            if re.search('kvm', host['virtualized']['hypervisor'], re.I):
                # TODO KVM hypervisor will be supported soon
                raise UniAutosException('KVM hypervisor will be supported soon')
            if re.search('connection_server', host['virtualized']['hypervisor'], re.I):
                # TODO Connection server hypervisor will be supported soon
                raise UniAutosException('Connection server hypervisor will be supported soon')
            if vHost and 'id' in host:
                # return the virtualized host, but firt add testbed_id
                vHost.testBedId = host['id']
            if vHost is not None:
                return vHost
        # If the user indicated this is an openstack, we try to
        # create an object of the indicated type
        if 'openstack' in host and 'type' in host['openstack']:
            paramsDict = {'type' : None,
                          'persistent_connection' : None,
                          'ip_address' : None,
                          'username' : None,
                          'password' : None,
                          'port' : None}
            if 'ipv4_address' in hostDict:
                paramsDict['ip_address'] = hostDict['ipv4_address']
            elif 'ipv6_address' in hostDict:
                paramsDict['ip_address'] = hostDict['ipv6_address']
            for paramKey in ['username', 'password', 'type', 'port']:
                if paramKey in hostDict:
                    paramsDict[paramKey] = hostDict[paramKey]
            hostDict['command'] = CommandBase.discover(paramsDict['type'],
                                                       paramsDict['ip_address'],
                                                       paramsDict['username'],
                                                       paramsDict['password'])
            if re.match('controller', host['openstack']['type'], re.I):
                hostDict['auth_url'] = host['openstack']['auth_url']
                openStack = OpenStack(host['openstack']['username'],
                                      host['openstack']['password'],
                                      hostDict)
                if 'id' in host:
                    openStack.testBedId = host['id']

                self.openStacks[host['id']] = openStack
                return openStack
        # discover will discover the host and create a new host device object
        hostDevice = HostBase.discover(hostDict)
        if hostDevice:
            # test bed host environment information
            hostDevice.environmentInfo = host.get('environment_info', {})
            hostDevice.testBedId = host.get('id')
        return hostDevice

    def __createHosts(self, rawHosts):
        """Create all host objects.

        Args:
            rawHosts List - Store the raw data of the hosts, it includes the host list
        """
        # Modified 2016/09/07 h90006090
        # 1. There have not vm to create host object, we use VmomiAdapter to get vm to create there.
        # 2. when create on host object, should be add to self.hosts first, will be not return any thing.
        errorMsg = []
        for host in rawHosts:
            try:
                hostObj = self.__createHostObject(host)
                self.hosts[host['id']] = hostObj
            except Exception:
                self.hostInitError += 1
                errorMsg.append(traceback.format_exc())
                self.logger.error("Create host[%s] error. detail:%s" % (host['id'], traceback.format_exc()))
        return errorMsg

    def __createSwitches(self, rawSwitches):
        """Create all host objects.

        Args:
            rawSwitches List - Store the raw data of the switches, it includes the switch list
        """
        errorMsg = []
        for switch in rawSwitches:
            if switch['type'] == 'Pcie':
                continue
            try:
                switchObj = self.__createSwitchObject(switch)
                self.switches[switch['id']] = switchObj
            except Exception:
                self.switcheInitError += 1
                errorMsg.append(traceback.format_exc())
                self.logger.error("Create switch[%s] error. detail:%s" % (switch['id'], traceback.format_exc()))
        return errorMsg

    def __createSwitchObject(self, switch):
        """Create a host object
        - Get configuration data for a single switch from __createSwitchDevices() and create a single switch object.

        Args:
        Switch (dict): Configuration data for a single host.

        Returns:
        switchObject (instance): A single switch object.

        Raises:
        DictKeyException: The key is missing in a single host configuration data.
        """
        template = {"id" : {"types": str, "optional": False},
                    "communication" : {"types": dict, "optional": False},
                    "type" : {"types": str, "optional": False},
                    "model" : {"types": str, "optional": False},
                    "ports" : {"types": (dict, str), "optional": True},
                    "array_id" : {"types": str, "optional": True}}
        switch = validateDict(switch, template)
        switchDict = {'model': switch['type'],
                      'manufacturer': switch['model'],
                      'username': switch['communication']['username'],
                      'password': switch['communication']['password'],
                      'device_id': switch['id']}
        if 'ports' in switch and isinstance(switch['ports'], dict):
            switchDict['ports'] = switch['ports']['port']
        for item in switch['communication'].keys():
            switchDict[item] = switch['communication'][item]
        return SwitchBase.discover(switchDict)

    def _createSvpMaster(self, svp):
        """Create an SVP host object for a single storage device

        Args:
        unifiedDeviceRawData (dict): The raw data that a single storage device reads from the test bed file.

        Returns:
        svpMasterObject (dict): svp object dictionary, key is the id of svp configured in the test bed, and value is the svp object corresponding to id.

        Raises:
        DictKeyException: "communication" is not configured in "svp" in the test bed file.
        """
        master = {}
        if svp.get('communication', {}).get('master_svp_user'):
            master.update({'super_username': 'svp_user', 'super_password': svp['communication']['master_svp_user']})
        if svp.get('communication', {}).get('master_root'):
            master.update({'username': 'root', 'password': svp['communication']['master_root'], 'ipv4_address': svp['communication']['ipv4_address']})
        if svp.get('communication', {}).get('master_port'):
            master.update({'port': svp['communication']['master_port']})
        master['type'] = 'standssh'
        master['detail'] = svp
        return SvpMaster.discover(master)

    def _createSvpIpmi(self, svp):
        """Create an SVP Ipmi host object for a single storage device

        Args:
            unifiedDeviceRawData (dict): The raw data that a single storage device reads from the test bed file.

        Returns:
            svpIpmiObject (dict): svp object dictionary, key is the id of svp configured in the test bed, and value is the svp object corresponding to id.

        Raises:
            DictKeyException: "communication" is not configured in "svp" in the test bed file.
        """
        master = {}
        if svp.get('communication', {}).get('ipmi_username'):
            master.update({'username': svp['communication']['ipmi_username'],
                           'password': svp['communication']['ipmi_password'],
                           'ipv4_address': svp['communication']['ipmi_ip']})
        master['type'] = 'svpipmissh'
        master['detail'] = svp
        return SvpIpmi.discover(master)

    def __createSvpObject(self, svp):
        """Create an SVP object for a single storage device
        - Used to create svp objects when svp is configured in the test bed.

        Args:
            unifiedDeviceRawData (dict): The raw data that a single storage device reads from the test bed file.

        Returns:
            svpObject (dict): svp object dictionary, key is the id of svp configured in the test bed, and value is the svp object corresponding to id.

        Raises:
            DictKeyException: "communication" is not configured in "svp" in the test bed file.
        """
        template = {"id" : {"types": str, "optional": True},
                    "communication" : {"types": dict, "optional": True},
                    "detail" : {"types": dict, "optional": True},
                    "monitor" : {"types": dict, "optional": True},
                    "management" : {'types': dict, "optional": True}}
        svp = validateDict(svp, template)

        svpDict = {}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address',
                         'port', 'type', 'ssh_private_key', 'ssh_public_key', 'linux_root']:
            if 'communication' in svp and paramKey in svp['communication']:
                svpDict[paramKey] = svp['communication'][paramKey]
        if 'communication' in svp and 'linux_root' in svp['communication']:
            svpDict['debug_username'] = 'root'
            svpDict['debug_password'] = svp['communication']['linux_root']
        if 'detail' in svp and 'os' in svp['detail']:
            svpDict['os'] = svp['detail']['os']
        if 'monitor' in svp:
            svpDict['monitor_processes'] = []
            if 'process' in svp['monitor'] and type(svp['monitor']['process']) == 'dict':
                svpDict['monitor_processes'].append(svp['monitor']['process']['name'])
            elif 'process' in svp['monitor']:
                for process in svp['monitor']['process']:
                    if 'name' in process:
                        svpDict['monitor_processes'].append(process['name'])
        return Svp.discover(svpDict)

    def __createControllerObject(self, controller, svp=None):
        """Create a UnifiedDevice Controller object
        - Used to create controller objects configured in the test bed.

        Args:
            unifiedDeviceRawData (dict): The raw data that a single storage device reads from the test bed file.

        Returns:
            controllerObjDict (dict): Controller object dictionary, key is the name of the controller in the test bed, value is the controller object corresponding to name.

        Raises:
            DictKeyException: The controller data configuration error in the test bed file.
        """
        template = {"name" : {"types": str, "optional": True},
                    "communication" : {"types": dict, "optional": True},
                    "management" : {"types": dict, "optional": True},
                    "host" : {"types": dict, "optional": True},}
        controller = validateDict(controller, template)
        controllerDict ={}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address',
                         'max_session', 'port', 'type', 'ssh_private_key',
                         'ssh_public_key', 'debug_username', 'debug_password']:
            if 'communication' in controller and paramKey in controller['communication']:
                controllerDict[paramKey] = controller['communication'][paramKey]
        if svp:
            controllerDict['svp'] = svp['communication']
        return OceanStor.discover(controllerDict)

    def __createIpenclosureObject(self, ipenclosure):
        """Create a UnifiedDevice Controller object
        - Used to create controller objects configured in the test bed.

        Args:
            unifiedDeviceRawData (dict): The raw data that a single storage device reads from the test bed file.

        Returns:
            controllerObjDict (dict): Controller object dictionary, key is the name of the controller in the test bed, value is the controller object corresponding to name.

        Raises:
            DictKeyException: The controller data configuration error in the test bed file.
        """
        template = {"name" : {"types": str, "optional": True},
                    "communication" : {"types": dict, "optional": True}}
        ipenclosure = validateDict(ipenclosure, template)
        ipenclosureDict ={}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address',
                         'max_session', "heartbeatIp", 'port', 'type',
                         'ssh_private_key', 'ssh_public_key', 'debug_username',
                         'debug_password']:
            if 'communication' in ipenclosure and paramKey in ipenclosure['communication']:
                ipenclosureDict[paramKey] = ipenclosure['communication'][paramKey]
        return IPenclosure.discover(ipenclosureDict)

    def __simuenclosureObject(self, simuenclosure):
        """Create a UnifiedDevice Controller object
        - Used to create controller objects configured in the test bed.

        Args:
            unifiedDeviceRawData (dict): The raw data that a single storage device reads from the test bed file.

        Returns:
            controllerObjDict (dict): Controller object dictionary, key is the name of the controller in the test bed, value is the controller object corresponding to name.

        Raises:
            DictKeyException: The controller data configuration error in the test bed file.
        """
        template = {"name" : {"types": str, "optional": True}, "communication" : {"types": dict, "optional": True}}
        simuenclosure = validateDict(simuenclosure, template)
        simuenclosureDict ={}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address','max_session', 'port',
                         'type', 'ssh_private_key', 'ssh_public_key', 'debug_username', 'debug_password']:
            if 'communication' in simuenclosure and paramKey in simuenclosure['communication']:
                simuenclosureDict[paramKey] = simuenclosure['communication'][paramKey]
        return Simuenclosure.discover(simuenclosureDict)

    def __createDockerControllerObject(self, controller, svp=None):
        """Create a DockerUnifiedDevice Controller object
        - Used to create controller objects configured in the test bed.

        Args:
            unifiedDeviceRawData (dict): The raw data that a single storage device reads from the test bed file.

        Returns:
            dockercontrollerObjDict (dict): Controller object dictionary, key is the name of the controller configured in the test bed, value is the controller object corresponding to name.

        Raises:
            DictKeyException: The controller data configuration error in the test bed file.
        """
        template = {"name" : {"types": str, "optional": True},
                    "communication" : {"types": dict, "optional": True},
                    "management" : {"types": dict, "optional": True},
                    "host" : {"types": dict, "optional": True},}
        controller = validateDict(controller, template)
        controllerDict ={}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address','max_session', 'port',
                         'type', 'ssh_private_key', 'ssh_public_key', 'debug_username', 'debug_password']:
            if 'communication' in controller and paramKey in controller['communication']:
                controllerDict[paramKey] = controller['communication'][paramKey]
        if svp:
            controllerDict['svp'] = svp['communication']
        return DockerControllerHost.discover(controllerDict)

    def __wrapperHostInit(self, wrapperParams):
        """The host object of the wrapper configuration in the test bed is initialized.
        - Get the host object through the host defined in management, used for the initialization association of the host in the wrapper.

        Args:
            wrapperParams (dict): The processed wrapper parameter dictionary in each controller. The key-value pairs are described as follows:
            Tools (list): toolWrapper configuration list.
            Host (dict): Host id information. The key is "id" and the value is the specific value of "id". For example: {"id": "1"}.
            Device (str): device type information, the default is unified.

        Returns:
            hostObj (instance): host object.

        Raises:
            ValueException: Multiple default hosts are configured in the test bed.
        """
        hostObj = None
        if "host" in wrapperParams and wrapperParams["host"]:
            if not isinstance(wrapperParams["host"], dict):
                raise ValueException("TestBed Some Device 'management' has more than one default host. ")

        if "id" in wrapperParams["host"] and wrapperParams["host"]["id"]:
            for hostId in self.hosts:
                if wrapperParams["host"]["id"] == hostId:
                    hostObj = self.hosts[hostId]
                    break

        if "controller" in wrapperParams["host"] and wrapperParams["host"]["controller"]:
            for controllerName in self.controllers:
                if wrapperParams["host"]["controller"] == controllerName:
                    hostObj = self.controllers[controllerName]
                    break

        if "svp" in wrapperParams["host"] and wrapperParams["host"]["svp"]:
            for svpId in self.svps:
                if wrapperParams["host"]["svp"] == svpId:
                    hostObj = self.svps[svpId]
                    break

        # nas node
        if 'node' in wrapperParams and wrapperParams['node']:
            if not isinstance(wrapperParams["node"], dict):
                raise ValueException("TestBed Some Device 'management' has more than one default host. ")

        if "id" in wrapperParams["node"] and wrapperParams["node"]["id"]:
            for nodeId in self.__nasNodes:
                if wrapperParams["node"]["id"] == nodeId:
                    hostObj = self.__nasNodes[nodeId]
                    break

        # Region's fusionStorageNode registration wrapper
        if 'fusionstorage_node' in wrapperParams and wrapperParams['fusionstorage_node']:
            if not isinstance(wrapperParams["fusionstorage_node"], dict):
                raise ValueException("TestBed Some Device 'management' has more than one default host. ")

        if "id" in wrapperParams["fusionstorage_node"] and wrapperParams["fusionstorage_node"]["id"]:
            for nodeId in self.__rocNodes:
                if wrapperParams["fusionstorage_node"]["id"] == nodeId:
                    hostObj = self.__rocNodes[nodeId]
                    break

        # Dware dswareNode registration wrapper
        if 'dsware_node' in wrapperParams and wrapperParams['dsware_node']:
            if not isinstance(wrapperParams["dsware_node"], dict):
                raise ValueException("TestBed Some Device 'management' has more than one default host. ")

        if "id" in wrapperParams["dsware_node"] and wrapperParams["dsware_node"]["id"]:
            for nodeId in self.__dswareNodes:
                if wrapperParams["dsware_node"]["id"] == nodeId:
                    hostObj = self.__dswareNodes[nodeId]
                    break

        # Roc's rocNode registration wrapper
        if wrapperParams.get('roc_node'):
            if not isinstance(wrapperParams["roc_node"], dict):
                raise ValueException("TestBed Some Device 'management' has more than one default host. ")

        if "id" in wrapperParams["roc_node"] and wrapperParams["roc_node"]["id"]:
            for nodeId in self.__rocNodes:
                if wrapperParams["roc_node"]["id"] == nodeId:
                    hostObj = self.__rocNodes[nodeId]
                    break

        return hostObj

    def __createWrapperObject(self, wrapperParams, tool, deviceType=None):
        """Create a single wrapper object.
        - Create a single wrapper object.

        Args:
            wrapperParams (dict): The processed wrapper parameter dictionary in each controller. The key-value pairs are described as follows:
            Tools (list): toolWrapper configuration list.
            Host (dict): Host id information. The key is "id" and the value is the specific value of "id". For example: {"id": "1"}.
            Device (str): device type information, the default is unified.
            Tool (dict): The configuration data of a single tool in wrapperParams, the key value pairs are as follows:
            Controller|host|svp (str): wrapper device, which can be controller, host, and svp. The value is a unique identifier. Optional.
            Priority (str): wrapper priority.
            Type (str): wrapper type.

        Eg:
            {'controller': 'B',
            'priority': '1',
            'type': 'adminCli'}

        Returns:
            wrapperObject (instance): wrapper object.
        """
        wrapper = {}
        for key in ["username", "password", "port", "timeout", "ip_address", "default_browser_type",
                    "guest_username", "guest_password"]:
            if key in tool:
                wrapper[key] = tool[key]

        # Wrapper object initialization.
        #Get version information
        version = ''
        productModel = ''
        patchVersion = ''

        # create unified used
        if self.controllers:
            for key in self.controllers:
                controllerObj = self.controllers[key]
                version = controllerObj.getRunningVersion()
                patchVersion = controllerObj.getPatchVersion()
                productModel = controllerObj.getRunningModel()
                break
        elif self.svps:
            for key in self.svps:
                version = self.svps[key].softVersion
                productModel = self.svps[key].productModel
                break

        if version == "V300R005C00":
            Resource.WRAPPERS = V300R005C00WRAPPERS

        elif version == "V200R002C30":
            Resource.WRAPPERS = V200R002C30WRAPPERS

        elif (version == "V300R001C20" or version == "V300R001C21" or version == "V300R001C30") and
            ('Dorado' in productModel):
            Resource.WRAPPERS = DORADOV300R001C20WRAPPERS

        elif version == "V300R003C10":
            Resource.WRAPPERS = V300R003C10WRAPPERS

        elif version == "V300R006C00" or version == "V300R006C00SPC100":
            Resource.WRAPPERS = V300R006C00WRAPPERS
        # 2018-03-29 wwx271515 Adapted to the new version V500R007C20 (V300R006C21) inherits V500R007C10 (V300R006C20)
        # 2018-06-14 wwx271515 Added V300R006C30, inherited V300R006C21
        # 2018-08-07 wwx271515 Added V300R006C50&V500R007C30, inherited V300R006C21
        elif "V500R007C00" in version or 'V300R006C10' in version or
            'V500R007C10' in version or 'V300R006C20' in version or 'V300R006C21' in version:
            """添加V500R007C00基础版本加载，继承V3R6C00"""
            Resource.WRAPPERS = V500R007C00WRAPPERS

        elif "V500R007C20" in version or 'V300R006C30' in version:
            Resource.WRAPPERS = V500R007C20WRAPPERS

        elif ('V300R006C50' in version or 'V500R007C30' in version or
              'V500R007C50' in version or 'V300R006C60' in version or
              'V500R008C00' in version or 'V500R007C60' in version) and 'Dorado NAS' not in productModel:
            Resource.WRAPPERS = V500R007C30WRAPPERS

        elif ('V300R006C50' in version or 'V500R007C30' in version or 'V300R002C10' in version) and 'Dorado NAS' in productModel:
            Resource.WRAPPERS = V500R007C30CommonNasWRAPPERS

        elif version == "V300R003C20":
            Resource.WRAPPERS = V300R003C20WRAPPERS
            if patchVersion == "SPC200" or patchVersion == 'SPC100':
                Resource.WRAPPERS = V300R003C20SPC200WRAPPERS

        elif version == "V300R003C00":
            Resource.WRAPPERS = V300R003C00WRAPPERS

        elif "V300R001C00" in version and (productModel == "Dorado6000 V3" or productModel == "Dorado5000 V3"):
            Resource.WRAPPERS = DORADOV300R001C00WRAPPERS

        elif "V300R001C01" in version and (productModel == "Dorado6000 V3" or productModel == "Dorado5000 V3"):
            Resource.WRAPPERS = DORADOV300R001C01WRAPPERS

        elif 'V300R001' in version and 'Dorado' not in productModel:
            Resource.WRAPPERS = V300R001WRAPPERS

        elif 'V300R002C10' in version and 'Dorado' not in productModel:
            Resource.WRAPPERS = V300R002C10WRAPPERS

        elif ('V300R002C10' in version or 'V300R002C20' in version) and 'Dorado' in productModel and "NAS" not in productModel:
            Resource.WRAPPERS = DORADOV300R002C10WRAPPERS

        elif 'V300R002' in version and 'Dorado' not in productModel:
            Resource.WRAPPERS = V300R002C00WRAPPERS

        elif version == 'V300R002C00' and 'Dorado' in productModel:
            Resource.WRAPPERS = V300R002C00WRAPPERS

        elif version == 'V100R001C00' and 'Dorado' in productModel:
            Resource.WRAPPERS = V100R001C00WRAPPERS

        elif ("6.0." in version)and ('Dorado' in productModel or "D" in productModel):
            Resource.WRAPPERS = V600R003C00WRAPPERS

        elif version == "V100R001C30" or version == "V200R002C30":
            Resource.WRAPPERS = V200R002C30WRAPPERS

        elif deviceType and deviceType == 'nas':
            Resource.WRAPPERS = N9000WRAPPERS

        elif deviceType and deviceType == 'region':
            Resource.WRAPPERS = REGIONWRAPPERS

        elif deviceType and deviceType == 'dsware':
            Resource.WRAPPERS = DSWAREWRAPPERS

        elif deviceType and deviceType == 'roc':
            Resource.WRAPPERS = ROCWRAPPERS

        if "type" in tool and tool["type"] in Resource.WRAPPERS and wrapperParams["device"] in Resource.WRAPPERS[tool["type"]]:
            wrapperModule = Resource.WRAPPERS[tool["type"]][wrapperParams["device"]]
            wrapperClass = Resource.WRAPPERS[tool["type"]]["class"]

            # Add the host username/password for the testcomplete wrapper
            if re.match(r'testcomplete', wrapperModule, re.IGNORECASE) and "host" in tool:
                for key in self.hosts:
                    if tool["host"] == key and self.hosts[key].username and self.hosts[key].password:
                        wrapper["host_username"] = self.hosts[key].username
                        wrapper["host_password"] = self.hosts[key].password
                    else:
                        self.logger.error("Username/password not defined for Host Id: %s" % tool["host"]["id"])
            __import__(wrapperModule)
            return getattr(sys.modules[wrapperModule], wrapperClass)(wrapper)
        else:
            raise ValueException("%s Does not exist for %s" % (tool["type"], wrapperParams["device"]))

    def __createToolSingleWrapper(self, wrapperParams, deviceType=None):
        """Create a list of tool Wrapper objects for a single controller configuration

        Args:
            wrapperParams (dict): The processed wrapper parameter dictionary in each controller. The key-value pairs are described as follows:
            Tools (list): toolWrapper configuration list.
            Host (dict): Host id information. The key is "id" and the value is the specific value of "id". For example: {"id": "1"}.
            Device (str): device type information, the default is unified.

        Returns:
            wrapperObjList (list): wrapper object information list, a single list element is a dictionary of wrapper information, the key value pairs are as follows:
            Host (instance): The device object that the wrapper sends the command to.
            Type (str): The type of wrapper.
            Wrapper (instance): wrapper object.

        Raises:
            ValueException: Thrown when the device that issued the wrapper command was not configured.
        """
        # Get the list of controller objects for this unified storage.
        wrapperObjList = []

        # Priority judgment.
        if "tools" in wrapperParams and isinstance(wrapperParams["tools"], list) and len(wrapperParams["tools"]) > 1:
            hasPriorityFlag = True
            for child in wrapperParams["tools"]:
                if "priority" not in child:
                    hasPriorityFlag = False
                    break
            if hasPriorityFlag is False:
                self.logger.warn("Warning! You defined some wrappers with priority and some without!")

        # Rest type wrapper type processing.
        reworked = []
        if "tools" in wrapperParams and isinstance(wrapperParams["tools"], list):
            for tool in wrapperParams["tools"]:
                # rest define, unified
                if tool["type"] == "rest":
                    if wrapperParams["device"] == "unified":
                        tool["type"] = 'restOceanStor'
                if tool['type'] == 'rest':
                    if wrapperParams['device'] == 'nas':
                        tool['type'] = 'restNas'
                reworked.append(tool)
            wrapperParams["tools"] = reworked

        # Loop processing
        for tool in wrapperParams["tools"]:
            twDict = {"host": self.__wrapperHostInit(wrapperParams),
                      "wrapper": self.__createWrapperObject(wrapperParams, tool, deviceType),
                      "type": tool["type"]}

            # If the host is configured with the host reset host object, an exception is thrown if it does not exist.
            if "host" in tool:
                if tool["host"] in self.hosts:
                    twDict["host"] = self.hosts[tool["host"]]
                else:
                    raise ValueException("Invalid host %s specified for %s management tool."% (tool["host"], tool["type"]))
            # unified controller
            elif "controller" in tool:
                twDict["host"] = self.controllers[tool["controller"]]
            # unified svp
            elif "svp" in tool:
                twDict["host"] = self.svps[tool["svp"]]
            # OceanStor Nas cluster Node
            elif 'node' in tool:
                twDict['host'] = self.__nasNodes[tool['node']]

            # If the initial value is None and the host is not configured in the tool, there is no host and an exception is thrown.
            if twDict["host"] is None:
                if re.match(r'^(UniAutos.Wrapper.Api)', twDict[tool["type"]]):
                    pass
                else:
                    raise ValueException("Management Host is not specified for %s, and the default management host is also not specified." % tool["type"])

            wrapperObjList.append(twDict)
        return wrapperObjList

    # todo: this function not used
    def __registerToolWrappersOnHostObject(self, unifiedDeviceRawData, deviceType=None):
        """Register wrapper
        - Register the created wrapper object to the host, controller, svp configured in the wrapper.

        Args:
            unifiedDeviceRawData (dict): The raw data dictionary that a single storage device is configured in the test bed.
        """
        wrapperList = self.__createToolWrapperObjects(unifiedDeviceRawData, deviceType)
        for wrapper in wrapperList:
            for twObject in wrapper:
                twObject["host"].registerToolWrapper(host=twObject["host"], wrapper=twObject["wrapper"])

    def __createToolWrapperObjects(self, controllerMgmt, deviceType):
        """Create a list of tool Wrapper objects
        - Each tool under "management" in each controller is initialized with a Wrapper object, and is initialized to be associated with the corresponding device to be used to issue a list of objects.

        Args:
            deviceType (str): need create wrapper's device type, eg: 'unified', 'nas'.
            unifiedDeviceRawData (dict): raw data dictionary configured by a single storage device in the test bed
            Returns:
            wrapperObjects (list): list of wrapper objects.
        """
        wrapperParams = self.__setToolWrapperParams(controllerMgmt, deviceType)
        return self.__createToolSingleWrapper(wrapperParams, deviceType)

    def __createIPenclosureWrapperObjects(self, ipenclosureName):
        wrapperObjList = []
        twDict = {}
        twDict["host"] = self.ipenclosures[ipenclosureName]
        wrapperModule = "UniAutos.Wrapper.Tool.CliLite.CliLite"
        wrapperClass = "CliLite"
        __import__(wrapperModule)
        twDict["wrapper"] = getattr(sys.modules[wrapperModule], wrapperClass)({})
        twDict["type"] = "cliLite"
        wrapperObjList.append(twDict)
        return wrapperObjList

    def __setToolWrapperParams(self, params, deviceType="unified"):
        """Get the wrapper configuration in a single controller and convert it to an available Wrapper parameter

        Args:
            Params (dict): The original configuration data dictionary for the Wrapper in the test bed.
            deviceType (str) : The default value is "unified", the device type corresponding to the wrapper, if nas cluster, deviceType is 'nas'.

        Returns:
            wrapperParams (dict): The processed wrapper parameter dictionary, the key-value pairs are described as follows:
            Tools (list): toolWrapper configuration list.
            Host (dict): Host id information. The key is "id" and the value is the specific value of "id". For example: {"id": "1"}.
            Device (str): device type information, the default is unified.
        """
        # Initialize the wrapper parameter to an empty dictionary.
        wrapperParams = {}
        if "tools" not in params:
            raise InvalidParamException("__setToolWrapperParams Failed, Please check test bed tool wrapper configuration.")
        if "tool" not in params["tools"]:
            raise InvalidParamException("__setToolWrapperParams Failed, Please check test bed tool wrapper configuration.")

        tmpToolWrapperParams = self.__changeParamToList(params["tools"]["tool"])
        allHavePri = True
        for child in tmpToolWrapperParams:
            if "priority" not in child:
                allHavePri = False
                break
        if allHavePri:
            wrapperParams["tools"] = sorted(tmpToolWrapperParams, key=lambda seq: seq["priority"])
        else:
            wrapperParams["tools"] = tmpToolWrapperParams

        # Host in param, configure host
        if "host" in params:
            wrapperParams["host"] = params["host"]
        elif 'node' in params:
            wrapperParams['node'] = params['node']
        elif 'fusionstorage_node' in params:
            wrapperParams['fusionstorage_node'] = params['fusionstorage_node']
        elif 'dsware_node' in params:
            wrapperParams['dsware_node'] = params['dsware_node']
        elif 'roc_node' in params:
            wrapperParams['roc_node'] = params['roc_node']

        # Device defaults to unified
        wrapperParams["device"] = deviceType
        return wrapperParams

    def __linkHostObjToUnifiedDevice(self, unifiedDeviceRawData):
        """Obtain the object list of the host configured in the UnifiedDevice configuration item in the configuration file.

        Used to associate the host with the storage device after obtaining the list.

        Used to associate the host with the storage device after obtaining the list

        Args:
            unifiedDeviceRawData (dict): The raw data dictionary that a single storage device is configured in the test bed.

        Returns:
            unifiedHostObjList (list): list of host objects.
        """
        unifiedHostObjList = []
        unifiedHostsInfo = XmlToDict.getSpecificKeyRawData(unifiedDeviceRawData, "hosts")
        if not self.hosts:
            return unifiedHostObjList

        if not unifiedHostsInfo:
            return unifiedHostObjList

        tmpHostsInfo = self.__changeParamToList(unifiedHostsInfo["host"])
        for tmpHost in tmpHostsInfo:
            hostInfo = {}
            if tmpHost["id"] in self.hosts:
                hostInfo[tmpHost["id"]] = self.hosts[tmpHost["id"]]
                hostInfo['host'] = self.hosts[tmpHost["id"]]
                hostInfo["type"] = tmpHost["type"]
                # Support host configuration arbitrary attributes.
                # tmpHost.pop('id')
                hostInfo.update(tmpHost)
                unifiedHostObjList.append(hostInfo)
        return unifiedHostObjList

    @staticmethod
    def __changeParamToList(param):
        """Only used for parsed xml data conversion, xml parsed data, if there is a dictionary, there is only one data in the dictionary.

        Args:
            Param (list|dict): The raw data of the dict parsed by the test beb configuration file.

        Returns:
            Param (list): list returns directly, dict is converted to list return.

        Raises:
            InvalidParamException: The argument passed in is not a dict or list.
        """
        if isinstance(param, list):
            return param
        if isinstance(param, dict): # The data structure design based on the data returned by the xml parsing module is only applicable to the parsed data of the XmlToDict module.
            return [param]
        else:
            raise InvalidParamException("Create resource failed, Please check test beb config file.")

    def __createUnifiedDeviceObject(self, unified):
        """Create a single UnifiedDevice object

        Args:
            unifiedDeviceRawData (dict): The raw data dictionary that a single storage device is configured in the test bed.

        Returns:
            unifiedObj (instance): A single storage object.
        """
        # Create the controller object and svp object of the storage device for registration of the wrapper object.
        svpConf = None
        svpObj = None
        svpMaster = None
        svpIpmi = None
        if 'svp' in unified and unified['svp']:
            svpObj = self.__createSvpObject(unified['svp']) # There is only one svp object for an array.
            self.svps[unified['svp']['id']] = svpObj
            svpConf = unified['svp']
            if 'management' in unified['svp'] and unified['svp']['management']:
                wrapperObjs = self.__createToolWrapperObjects(unified['svp']['management'], deviceType='unified')
                for key in self.svps:
                    from UniAutos.Wrapper.Template.CLI import CliWrapper
                        for wrapper in wrapperObjs:
                            self.svps[key].registerToolWrapper(host=wrapper["host"], wrapper=wrapper["wrapper"])
                # Import a new Wrapper
                wrapper = CliWrapper(productModel=self.svps[key].productModel,
                                     version=self.svps[key].softVersion,
                                     patchVersion=self.svps[key].patchVersion)
            self.svps[key].registerToolWrapper(host=self.svps[key], wrapper=wrapper)
            svpMaster = self._createSvpMaster(unified['svp'])
            svpIpmi = self._createSvpIpmi(unified['svp'])

        if 'controller' in unified and unified['controller']:
            rawControllers = self.__changeParamToList(unified['controller'])
            for controller in rawControllers:
                self.controllers[controller['name']] = self.__createControllerObject(controller)

                wrapperObjs = []
                if 'management' in controller and controller['management']:
                    wrapperObjs = self.__createToolWrapperObjects(controller['management'], deviceType='unified')

                for wrapper in wrapperObjs:
                    self.controllers[controller['name']].registerToolWrapper(host=wrapper["host"],
                                                                             wrapper=wrapper["wrapper"])

        #Generate ip box object (host object)
        if "ipenclosure" in unified and unified['ipenclosure']:
            #Determine whether the current device is a disk frame. If the frame ip is the same as the controller, it is a disk frame.
            flag = False
            ipenclosure = unified['ipenclosure'][0]
            for controller in unified['controller']:
                if controller['communication']['ipv4_address'] == ipenclosure['communication']['ipv4_address']:
                    flag = True
                    break

            rawIpenclosure = self.__changeParamToList(unified['ipenclosure'])
            for ipenclosure in rawIpenclosure:
                if flag:
                    #Ip box adapter disk control integrated environment modify the login connection to storSSH, mark the current object as a disk frame integrated environment
                    ipenclosure['communication']['type'] = 'storSSH'
                    ipenclosure['communication']['isTogether'] = True
                    self.ipenclosures[ipenclosure['name']] = self.__createIpenclosureObject(ipenclosure)
                else:
                    self.ipenclosures[ipenclosure['name']] = self.__createIpenclosureObject(ipenclosure)
                #Register wrapper
                wrapperObjs = []
                wrapperObjs = self.__createIPenclosureWrapperObjects(ipenclosureName=ipenclosure['name'])
                for wrapper in wrapperObjs:
                    self.ipenclosures[ipenclosure['name']].registerToolWrapper(host=wrapper["host"],
                                                                               wrapper=wrapper["wrapper"])

        #Generate simulation box object
        if "simuenclosure" in unified and unified['simuenclosure']:
            rawSimuenclosure = self.__changeParamToList(unified['simuenclosure'])
            for simuenclosure in rawSimuenclosure:
                self.simuenclosures[simuenclosure['name']] = self.__simuenclosureObject(simuenclosure)

        unifiedObjInfo = {"hosts" : self.__linkHostObjToUnifiedDevice(unified),
                          "resource" : self,
                          "raw_resource_data" : unified,
                          "svp" : svpObj,
                          "controller" : self.controllers,
                          "ipenclosure" : self.ipenclosures,
                          "simuenclosure" : self.simuenclosures,
                          "device_type" : "unified",
                          "svp_master" : svpMaster,
                          "svp_ipmi" : svpIpmi}

        if "ipenclosure" in unified:
            unifiedObjInfo["ipenclosure_info"] = unified["ipenclosure"]

        if "environment_info" in unified:
            unifiedObjInfo["environment_info"] = unified["environment_info"]

        if "communication" in unified and "ipv4_address" in unified["communication"]:
            unifiedObjInfo["ipv4_address"] = unified["communication"]["ipv4_address"]

        if "communication" in unified and "ipv6_address" in unified["communication"]:
            unifiedObjInfo["ipv6_address"] = unified["communication"]["ipv6_address"]

        if "communication" in unified and "password" in unified["communication"]:
            unifiedObjInfo["password"] = unified["communication"]["password"]

        if "communication" in unified and "username" in unified["communication"]:
            unifiedObjInfo["username"] = unified["communication"]["username"]

        if "id" in unified and unified["id"]:
            unifiedObjInfo["device_id"] = unified["id"]

        if "links" in unified and unified["links"]:
            unifiedObjInfo['links'] = unified["links"]

        unifiedObj = Unified(**unifiedObjInfo)
        self.controllers = {} # The controller object is a process variable, which should be cleared after initialization, otherwise it will affect the subsequent configuration.。
        self.ipenclosures = {} # The ip box object is a process variable. It should be cleared after initialization. Otherwise, it will affect the subsequent configuration.
        self.svps = {} # The svps object is a process variable. It should be cleared after initialization, otherwise it will affect the subsequent configuration.。
        self.simuenclosures = {} # The simulation box object is a process variable, which should be cleared after initialization, otherwise it will affect the subsequent configuration.
        return unifiedObj

    def __createDockerUnifiedDeviceObject(self, unified):
        """Create a single DockerUnifiedDevice object

        Args:
            unifiedDeviceRawData (dict): The raw data dictionary that a single storage device is configured in the test bed.

        Returns:
            dockerunifiedObj (instance): A single storage object.
        """
        # Create the controller object and svp object of the storage device for registration of the wrapper object.
        svpConf = None
        svpObj = None
        svpMaster = None
        svpIpmi = None

        if 'controller' in unified and unified['controller']:
            rawControllers = self.__changeParamToList(unified['controller'])
            for controller in rawControllers:
                self.controllers[controller['name']] = self.__createDockerControllerObject(controller)

                wrapperObjs = []
                if 'management' in controller and controller['management']:
                    wrapperObjs = self.__createToolWrapperObjects(controller['management'], deviceType='unified')

                for wrapper in wrapperObjs:
                    self.controllers[controller['name']].registerToolWrapper(host=wrapper["host"],
                                                                             wrapper=wrapper["wrapper"])

        #生成仿真框对象
        if "simuenclosure" in unified and unified['simuenclosure']:
            rawSimuenclosure = self.__changeParamToList(unified['simuenclosure'])
            for simuenclosure in rawSimuenclosure:
                self.simuenclosures[unified['simuenclosure']['name']] = self.__simuenclosureObject(simuenclosure)

        unifiedObjInfo = {"hosts" : self.__linkHostObjToUnifiedDevice(unified),
                          "resource" : self,
                          "raw_resource_data" : unified,
                          "svp" : svpObj,
                          "controller" : self.controllers,
                          "simuenclosure" : self.simuenclosures,
                          "device_type" : "unified",
                          "svp_master" : svpMaster,
                          "svp_ipmi" : svpIpmi}

        if "environment_info" in unified:
            unifiedObjInfo["environment_info"] = unified["environment_info"]

        if "communication" in unified and "ipv4_address" in unified["communication"]:
            unifiedObjInfo["ipv4_address"] = unified["communication"]["ipv4_address"]

        if "communication" in unified and "ipv6_address" in unified["communication"]:
            unifiedObjInfo["ipv6_address"] = unified["communication"]["ipv6_address"]

        if "communication" in unified and "password" in unified["communication"]:
            unifiedObjInfo["password"] = unified["communication"]["password"]

        if "communication" in unified and "username" in unified["communication"]:
            unifiedObjInfo["username"] = unified["communication"]["username"]

        if "id" in unified and unified["id"]:
            unifiedObjInfo["device_id"] = unified["id"]

        if "links" in unified and unified["links"]:
            unifiedObjInfo['links'] = unified["links"]

        dockerUnifiedObj = DockerUnified(**unifiedObjInfo)
        self.dockerControllers = {} # 控制器对象为过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
        self.simuenclosures = {} # 仿真框对象为过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
        self.svps = {} # svps对象为过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
        return dockerUnifiedObj

    def __createUnifiedDevices(self, unifiedRawData, supportAbnormalController):
        """Create all UnifiedDevice objects
        - Get all the storage device configuration raw data configured in the test bed, and create all storage devices as UnifiedDevice objects.

        Args:
        unifiedRawData (Dict)

        Returns:
        unifiedDevicesObject (dict): The key of the dictionary is the ID of unifiedDevice, and the value is the dictionary of the unifiedDevice object.
        """
        # Modified 2016/09/07 h90006090
        # 1. when create on unified object, should be add to self.unifiedDevices first, will be not return any thing.
        errorMsg = []
        for unified in unifiedRawData:
            try:
                unifiedObj = self.__createUnifiedDeviceObject(unified)
                self.unifiedDevices[unified['id']] = unifiedObj
            except Exception as e:
                self.unifiedInitError += 1
                # The simulation environment is only allowed to wait once during the initialization process.
                if isinstance(unified.get("controller"), dict):
                    if unified.get("controller").get("communication", {}).get("type", "").lower() == "emustorssh"
                        and "DoradoV6R3C00 or Simulation system is error" in e.message:
                        raise Exception(e.message)
                if isinstance(unified.get("controller"), list):
                    if unified.get("controller")[0].get("communication", {}).get("type", "").lower() == "emustorssh"
                        and "DoradoV6R3C00 or Simulation system is error" in e.message:
                        raise Exception(e.message)
                errorMsg.append(traceback.format_exc())
                self.logger.error("Create unified[%s] error. detail:%s" % (unified['id'], traceback.format_exc()))
        return errorMsg

    def __createDockerUnifiedDevices(self, unifiedRawData, supportAbnormalController):
        """Create all DockerUnifiedDevice objects
        - Get all the storage device configuration raw data configured in the test bed, and create all the storage devices for the DockerSSH protocol as DockerUnifiedDevice objects.

        Args:
        unifiedRawData (Dict)

        Returns:
        dockerunifiedDevicesObject (dict): The key of the dictionary is the ID of the dockerunifiedDevice, and the value is the dictionary of the dockerunifiedDevice object.
        """
        # Modified 2016/09/07 h90006090
        # 1. when create on unified object, should be add to self.unifiedDevices first, will be not return any thing.
        errorMsg = []
        for unified in unifiedRawData:
            try:
                dockerUnifiedObj = self.__createDockerUnifiedDeviceObject(unified)
                self.dockerUnifiedDevices[unified['id']] = dockerUnifiedObj
            except Exception:
                self.dockerUnifiedInitError += 1
                errorMsg.append(traceback.format_exc())
                self.logger.error("Create docker unified[%s] error. detail:%s" % (unified['id'], traceback.format_exc()))
        return errorMsg

    @staticmethod
    def __isHighEndDevice(unifiedDeviceRawData):
        """判断是否为高端设备
        -高端目前支持18000\18500\18800配置.

        Args:
            unifiedDeviceRawData (dict): 测试床中配置的单个存储设备原始数据.

        Returns:
            True (bool): 是高端设备.
            False (bool): 非高端设备.

        Raises:
            ValueException: 当测试床中配置"product_model" 且为18000/18500/18800时，无"svp"配置时抛出异常.
        """
        if "product_model" in unifiedDeviceRawData and unifiedDeviceRawData["product_model"]
            and re.match(r'^(18000|18500|18800)', unifiedDeviceRawData["product_model"]):
            if "svp" in unifiedDeviceRawData and unifiedDeviceRawData["svp"]:
                return True
            else:
                raise ValueException("Create Resource failed, Test bed configuration error,have not 'svp' configuration.")
        elif "svp" in unifiedDeviceRawData and unifiedDeviceRawData["svp"]:
            return True
        else:
            return False

    @validateParam(deviceType=str, deviceId=str)
    def getDevice(self, deviceType, deviceId):
        """Get the device of the specified type, id
        - Returns all hosts, switches, and array devices in the test suite configuration when no parameters are specified.

        Args:
            deviceType (str|None): device type, defaults to None, valid values ​​are "host", "switch", "fusionstorage_node", "nas_cluster", "dockerunified" and "unified".
            deviceId (str|None): Device ID, defaults to None.

        Returns:
            Device (instance): Returns a single matching device object when deviceType and deviceId are specified;

        Examples:
            dev = self.resource.getDevice(deviceType="unified",
            deviceId="1")
            output:
            >>
        """
        if deviceType == "host":
            return self.__getDeviceById(self.hosts, deviceId)
        elif deviceType == "unified":
            return self.__getDeviceById(self.unifiedDevices, deviceId)
        elif deviceType == "switch":
            return self.__getDeviceById(self.switches, deviceId)
        elif deviceType == "nas_cluster":
            return self.__getDeviceById(self.nasClusters, deviceId)
        elif deviceType == "region":
            return self.__getDeviceById(self.regions, deviceId)
        elif deviceType == "dsware":
            return self.__getDeviceById(self.dswares, deviceId)
        elif deviceType == "dockerunified":
            return self.__getDeviceById(self.dockerUnifiedDevices, deviceId)


    def getHost(self, role, platform=None):
        """Get the HOST object of the specified type or operating system

        Args:
            Role (str): host type Optional values ​​io, ldap, ad, cps, etc., io represents the host that provides business read and write.
            Platform (str|None): The operating system platform of host, the default is None.

        Returns:
            Device (list): list of host objects.

        Examples:
        1. Get all the Linux hosts
        Linux_host = case.getHost(hostRole='io', platform='linux')

        2. Get all LDAP servers
        Ldap_server = case.getHost(hostRole='ldap')
        """
        # Filter the host of the specified type, and when the hostRole is None, it indicates the host that provides service reading and writing.
        hosts = [host for host in self.getSpecifiesTypeDevices('host') if role.lower() == host.detail.get('host_role', '').lower()]
        # Filter the host of the specified operating system
        if platform:
            hosts = [host for host in hosts if platform.lower() == host.os.lower()]
        if hosts:
            return hosts

    def __getDeviceById(self, devicesDict, deviceId):
        """Get device object according to the device id

        Args:
            devicesDict (Dict) : A dict stores the device object mapped with the divice id as a key

        Returns:
            deviceobj (UniAutos.Device) : Return an UniAutos object
        """
        if devicesDict and deviceId in devicesDict:
            return devicesDict[deviceId]
        else:
            self.logger.warn('Be careful, can not find region with id: %s' % deviceId)
            return None

    def getAllDevices(self):
        """Get all the devices

        Returns:
            Devices (dict): Returns a dictionary of all device objects, the key is the type of the device, and the value is the dictionary of device ids and device objects.

        Examples:
        dev = self.resource.getAllDevices()
        output:
        >>[,
        ]
        """
        tmpDevicesList = list()
        tmpDevicesList.extend(self.getSpecifiesTypeDevices("host"))
        tmpDevicesList.extend(self.getSpecifiesTypeDevices("unified"))
        tmpDevicesList.extend(self.getSpecifiesTypeDevices("switch"))
        tmpDevicesList.extend(self.getSpecifiesTypeDevices("nas_cluster"))
        tmpDevicesList.extend(self.getSpecifiesTypeDevices("region"))
        tmpDevicesList.extend(self.getSpecifiesTypeDevices("dsware"))
        return tmpDevicesList

    @validateParam(deviceType=str)
    def getSpecifiesTypeDevices(self, deviceType):
        """Get the device of the specified type

        Args:
        deviceType (str|None): device type, defaults to None, valid values ​​are "host", "unified", 'nas_cluster', 'switch' and 'fusionstorage_node'.
        deviceId (str|None): Device ID, defaults to None.

        Returns:
        Devices (dict): Returns the device dictionary of all deviceType types, the key is the id of the device object, and the value is the device object;

        Examples:
        dev = self.resource.getSpecifiesTypeDevices(deviceType="unified")
        output:
        >>[]
        """
        if deviceType == "host" and self.hosts:
            return self.hosts.values()
        elif deviceType == "unified" and self.unifiedDevices:
            return self.unifiedDevices.values()
        elif deviceType == "switch" and self.switches:
            return self.switches.values()
        elif deviceType == "nas_cluster" and self.nasClusters:
            return self.nasClusters.values()
        elif deviceType == 'region' and self.regions:
            return self.regions.values()
        elif deviceType == 'dsware' and self.dswares:
            return self.dswares.values()

        return []

    @validateParam(deviceId=str)
    def getSpecifiesIdDevices(self, deviceId):
        """Get the device with the specified id

        Args:
            deviceId (str|None): Device ID, defaults to None.

        Returns:
            Device (dict): Returns the device dictionary with all device ids as deviceId, the key is the device type, and the value is the device object.

        Examples:
            dev = self.resource.getSpecifiesIdDevices(deviceId="1")
        output:
            >>[,]
        """
        tmpDevicesList = []
        if self.hosts:
            for hostId in self.hosts:
                if hostId == deviceId:
                    tmpDevicesList.append(self.hosts[deviceId])
                    break
        if self.unifiedDevices:
            for unifiedId in self.unifiedDevices:
                if unifiedId == deviceId:
                    tmpDevicesList.append(self.unifiedDevices[deviceId])
                    break
        if self.nasClusters:
            for nasId in self.nasClusters:
                if nasId == deviceId:
                    tmpDevicesList.append(self.nasClusters[deviceId])
                    break
        return tmpDevicesList

    def setDeviceResource(self):
        """Bind the device object created by the Resource module to the Resource.
        """
        devices = self.getAllDevices()
        for dev in devices:
            dev.setResource(self)
        return

    @staticmethod
    def __createNasNode(rawNode):
        """create single nas cluster node.

        Args:
        rawNode (dict): Tests the raw data of the nas node configured in the bed.

        Returns:
        nasNode (OceanStorNas): Nas node object.

        """
        template = {"id" : {"types": str, "optional": True},
                    "communication" : {"types": dict, "optional": True},
                    "management" : {"types": dict, "optional": True},
                    "detail" : {"types": dict, "optional": True},
                    "host" : {"types": dict, "optional": True},
                    "role" : {"types": str, "optional": True},}
        node = validateDict(rawNode, template)

        nodeDict = {}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address','max_session', 'port', 'type',
                         'ssh_private_key', 'ssh_public_key', 'debug_username', 'debug_password']:
            if 'communication' in node and paramKey in node['communication']:
                nodeDict[paramKey] = node['communication'][paramKey]

        if 'detail' in node and node['detail']:
            nodeDict['detail'] = node['detail']

        if 'id' in node and node['id']:
            nodeDict['id'] = node['id']

        if 'role' in node and node['role']:
            nodeDict['role'] = node['role']

        return OceanStorNas.discover(nodeDict)

    def __createNasClusters(self, rawNasClusters):
        """create all nas clusters configed in test bed

        Args:
        rawNasClusters (list): Data for multiple nas clusters configured in the test bed.

        Returns:
        nasClusters (dict): Tests all NasCluster objects configured in the bed, with key id and value NasLuster objects.

        """
        nasClusters = {}
        for rawNasCluster in rawNasClusters:
            nasClusterObj = self.__createNasCluster(rawNasCluster)
            nasClusters[rawNasCluster['id']] = nasClusterObj
        return nasClusters

    def __createRegions(self, rawRegions):
        """create all nas fusion storage nodes configured in test bed

        Args:

        rawRegions (list): Data that is configured by multiple Regions in the test bed.

        Returns:
        errorMsg (list): Create an error message or an empty list of the region

        """
        errorMsg = []
        for rawRegion in rawRegions:
            try:
                regsionObj = self.__createRegionObject(rawRegion)
                self.regions[rawRegion['id']] = regsionObj
            except Exception:
                self.regionInitError += 1
                errorMsg.append(traceback.format_exc())
                self.logger.error("Create region[%s] error. detail:%s" % (rawRegion['id'], traceback.format_exc()))
        return errorMsg

    def __createDswares(self, rawDswares):
        """create all nas dsware nodes configured in test bed

        Args:
        rawDswares (list): Multiple Dsware data configured in the test bed.

        Returns:
        errorMsg (list): Create an error message or an empty list of dsware

        """
        errorMsg = []
        for rawDsware in rawDswares:
            try:
                dswareObj = self.__createDswareObject(rawDsware)
                self.dswares[rawDsware['id']] = dswareObj
            except Exception:
                self.dswareInitError += 1
                errorMsg.append(traceback.format_exc())
                self.logger.error("Create dsware[%s] error. detail:%s" % (rawDsware['id'], traceback.format_exc()))
        return errorMsg

    def __createAvailableZone(self, rawAvailableZone):
        """create an available zone configured in test bed

        Args:
        rawFusionNodes (list): 单个available zone在测试床床中的配置数据

        Returns:
        availableZone (AvailableZone): AvailableZone对象.

        """
        if 'fusionstorage_node' in rawAvailableZone and rawAvailableZone['fusionstorage_node']:
            rawFusionNodes = self.__changeParamToList(rawAvailableZone['fusionstorage_node'])
            for rawFusionNode in rawFusionNodes:
                fusionNodeObj = self.__createFusionNodeObject(rawFusionNode)
                self.__rocNodes[rawFusionNode['id']] = fusionNodeObj
                wrapperObjs = []
                if 'management' in rawFusionNode and rawFusionNode['management']:
                    wrapperObjs = self.__createToolWrapperObjects(rawFusionNode['management'], deviceType='region')

                if wrapperObjs:
                    for wrapper in wrapperObjs:
                        self.__rocNodes[rawFusionNode['id']].registerToolWrapper(host=wrapper["host"],
                                                                                 wrapper=wrapper["wrapper"])
            availableZone = AvailableZone(self.__rocNodes)
            # 过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
            self.__rocNodes = {}

            # 加入az的environment
            if isinstance(rawAvailableZone.get('environment'), dict):
                t_dict = {}
                for key, value in rawAvailableZone['environment'].items():
                    t_dict[key.lower()] = value
                availableZone.environmentInfo = t_dict
        return availableZone

    def __createRegionObject(self, rawRegion):
        """create a region configured in test bed

        Args:
        rawRegion (list): 单个region在测试床中配置的数据.

        Returns:
        regionObj (region): region对象.

        """
        if 'available_zone' in rawRegion and rawRegion['available_zone']:
            rawAvailableZones = self.__changeParamToList(rawRegion['available_zone'])
            for rawAvailableZone in rawAvailableZones:
                available_zone = self.__createAvailableZone(rawAvailableZone)
                self.__available_zones[rawAvailableZone['id']] = available_zone
        regionObj = Region(self.__available_zones, rawRegion)
        # __available_zones过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
        self.__available_zones = {}
        return regionObj

    def __createDswareObject(self, rawDsware):
        """create a dsware configured in test bed

        Args:
        rawDsware (list): 单个dsware在测试床中配置的数据.

        Returns:
        dswareObj (dsware): dsware对象.

        """
        if 'dsware_node' in rawDsware and rawDsware['dsware_node']:
            rawDswareNodes = self.__changeParamToList(rawDsware['dsware_node'])
            for rawDswareNode in rawDswareNodes:
                dswareNodeObj = self.__createDswareNodeObject(rawDswareNode)
                self.__dswareNodes[rawDswareNode['id']] = dswareNodeObj
                wrapperObjs = []
                if 'management' in rawDswareNode and rawDswareNode['management']:
                    wrapperObjs = self.__createToolWrapperObjects(rawDswareNode['management'], deviceType='dsware')
                if wrapperObjs:
                    for wrapper in wrapperObjs:
                        self.__dswareNodes[rawDswareNode['id']].registerToolWrapper(host=wrapper["host"],
                                                                                    wrapper=wrapper["wrapper"])
        # 过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
        dsware = DSware(self.__dswareNodes)
        self.__dswareNodes = {}
        return dsware

    def __createFusionNodeObject(self, rawFusionNode):
        """create single fusion node
        Args：
        rawFusionNode (dict): 在测试床中配置的单个FusionNode数据.

        Returns:
        fusionNode (FusionStorageNode): FusionStorageNode对象.

        """
        template = {"id": {"types": str, "optional": True},
                    "name": {"types": str, "optional": True},
                    "communication": {"types": dict, "optional": True},
                    "management": {"types": dict, "optional": True},
                    "detail": {"types": dict, "optional": True},
                    "inet_panels": {"types": dict, "optional": True}}
        node = validateDict(rawFusionNode, template)
        nodeDict = {}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address', 'port', 'type', 'max_session']:
            if 'communication' in node and paramKey in node['communication']:
                nodeDict[paramKey] = node['communication'][paramKey]

        if 'detail' in node and node['detail']:
            nodeDict['detail'] = node['detail']

        if 'id' in node and node['id']:
            nodeDict['id'] = node['id']

        if 'name' in node and node['id']:
            nodeDict['name'] = node['name']

        if 'inet_panels' in node and node['inet_panels']:
            nodeDict['inet_panels'] = node['inet_panels']
        return FusionStorageNode.discover(nodeDict)

    def __createDswareNodeObject(self, rawDswareNode):
        """create single dsware node
        Args：
        rawDswareNode (dict): 在测试床中配置的单个DswareNode数据.

        Returns:
        dswareNode (DSwareNode): DswareNode对象.

        """
        template = {"id": {"types": str, "optional": True},
                    "name": {"types": str, "optional": True},
                    "communication": {"types": dict, "optional": True},
                    "management": {"types": dict, "optional": True},
                    "detail": {"types": dict, "optional": True},}
        node = validateDict(rawDswareNode, template)

        nodeDict = {}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address', 'port', 'type', 'max_session']:
            if 'communication' in node and paramKey in node['communication']:
                nodeDict[paramKey] = node['communication'][paramKey]

        if 'detail' in node and node['detail']:
            nodeDict['detail'] = node['detail']

        if 'id' in node and node['id']:
            nodeDict['id'] = node['id']

        if 'name' in node and node['id']:
            nodeDict['name'] = node['name']

        return DSwareNode.discover(nodeDict)

    def __createRocNodeObject(self, fusionNode):
        """create single roc node
        Args：
        fusionNode (dict): 在测试床中配置的单个fusionNode数据.

        Returns:
        rocNode (rocNode): rocNode对象.

        """
        template = {"id": {"types": str, "optional": True},
                    "name": {"types": str, "optional": True},
                    "communication": {"types": dict, "optional": True},
                    "management": {"types": dict, "optional": True},
                    "detail": {"types": dict, "optional": True},}
        node = validateDict(fusionNode, template)

        nodeDict = {}
        for paramKey in ['username', 'password', 'ipv4_address', 'ipv6_address', 'admincli_password', 'port',
                         'type', 'max_session', 'docker_ip', 'docker_user', 'docker_password', 'docker_port']:
            if 'communication' in node and paramKey in node['communication']:
                nodeDict[paramKey] = node['communication'][paramKey]

        if 'detail' in node and node['detail']:
            nodeDict['detail'] = node['detail']

        if 'id' in node and node['id']:
            nodeDict['id'] = node['id']

        if 'name' in node and node['id']:
            nodeDict['name'] = node['name']

        if 'inet_panels' in node and node['inet_panels']:
            nodeDict['inet_panels'] = node['inet_panels']

        if 'float_ip' in node and node['float_ip']:
            nodeDict['float_ip'] = node['float_ip']
        return RocNode.discover(nodeDict)

    def __createNasCluster(self, rawNasCluster):
        """create single nas cluster
        Args：
        rawNasCluster (dict): 在测试床中配置的单个nas集群数据.

        Returns:
        nasCluster (NasCluster): NasCluster对象。
        """
        if 'node' in rawNasCluster and rawNasCluster['node']:
            rawNodes = self.__changeParamToList(rawNasCluster['node'])
            for rawNode in rawNodes:
                self.__nasNodes[rawNode['id']] = self.__createNasNode(rawNode)

                wrapperObjs = []
                if 'management' in rawNode and rawNode['management']:
                    wrapperObjs = self.__createToolWrapperObjects(rawNode['management'], deviceType='nas')

                if wrapperObjs:
                    for wrapper in wrapperObjs:
                        self.__nasNodes[rawNode['id']].registerToolWrapper(host=wrapper["host"],
                                                                           wrapper=wrapper["wrapper"])

        nasClusterObjInfo = {"hosts" : self.__linkHostObjToUnifiedDevice(rawNasCluster),
                             "resource" : self,
                             "raw_resource_data" : rawNasCluster,
                             "nodes" : self.__nasNodes,
                             "device_type" : "nas_cluster"}

        if "environment_info" in rawNasCluster:
            nasClusterObjInfo["environment_info"] = rawNasCluster["environment_info"]
        #
        if "communication" in rawNasCluster and "ipv4_address" in rawNasCluster["communication"]:
            nasClusterObjInfo["ipv4_address"] = rawNasCluster["communication"]["ipv4_address"]
        #
        if "communication" in rawNasCluster and "ipv6_address" in rawNasCluster["communication"]:
            nasClusterObjInfo["ipv6_address"] = rawNasCluster["communication"]["ipv6_address"]

        if "communication" in rawNasCluster and "password" in rawNasCluster["communication"]:
            nasClusterObjInfo["password"] = rawNasCluster["communication"]["password"]

        if "communication" in rawNasCluster and "username" in rawNasCluster["communication"]:
            nasClusterObjInfo["username"] = rawNasCluster["communication"]["username"]

        if "id" in rawNasCluster and rawNasCluster["id"]:
            nasClusterObjInfo["device_id"] = rawNasCluster["id"]

        nasClusterObj = NasCluster(**nasClusterObjInfo)
        self.__nasNodes = {} # nas node对象为过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
        return nasClusterObj

    def __createRocRegions(self, rawRegions):
        """create all nas fusion storage nodes configured in test bed

        Args:
        rawRegions (list): 多个Region在测试床中配置的数据.

        Returns:
        errorMsg (list): 创建region的报错消息或空列表

        """
        errorMsg = []
        for rawRegion in rawRegions:
            try:
                regionObj = self.__createRocRegionObject(rawRegion)
                self.regions[rawRegion['id']] = regionObj
            except Exception:
                self.regionInitError += 1
                errorMsg.append(traceback.format_exc())
                self.logger.error("Create region[%s] error. detail:%s" % (rawRegion['id'], traceback.format_exc()))
        return errorMsg

    def __createRocRegionObject(self, rawRegion):
        """create a region configured in test bed

        Args:
        rawRegion (list): 单个region在测试床中配置的数据.

        Returns:
        regionObj (region): region对象.

        """
        if 'available_zone' in rawRegion and rawRegion['available_zone']:
            rawAvailableZones = self.__changeParamToList(rawRegion['available_zone'])
            for rawAvailableZone in rawAvailableZones:
                available_zone = self.__createRocAvailableZone(rawAvailableZone)
                self.__available_zones[rawAvailableZone['id']] = available_zone
        regionObj = RocRegion(self.__available_zones, rawRegion)
        # __available_zones过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
        self.__available_zones = {}
        return regionObj

    def __createRocAvailableZone(self, rawAvailableZone):
        """create an available zone configured in test bed

        Args:
        rawFusionNodes (list): 单个available zone在测试床床中的配置数据

        Returns:
        availableZone (AvailableZone): AvailableZone对象.

        """
        if rawAvailableZone.get('roc_node'):
            rawRocNodes = self.__changeParamToList(rawAvailableZone['roc_node'])
            for rawRocNode in rawRocNodes:
                rocNodeObj = self.__createRocNodeObject(rawRocNode)
                self.__rocNodes[rawRocNode['id']] = rocNodeObj
                wrapperObjs = []
                if 'management' in rawRocNode and rawRocNode['management']:
                    wrapperObjs = self.__createToolWrapperObjects(rawRocNode['management'], deviceType='roc')

                if wrapperObjs:
                    for wrapper in wrapperObjs:
                        self.__rocNodes[rawRocNode['id']].registerToolWrapper(host=wrapper["host"],
                                                                              wrapper=wrapper["wrapper"])
                # add rest wrapper here
                restDict = {"UniAutos.Wrapper.Api.Rest.Roc.RestForRoc":"RocRestBase"}
                for m, v in restDict.iteritems():
                    __import__(m)
                    moduleClass = getattr(sys.modules[m], v)
                    wobj = moduleClass()
                    rocNodeObj.registerToolWrapper(host=rocNodeObj, wrapper=wobj)

        availableZone = RocAvailableZone(self.__rocNodes)
        # 过程变量， 初始化完成后应该清空， 否则会影响后续的配置。
        self.__rocNodes = {}

        # 加入az的environment
        if isinstance(rawAvailableZone.get('environment'), dict):
            t_dict = {}
            for key, value in rawAvailableZone['environment'].items():
                t_dict[key.lower()] = value
            availableZone.environmentInfo = t_dict
        return availableZone

if __name__ == "__main__":
pass