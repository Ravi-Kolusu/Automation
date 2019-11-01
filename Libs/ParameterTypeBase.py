# !/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: ParameterType类，所有parameter类型的父类，用于接口声明和创建ParameterType对象实例.

版权信息: 华为技术有限公司，版权所有(C) 2014-2015.

"""

import re

from Libs.TypeCheck import *
from Libs.ParamUtil import PARAMETER_TYPE_TEMPLATE
from Libs.Exception.CustomExceptions import DictKeyException

class ParameterTypeBase(object):
    """ParameterTypeBase, parameter子类的父类

    功能说明：接口声明, parameter的"validation"和"type"初始化.

    Args:
    typeAndValidation (dict): 内容为parameter的"validation"和"type".

    Attributes:
    self.validation (dict or None) : parameter的validation.
    self.typeName (str) : parameter的type名称.

    Returns:
    ParameterType (instance): ParameterType对象实例.

    Raises:
    InvalidParamException: 参数类型错误, 不是dict类型.
    DictKeyException: 传入的参数的字典不符合PARAMETER_TYPE_TEMPLATE定义的格式.


    Examples:
    参考create()方法示例, 创建ParameterType实例对象.

    """
    @validateParam(typeAndValidation=dict)
    def __init__(self, typeAndValidation):
        super(ParameterTypeBase, self).__init__()
        validateDict(typeAndValidation, PARAMETER_TYPE_TEMPLATE)
        self.validation = None
        if "validation" in typeAndValidation:
            self.validation = typeAndValidation["validation"]
        self.name = typeAndValidation["type"]
        pass

    def hasValidation(self):
        """判断Parameter中是否存在"validation"

        该函数用于接口声明，并返回一个默认值，需要返回其他值时需子类重写.

        Args:
        None

        Returns:
        False (bool): 默认返回False.

        Raises:
        None

        Examples:
        import ParameterType
        paramTypeObj = ParameterType.create(typeAndValidation)
        paramTypeObj.hasValidation()
        """
        return False

    def getValidation(self):
        """获取parameter中的"validation"值

        该函数用于接口声明，并返回一个默认值，需要返回其他值时需子类重写.

        Args:
        None

        Returns:
        None: 默认返回None.

        Raises:
        None

        Examples:
        import ParameterType
        paramTypeObj = ParameterType.create(typeAndValidation)
        paramTypeObj.getValidation()
        """
        return None

    def getValidationValues(self):
        """获取parameter中"validation"的"valid_values"值

        该函数用于接口声明，并返回一个默认值，需要返回其他值时需子类重写.

        Args:
        None

        Returns:
        None: 默认返回None.

        Raises:
        None

        Examples:
        import ParameterType
        paramTypeObj = ParameterType.create(typeAndValidation)
        paramTypeObj.getValidationValues()

        """
        return None

    def getValidInput(self, defaultValue):
        """校验defaultValue合法性后返回处理后的值，接口声明

        Args:
        defaultValue (int|str|list): 需要进行判断处理的值.

        Returns:
        None

        Raises:
        None

        Notes:
        父类函数需要子类重写.

        Examples:
        参考子类示例.

        """
        pass

    def __boolean(inputType):
        """定义创建Boolean实例对象代码段
        """
        from UniAutos.TestEngine.ParameterType.Boolean import Boolean
        return Boolean(inputType)

    def __ipAddress(inputType):
        """定义创建IPAddress实例对象代码段
        """
        from UniAutos.TestEngine.ParameterType.IpAddress import IpAddress
        return IpAddress(inputType)

    def __text(inputType):
        """定义创建Text实例对象代码段
        """
        from UniAutos.TestEngine.ParameterType.Text import Text
        return Text(inputType)

    def __number(inputType):
        """定义创建Number实例对象代码段
        """
        from UniAutos.TestEngine.ParameterType.Number import Number
        return Number(inputType)

    def __time(inputType):
        """定义创建Time实例对象代码段
        """
        from UniAutos.TestEngine.ParameterType.Time import Time
        return Time(inputType)

    def __size(inputType):
        """定义创建Size实例对象代码段
        """
        from UniAutos.TestEngine.ParameterType.Size import Size
        return Size(inputType)

    def __list(inputType):
        """定义创建List实例对象代码段
        """
        from UniAutos.TestEngine.ParameterType.List import List
        return List(inputType)

    def __select(*args):
        """定义创建Select实例对象代码段
        """
        from UniAutos.TestEngine.ParameterType.Select import Select
        return Select(*args)

    @validateParam(typeAndValidation=dict)
    def create(typeAndValidation):
        """创建各种子类中定义的parameter Type实例对象.

        Args:
        typeAndValidation (dict): 内容为parameter的validation和type.

        Returns:
        ParameterType (instance): parameterType实例对象.

        Raises:
        DictKeyException: 传入参数(dict)没有key: "type"，或者"type"不在定义的ParameterType类型中.

        Notes:
        传入参数的格式参考各Type类型说明.

        Examples:
        typeAndValidation = {"validation": {"max": 200, "min": -10},
        "type": "number"}
        import ParameterType
        parameterTypeObj = ParameterType.create(typeAndValidation)

        Changes:
        2015-4-21 h90006090 删除ParamType的lambda函数，直接使用各中Type创建对象的私有函数的函数名.

        """
        if "type" not in typeAndValidation:
            raise DictKeyException("Create ParameterType Obj Failed, Parameter Format Error, have not key: 'type'.")
        typeName = typeAndValidation["type"].lower()

        # 设置是否为多选参数，初始值为False
        isMultiple = False

        # 检查传入参数的typeName是否为multiple_开头，且以上述字典定义的key结束的字符串
        multipleRegex = r'^multiple_(boolean|ip_address|text|number|size|time|list|select)$'
        if re.match(multipleRegex, typeName):
            typeName = re.sub(r'^multiple_', "", typeName)
            isMultiple = True
            typeAndValidation["type"] = typeName

        # 定义一个字典，Key为参数类型，Value为创建对象的函数名，用于创建typeObj
        paramType = {"boolean": __boolean,
                     "ip_address": __ipAddress,
                     "text": __text,
                     "number": __number,
                     "size": __size,
                     "time": __time,
                     "list": __list,
                     "select": __select}

        # 检查typeName是否在定义的字典中,根据typeName，得到需要创建typeObj的lambda函数
        if typeName not in paramType:
            raise DictKeyException("Create ParameterType Obj Failed, Parameter typeName(%s) is invalid." % typeName)
        typeObjFunc = paramType[typeName]

        # 如果是多选参数则单独处理,返回multiple类型的对象
        if isMultiple is True:
            from UniAutos.TestEngine.ParameterType.MultipleThing import MultipleThing
            # 如下multipleParam的key为固定值不能改变，否则影响ParameterType的创建.
            multipleParam = {"factory_method": typeObjFunc,
                             "type": typeName}
            if "validation" in typeAndValidation:
                multipleParam["validation"] = typeAndValidation["validation"]
                typeObj = MultipleThing(multipleParam)
            else:
                typeObj = typeObjFunc(typeAndValidation)
        return typeObj

if __name__ == "__main__":
    pass

