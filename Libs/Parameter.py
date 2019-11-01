#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: 提供用例的parameter的处理接口.

版权信息: 华为技术有限公司，版权所有(C) 2014-2015.

"""

import re

from UniAutos.TestEngine.ParameterType import ParameterTypeBase
from Libs.TypeCheck import *
from Libs.Exception.CustomExceptions import DictKeyException


class Parameter:
    """Parameter类，实例化Parameter对象

    Args：
    param (dict): 用例中添加的parameter参数, 键值对说明如下:
    name (str): parameter的名称, 必选参数.
    display_name (str): parameter的显示名称, 可选参数.
    description (str): parameter的描述信息，可选参数.
    default_value (parameterType): parameter的默认值，可选参数，优先级最低.
    type (str): parameter的值类型，由ParameterType定义，必选参数取值范围为:
    -Boolean、Ip_Address、List、Number、Select、Size、Text、
    -Time、Multiple_(Boolean、Ip_Address、List、Number、
    -Select、Size、Text、Time).
    identity (str): parameter的标识.
    assigned_value (parameterType): parameter设置值，优先级高于default_value，可选参数.
    optional (bool): parameter的值是否时可选的，可选参数，不传入值时默认为False.
    validation (dict): parameter对象的validation(校验)值，默认为None.

    Attributes:
    self.name (str) : parameter对象的名称，必须存在.
    self.type (str) : parameter对象的类型，必须存在.
    self.identity (str) : parameter对象的唯一标识.
    self.displayName (str) : parameter对象的详细描述.
    self.description (str) : parameter对象的description.
    self.optional (str) : parameter对象的optional，parameter是否必要，默认为True.
    self.validationValues (list) : parameter对象中的valid_values值，默认为None.
    self.validation (dict) : parameter对象的validation值，默认为None.
    self.type (ParameterTypeBase) : parameter类型对象，与self.parameter["type"]值相同.

    Returns:
    Parameter (instance): parameter对象实例.

    Raises:
    InvalidParamException：传入parameter不是dict.
    DictKeyException: 传入parameter没有name、和type.

    注：其他异常，参考对应的parameter type对象异常.

    Notes：
    1、输入的parameter参数必须符合如下格式：
    parameter = {'name': 'fs_type', # 必要参数.
    'display_name': 'filesystem type',
    'description': 'ext3 or ext2 or mixed',
    'default_value': 'ext3',
    'validation': {
    'valid_values': ['ext3, ext2'],
    }, # value必须为ext3和ext2的其中之一.
    'type': 'select', # 必要参数.
    'identity': 'id1',
    'assigned_value': 'ext2',
    'optional': True} # 必须是布尔型，不给定时默认为True.

    Examples:
    from UniAutos.TestController.Parameter import Parameter
    parameterObj = Parameter(parameter)
    """
    @validateParam(param=dict)
    def __init__(self, param):
        self.parameter = param
        # parameter中type和name是必选项.
        if "type" not in self.parameter or "name" not in self.parameter:
            raise DictKeyException("Parameter create Failed, Parameter have not key: 'type' or 'name'.")
        # 将传入的type和validation抛出, 用于创建ParameterType对象.
        typeAndValidation = {"type": self.parameter.pop("type", None)}
        if "validation" in self.parameter:
            typeAndValidation["validation"] = self.parameter.pop("validation", None)
        self.type = ParameterTypeBase.create(typeAndValidation)
        self.parameter["type"] = self.type

        # 转换检查value是否合法.
        if "default_value" in self.parameter:
            self.parameter["default_value"] = self.type.getValidInput(self.parameter["default_value"])
        if "assigned_value" in self.parameter:
            self.parameter["assigned_value"] = self.type.getValidInput(self.parameter["assigned_value"])

        self.name = self.parameter["name"]
        self.identity = None
        if "identity" in self.parameter:
            self.identity = self.parameter["identity"]

        self.displayName = None
        if "display_name" in self.parameter:
            self.displayName = self.parameter["display_name"]

        self.description = None
        if "description" in self.parameter:
            self.description = self.parameter["description"]

        self.optional = False
        if "optional" in self.parameter:
            self.optional = self.parameter["optional"]

        self.validationValues = self.type.getValidationValues()
        self.validation = self.type.getValidation()

    def isOptional(self):
        """校验parameter对象是否为一个Optional对象

        Args:
        None

        Returns：
        True (bool)：是Optional参数.
        False (bool): 不是Optional参数.

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.isOptional()

        """
        if "optional" in self.parameter:
            return self.parameter["optional"]
        return False

    def hasAssignedValue(self):
        """判断parameter中是否存在assigned_value

        Args:
        None

        Returns：
        True (bool): 存在.
        False (bool)：不存在.

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.hasAssignedValue()

        Changes：
        2015-4-3 h90006090 修改为直接返回判断
        """
        return "assigned_value" in self.parameter

    def hasDefaultValue(self):
        """判断parameter中是否存在default_value

        Args:
        None

        Returns：
        True (bool): 存在.
        False (bool)：不存在.

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.hasDefaultValue()

        Changes：
        2015-4-3 h90006090 修改为直接返回判断
        """
        return "default_value" in self.parameter

    def hasValidation(self):
        """判断parameter中是否存在"validation"

        Args:
        None

        Returns：
        True (bool): 存在.
        False (bool)：不存在为.

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.hasValidation()

        """
        return self.type.hasValidation()

    def getAssignedValue(self):
        """获取parameter对象的assigned_value

        Args:
        None

        Returns：
        self.parameter["assigned_value"] (int|str|list): parameter对象存在assigned_value时返回assigned_value.
        None: 不存在assigned_value

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.getAssignedValue()

        """
        if self.hasAssignedValue():
            return self.parameter["assigned_value"]
        return None

    def getDefaultValue(self):
        """获取parameter对象的default_value

        Args:
        None

        Returns：
        self.parameter["default_value"] (int|str|list): parameter对象存在default_value时返回default_value.
        None: 不存在default_value

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.getDefaultValue()
        """
        if self.hasDefaultValue():
            return self.parameter["default_value"]
        return None

    def getValue(self):
        """获取parameter对象的value.

        Args:
        None

        Returns：
        parameter的value (int|str|list): 若parameter对象存在assigned_value返回assigned_value，否则返回default_value.

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.getValue()

        """
        if self.hasAssignedValue():
            return self.getAssignedValue()
        return self.getDefaultValue()

    def getParamKey(self):
        """转换value为dict类型，并返回

        Args:
        None

        Returns：
        paramKey (dict): parameter对象的关键信息："name"和"value".

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.getParamKey()
        """
        paramKey = {"name": self.name, "value": self.getValue()}
        return paramKey

    def hasValue(self):
        """判断parameter对象是否存在value

        Args:
        None

        Returns：
        True (bool): 存在.
        False (bool): 不存在.

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.hasValue()
        """
        return self.hasAssignedValue() or self.hasDefaultValue()

    def getParamInstanceData(self):
        """获取一个应用于TestSuite的parameter值

        Args:
        None

        Returns：
        instanceData (dict): parameter参数，包含name、values、和identity

        Raises:
        None

        Notes：
        返回值的格式为：
        {"name": "name of param",
        "value": "param value",
        "identities": {"identity":[{"name": "ax_id", "value": "param id"}]}}

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.getParamInstanceData()
        """
        instanceData = {"name": self.name,
                        "identities": {"identity": [{"name": "ax_id",
                                                     "value": self.identity}]}}
        if re.match(r'(multiple|list)', self.type.name):
            instanceData["value"] = {}
            instanceData["value"].update({"values": self.getValue()})
        else:
            instanceData["value"] = self.getValue()
        return instanceData

    def getMetaData(self):
        """获取parameter对象的用例中parameter的原始值

        Args:
        None

        Returns:
        metaData (dict): parameter的原始值.

        Raises:
        None

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.getMetaData()
        """
        metaData = {"type": self.type.name, "name": self.name}
        if "identity" in self.parameter:
        metaData["identity"] = self.identity
        if "display_name" in self.parameter:
            metaData["display_name"] = self.displayName
        if "description" in self.parameter:
            metaData["description"] = self.description
        if "optional" in self.parameter:
            metaData["optional"] = self.parameter["optional"]
        if "default_value" in self.parameter:
            metaData["default_value"] = self.parameter["default_value"]
        if self.hasValidation():
            metaData["validation"] = self.validation
        return metaData

    def setAssignedValue(self, assignedValue):
        """将assignedValue校验后，设置为parameter对象的assigned_value

        Args:
        assignedValue (int|str|list): 传入的需要设置的assigned value值.

        Returns:
        None

        Raises:
        参考对应的parameter type对象.

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.setAssignedValue("thin")
        """
        self.parameter["assigned_value"] = self.type.getValidInput(assignedValue)

    def setDefaultValue(self, defaultValue):
        """将defaultValue校验后，设置为parameter对象的default_value

        Args:
        defaultValue (int|str|list): 传入的需要设置的default value值.

        Returns:
        None

        Raises:
        参考对应的parameter type对象.

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.setDefaultValue("thin")
        """
        self.parameter["default_value"] = self.type.getValidInput(defaultValue)

    def setValue(self, paramValue):
        """设置parameter对象的value

        Args:
        paramValue (int|str|list): 传入的需要设置的parameter value值.

        Returns:
        None

        Raises:
        参考对应的parameter type对象.

        Examples:
        from UniAutos.TestController.Parameter import Parameter
        parameterObj = Parameter(param)
        parameterObj.setValue("thin")
        """
        self.setAssignedValue(paramValue)

if __name__ == "__main__":
    pass