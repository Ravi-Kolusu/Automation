try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from Libs.InitDict import InitDict
from Libs.Exception.CustomExceptions import TypeException

class xmlToDict:
    """
    Convert xml file data to dictionary type data class

    provides an interface to parse the xml file and convert it to a dictionary type
    """
    def __init__(self):
        pass

    @classmethod
    def _xmlTreeToDict(cls, nodeElement, xmlDictClass):
        """
        TODO
        """
        nodeDict = xmlDictClass()
        if len(nodeElement.items()) > 0:
            nodeDict.update(dict(nodeElement.items()))

        for child in nodeElement:
            childItemDict = cls._xmlTreeToDict(child, xmlDictClass)
            if child.tag in nodeDict:
                if isinstance(nodeDict[child.tag], list):
                    nodeDict[child.tag].append(childItemDict)
                else:
                    nodeDict[child.tag] = [nodeDict[child.tag], childItemDict]
            else:
                nodeDict[child.tag] = childItemDict
        text = ''
        if nodeElement.text is not None:
            text = nodeElement.text.strip()
        if len(nodeDict)>0:
            if len(text)>0:
                nodeDict[nodeElement.tag + '_text'] = text
        else:
            nodeDict = text
        return nodeDict

    @classmethod
    def getConfigFileRawData(cls, xmlFilePath, xmlDictClass=InitDict):
        """
        TODO
        """
        rootElementTree = None
        if not isinstance(xmlFilePath, basestring):
            raise TypeException('getConfigFileRawData(), param:xmlFilePath; Expected a file path string')
        try:
            rootElementTree = ET.parse(xmlFilePath).getroot()
        except IOError, error:
            raise IOError(error)
        except ET.ParseError, error:
            raise ET.ParseError(error)
        if rootElementTree is None:
            raise AttributeError('getConfigFileRawData(), Inout file have not root element')

        return xmlDictClass({rootElementTree.tag:cls._xmlTreeToDict(rootElementTree, xmlDictClass)})

    @classmethod
    def _dictKeywordValue(cls, tmpDict, key, value=None):
        """
        TODO
        """
        tmpValue = tmpDict.get(key, None)

        if tmpValue is not None:
            if value is None:
                return tmpValue
            elif value is not None and tmpValue == value:
                return tmpDict
            elif value is not None and tmpValue != value:
                return None
        for child in tmpDict:
            tmpValue = cls.getSpecificKeyRawData(tmpDict[child], key, value)

            if tmpValue is not None:
                break
        return tmpValue

    @classmethod
    def getSpecificKeyRawData(cls, rawDictData, key, value=None):
        """
        TODO
        """
        keywordValue = None
        if isinstance(rawDictData, dict):
            keywordValue = cls._dictKeywordValue(rawDictData, key, value)
        elif isinstance(rawDictData, list):
            for child in rawDictData:
                keywordValue = cls.getSpecificKeyRawData(child, key, value)
                if keywordValue is not None:
                    break
        return keywordValue

#==========================================================================================================

==============================================================================================================

from UniAutos.Util.XmlParser.XmlToDict import XmlToDict
"""

Function: InitDict class, the main function of this class is to initialize an empty dictionary, or convert the incoming data to a dictionary type.

Copyright Information: Huawei Technologies Co., Ltd., Copyright (C) 2014-2015

"""


class InitDict(dict):
"""Initialize the dictionary class

This class inherits dict and is used to initialize an empty dictionary, or to convert data to a dictionary type.

Args:
initDict (dict): The default is None.
Can be specified as a dictionary type of data.

Returns:
Dict: The initDict parameter returns an empty dictionary when default, and returns a dictionary with the specified data when specified as a dictionary type.

Examples:

1. Initialize an empty dictionary:
>>>dictClass = InitDict()
dictClass = {}

2.Convert data to dictionary type:
>>>score = {"Languages": "100", "Mathematics": "100"}
>>>name = "Jackie"
>>>myDict = InitDict({name: score})
myDict = {"jackie":
{"Languages": "100",
"Mathematics": "100"}
}

3.Define an alias for InitDict:
>>>myDictClass = InitDict


"""

