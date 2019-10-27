"""
Function: Provides a base class for command encapsulation echo parsing
"""
import re
from Libs.TypeCheck import validateParam

GETMETHOD = 'getmethod'
SETMETHOD = 'setmethod'
PROPERTY = 'properties'
GLOBAL = 'global'

class WrapperBase(object):
    """
    Wrapper class initialization

    Args:
       param (dict) :: param = {"versionInfo":(str)}
    """
    def __init__(self, param=None):
        super(WrapperBase, self).__init__()
        if param and "versionInfo" in param:
            self.versionInfo = param["versionInfo"]

    def setDevice(self, device):
        """
        Bind the wrapper to the device

        Args:
            Device (obj) :: specific device object
        """
        if hasattr(self, "device"):
            self.device = device
            return self.device

    def getDevice(self):
        """
        Returns the device object bound to the wrapper
        """
        if hasattr(self, 'device'):
            return self.device
        return None

    def getDeviceVersion(self):
        pass

    @validateParam(versionInfo=str)
    def storeDeviceVersionInfo(self, versionInfo):
        """
        Save device verison information

        Args:
            versionInfo (str) :: version name string
        """
        self.versionInfo = versionInfo
        pass

    def retrieveDeviceVersionInfo(self):
        """
        Get device version information

        Returns:
            versionInfo (str) :: device version information
        """
        return self.versionInfo

    @validateParam(release=str, qualifier=str)
    def isRelease(self, release, qualifier="=="):
        """
        Detect the relationship between the provided version number and the device
        version number

        Args:
             release (str) :: the version number provided
             qualifier (str) :: the symbol of the comparison operation, default qualifier = "=="

        Returns:
              bool (1-true, 0-false)
        """
        pass

    def _getPropertyHash(self):
        """
        Get the property information of all wrappers

        Returns:
            propertyHash (dict) : property information for all wrappers
        """
        propertyHash = {}
        if hasattr(self, "getPropertyBasedOnVersion"):
            propertyHash = self.getPropertyBasedOnVersion()
        elif hasattr(self, 'PROPERTY_HASH'):
            propertyHash = self.PROPERTY_HASH

        return propertyHash

    def getLimitInfo(self):
        """
        Return wrapper limit information

        Returns:
             limitHash (dict) :: restriction information defined in properties
        """
        limitHash = {}
        if hasattr(self, "LIMITS_HASH"):
            limitHash = self.LIMITS_HASH

        return limitHash

    def getPropertyInfo(self, obj):
        """
        Get the property information of the corresponding class

        Args:
             obj (str) : the full path of the concrete wrapper class

        Returns:
              propHash (dict) :: attribute information of the corresponding class
        """
        propHash = self._getPropertyHash()
        if obj in propHash:
            return propHash[obj]
        else:
            return propHash

    def createPropertyInfoHash(self, obj, properties=list()):
        """
        Get the get and set methods corresponding to the specified property of obj

        Args:
            obj (obj/str) :: a full path string of a class instance or class
            properties (list) :: list of properties

        Returns:
              fullPropertyInfo (dict) :: specifies the dictionary of the get and set methods
                                         corresponding to the attribute

              fullPropertyInfo = {"propertyname1": {"getmethod":"methodname", "setmethod":"methodname"}}
        Example:
              self.createPropertyInfoHash(obj, ["p1", "p2", "p3"])
        """
        if not isinstance(obj, str):
            obj = obj.__module__+'.'+obj.__name__

        baseProps = self.getPropertyInfo(obj)
        fullPropertyInfo = {}
        if not baseProps:
            return fullPropertyInfo
        if properties:
            neededProps = properties
        else:
            if PROPERTY in baseProps and baseProps[PROPERTY]:
                neededProps = baseProps[PROPERTY].keys()
            else:
                neededProps = []
        for prop in neededProps:
            if PROPERTY in baseProps and baseProps[PROPERTY] and prop in baseProps[PROPERTY]:
                if prop not in fullPropertyInfo:
                    fullPropertyInfo[prop] = {}
                if GETMETHOD in baseProps[PROPERTY][prop] and baseProps[PROPERTY][prop][GETMETHOD]:
                    fullPropertyInfo[prop][GETMETHOD] = baseProps[PROPERTY][prop][GETMETHOD]
                elif GETMETHOD in baseProps[GLOBAL] and baseProps[GLOBAL][GETMETHOD]:
                    fullPropertyInfo[prop][GETMETHOD] = baseProps[GLOBAL][GETMETHOD]
                if SETMETHOD in baseProps[PROPERTY][prop] and baseProps[PROPERTY][prop][SETMETHOD]:
                    fullPropertyInfo[prop][SETMETHOD] = baseProps[PROPERTY][prop][SETMETHOD]
                elif SETMETHOD in baseProps[GLOBAL] and baseProps[GLOBAL][SETMETHOD]:
                    fullPropertyInfo[prop][SETMETHOD] = baseProps[GLOBAL][SETMETHOD]
        return fullPropertyInfo

    def getCommonPropertyInfo(self, getMethod, properties=list()):
        """
        Returns the class whose specified property has a common get method

        Args:
             getMethod (str) :: get method
             properties (list) :: the specified property

        Returns:
              classes (list) :: list of classes with common get methods

        Example:
              self.getCommonPropertyInfo(getMethod, ["property1", "property2"])
        """
        classes = []
        baseProps = self.getPropertyInfo(None)
        if not baseProps:
            return classes

        for singleClass in baseProps.keys():
            if not properties:
                twProps = self.createPropertyInfoHash(singleClass)
                properties = twProps.keys()
            propInfo = self.createPropertyInfoHash(singleClass, properties)
            for prop in propInfo.values():
                if "getmethod" in prop and prop['getmethod'] == getMethod:
                    classes.append(singleClass)
                    break
        return classes

    def convertBooleanToYesNo(self, val):
        """
        Convert true and false values

        Args:
             val: can be any value

        Returns:
              yes if value is True
              no if value is False
        """
        if val:
            return "yes"
        else:
            return "no"

    def convertBooleanToOnOff(self, val):
        """
        Convert true and false values

        Args:
             val: can be any value

        Returns:
              on if value is True
              off if value is False
        """
        if val:
            return "on"
        else:
            return "off"

    def convertStrToInt(self, rawVal):
        """
        Convert raw data string to int type

        Args:
             rawVal (str)

        Returns:
              Int
        """
        if re.search("[^0-9]+", rawVal) is None:
            return int(rawVal)
        return rawVal

    def convertRawToBoolean(self, rawVal):
        """
        Convert raw data yes/no/1/0 etc to boolean type

        Args:
             rawVal : yes/no/1/0

        Returns:
              bool value
        """
        if re.search('yes|enable|enabled|on|y|true|1', rawVal, re.IGNORECASE):
            return True
        else:
            return False