def __init__(self, initDict=None):
"""InitDict constructor

Override the dict constructor to initialize an empty dictionary, or convert data to a dictionary type

"""
if initDict is None:
initDict = {}
dict.__init__(self,initDict)

if __name__ == "__main__":
pass

"""

Function: XmlToDict class, the main function of this class is to parse XML file data into dictionary type data.

Copyright Information: Huawei Technologies Co., Ltd., Copyright (C) 2014-2015

"""

try:
import xml.etree.cElementTree as ET
except ImportError:
import xml.etree.ElementTree as ET
from InitDict import InitDict
from UniAutos.Exception.TypeException import TypeException


class XmlToDict:
"""Convert Xml file data to dictionary type data class

Provides an interface to parse the xml file and convert it to a dictionary type

"""

def __init__(self):
pass

@classmethod
def _xmlTreeToDict(cls, nodeElement, xmlDictClass):
"""
The xml Element instance is passed in by other public functions that parse the data contained in the transferred Element instance and convert the data to a dictionary type.

Args:
nodeElement (xml.ElementTree.Element): xml Element instance.
xmlDictClass (InitDict): A custom dictionary category name used to initialize an empty dictionary, or to convert data to a dictionary type.

Returns:
Dict: The data contained in the dictionary element of the dictionary type.
{"jackie":
{"Languages": "100",
"Mathematics": "100"}
}

Raises:
TypeException: if the passed nodeElement parameter is not of type xml.ElementTree.Element.

Examples:
This function is a protected class function that needs to be called in a function of the class, or called in a subclass; an instance of this class can also be called, but it is not recommended.

1. Convert the Element instance to a dictionary type:
From InitDict import InitDict
From UniAutos.Util.XmlParser.XmlToDict import XmlToDict
Class MyClass(XmlToDict):
Def getXmlInfo(self):
nodeTagElement = None
xmlDictClass = InitDict
myDict = XmlToDict._xmlTreeToDict(nodeTagElement, xmlDictClass)

Changes:
2015-3-17 h90006090 Add class comments, function comments.
2015-3-19 h90006090 Change the nodeElement.text to None. If the judgment is not None, remove the else branch.
"""

nodeDict = xmlDictClass()
if len(nodeElement.items()) > 0:
nodeDict.update(dict(nodeElement.items()))


for child in nodeElement:
childItemDict = cls._xmlTreeToDict(child, xmlDictClass)

if child.tag in nodeDict:
if isinstance(nodeDict[child.tag], list):
nodeDict[child.tag].append(childItemDict)
else:
nodeDict[child.tag] = [nodeDict[child.tag], childItemDict]
else:
nodeDict[child.tag] = childItemDict

text = ''
if nodeElement.text is not None:
text = nodeElement.text.strip()

if len(nodeDict) > 0:
if len(text) > 0:
nodeDict[nodeElement.tag + '_text'] = text
else:
nodeDict = text

return nodeDict

@classmethod
def getConfigFileRawData(cls, xmlFilePath, xmlDictClass=InitDict):
"""Parse arbitrary xml file data and convert it to dictionary data type.

Args:
xmlFilePath (string): xml file path.
xmlDictClass (InitDict): The default is InitDict, which keeps the default value when used. It can be specified as dict.

Args:
xmlFilePath (string): xml file path.
xmlDictClass (InitDict): The default is InitDict, which keeps the default value when used. It can be specified as dict.

Returns:
Dict: The data contained in the xml file pointed to by xmlFilePath.

Returns:
Dict: The data contained in the xml file pointed to by xmlFilePath.

Raises:
TypeException: if xmlFilePath and nodeTag are not of type string.
IOError: The xml file pointed to by xmlFilePath does not exist.
xml.etree.ElementTree.ParseError: The xml file pointed to by xmlFilePath has a syntax error.
AttributeError: The root node of the obtained xml file is None.

Raises:
TypeException: if xmlFilePath and nodeTag are not of type string.
IOError: The xml file pointed to by xmlFilePath does not exist.
xml.etree.ElementTree.ParseError: The xml file pointed to by xmlFilePath has a syntax error.
AttributeError: The root node of the obtained xml file is None.

Examples:
1. Specify the xml file, convert the data to dict and return.

Code:
From UniAutos.Util.XmlParser.XmlToDict import XmlToDict
FilePath = "c:\\file.xml"
myDict = XmlToDict.getConfigFileRawData(FilePath)


Output:

Output:
{
"opt": {
"doc_type": "MAIN_CFG",
"parameters": {
"param": [
{
"name": "STOP_ON_ERROR",
"value": "0"
},
{
"name": "LOGGING_LEVEL",
"value": "INFO"
}
]
},
"local_base_log_path": "logs",
"version": "1"
}
}

Changes:
2015-3-17 h90006090 Add class comments, function comments.

"""
rootElementTree = None
if not isinstance(xmlFilePath, basestring):
raise TypeException('getConfigFileRawData(), param: xmlFilePath; Expected a file path string')

try:
rootElementTree = ET.parse(xmlFilePath).getroot()
except IOError, error:
raise IOError(error)
except ET.ParseError, error:
raise ET.ParseError(error)

if rootElementTree is None:
raise AttributeError('getConfigFileRawData(), Input file have not root element')

return xmlDictClass({rootElementTree.tag: cls._xmlTreeToDict(rootElementTree, xmlDictClass)})

@classmethod
def __dictKeywordValue(cls, tmpDict, key, value=None):
"""Gets the value of the specified keyword key of the dictionary type data, or returns the dictionary where the key and value are located when the value is specified.

Args:
tmpDict (dict): The dictionary data passed in, which is any dictionary value.
Key (str): the key of the dictionary to be queried
Value (str|int|list|dict|None): The value of the key to be queried.

Returns:
tmpValue(str|int|list|dict|None):
If no value is specified, the value of the specified key is directly returned. If the value parameter is specified, the dictionary of the key and value is returned. Otherwise, it returns None.

Raises:
None

Notes:
1. The xmlData name in the return value is the same as the parameter. At that time, the function is a recursive call method, and the final xmlData may be a sub-element dictionary of the parameter.

Examples：
firstID = {'id': 1, 'name': {'first': 'jack', 'second': 'brown'}}
__dictKeywordValue(firstID, "id", 1):

"""

tmpValue = tmpDict.get(key, None)

if tmpValue is not None:

if value is None:
return tmpValue

elif value is not None and tmpValue == value:
return tmpDict

elif value is not None and tmpValue != value:
return None

for child in tmpDict:
tmpValue = cls.getSpecificKeyRawData(tmpDict[child], key, value)

if tmpValue is not None:
break

return tmpValue

@classmethod
def getSpecificKeyRawData(cls, rawDictData, key, value=None):
"""Get the value of the specified keyword key of the dictionary data or list data parsed by xml, and return the dictionary where key and value are located when the value is specified.

Args:
xmlData (dict|list): The parsed xml data passed in, which is any dictionary value.
Key (str): The specified keyword to be queried, which is the key of the dictionary.
Value (str|int|list|dict|None):
- The value of the specified key to be queried, used to match whether the value of the specified key meets the condition, and returns a dictionary that meets the criteria.

Returns:
keywordValue(str|int|list|dict|None):
- If you do not specify value, the value of the specified key is directly returned. If the value parameter is specified, the dictionary of key and value is returned, otherwise it returns None.

Raises:
None

Notes:
1. The xmlData name in the return value is the same as the parameter. At that time, the function is a recursive call method, and the final xmlData may be a sub-element dictionary of the parameter.

Examples：
xmlData = {"a": 1,
"b": {"c": {"d": 3}},
"e": [{"id": 1, "name": {"first": "jack",
"second": "brown"}},
{"id": 2, "name": "tom"}]}
eValue = getSpecificKeyRawData(xmlData, "e")
firstID = getSpecificKeyRawData(eValue, "id", 1)

output:
eValue = [{'id': 1, 'name': {'first': 'jack', 'second': 'brown'}},
{'id': 2, 'name': 'tom'}]

firstID = {'id': 1, 'name': {'first': 'jack', 'second': 'brown'}}

"""
keywordValue = None

if isinstance(rawDictData, dict):
keywordValue = cls.__dictKeywordValue(rawDictData, key, value)

elif isinstance(rawDictData, list):

for child in rawDictData:
keywordValue = cls.getSpecificKeyRawData(child, key, value)

if keywordValue is not None:
break

return keywordValue

if __name__ == "__main__":
pass




