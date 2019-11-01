#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: 公共函数包，用于存放Parameter不可抽象的公共类函数, Parameter模板.

版权信息: 华为技术有限公司，版权所有(C) 2014-2015.

"""
import collections
from Libs.Exception.CustomExceptions import InvalidParamException
from Libs.Exception.CustomExceptions import TypeException

# select 类型的Parameter模板，用于参数检查.
PARAMETER_TEMPLATE_SELECT = {'name': {"types": str, "optional": False},
                             'display_name': {"types": str, "optional": True},
                             'description': {"types": str, "optional": True},
                             'default_value': {"types": None, "optional": True},
                             'validation': {"types": dict, "optional": True,
                             "child": {'valid_values': {"types": list, "optional": True}}},
                             'type': {"types": str, "optional": False},
                             'identity': {"types": str, "optional": True},
                             'assigned_value': {"types": None, "optional": True},
                             'optional': {"types": bool, "optional": True}}

# time、size 类型的Parameter模板，用于参数检查.
PARAMETER_TEMPLATE_UNITS = {'name': {"types": str, "optional": False},
                            'display_name': {"types": str, "optional": True},
                            'description': {"types": str, "optional": True},
                            'default_value': {"types": None, "optional": True},
                            'validation': {"types": dict, "optional": True,
                            "child": {"max": {"types": str, "optional": True},
                            "min": {"types": str, "optional": True}}},
                            'type': {"types": str, "optional": False},
                            'identity': {"types": str, "optional": True},
                            'assigned_value': {"types": None, "optional": True},
                            'optional': {"types": bool, "optional": True}}

# number 类型的Parameter模板，用于参数检查.
PARAMETER_TEMPLATE_NUMBER = {'name': {"types": str, "optional": False},
                             'display_name': {"types": str, "optional": True},
                             'description': {"types": str, "optional": True},
                             'default_value': {"types": None, "optional": True},
                             'validation': {"types": dict, "optional": True,
                             "child": {"max": {"types": float, "optional": True},
                             "min": {"types": float, "optional": True}}},
                             'type': {"types": str, "optional": False},
                             'identity': {"types": str, "optional": True},
                             'assigned_value': {"types": None, "optional": True},
                             'optional': {"types": bool, "optional": True}}

# 通用Parameter模板
PARAMETER_TEMPLATE = {'name': {"types": str, "optional": False},
                      'display_name': {"types": str, "optional": True},
                     'description': {"types": str, "optional": True},
                     'default_value': {"types": None, "optional": True},
                     'validation': {"types": None, "optional": True},
                     'type': {"types": str, "optional": False},
                     'identity': {"types": str, "optional": True},
                     'assigned_value': {"types": None, "optional": True},
                     'optional': {"types": bool, "optional": True}}

# 通用ParameterType模板
PARAMETER_TYPE_TEMPLATE = {"type": {"types": str, "optional": False},
                           "validation": {"types": None, "optional": True},
                           "factory_method": {"types": None, "optional": True}}

# 定义type名称枚举
TYPE_NAME_SPACE = collections.namedtuple('TYPE', ('BOOLEAN', 'SIZE', 'TIME', 'NUMBER',
                                                  'IP_ADDRESS', 'TEXT', 'SELECT',
                                                  'LIST', 'MULTIPLE_BOOLEAN', 'MULTIPLE_SIZE',
                                                  'MULTIPLE_TIME', 'MULTIPLE_NUMBER', 'MULTIPLE_IP_ADDRESS',
                                                  'MULTIPLE_TEXT', 'MULTIPLE_SELECT', 'MULTIPLE_LIST'))

TYPE = TYPE_NAME_SPACE("boolean", "size", "time", "number", "ip_address", "text", "select",
                       "list", "multiple_boolean", "multiple_size", "multiple_time", "multiple_number",
                       "multiple_ip_address", "multiple_text", "multiple_select", "multiple_list")


def listMap(func, seq):
    # todo 参数检查
    """重写的map()函数,处理传入的seq参数(list)中元素有list类型的情况.

    Args：
    func (function): 需要递归执行的函数.
    seq (list): 需要递归处理的数据列表.

    Returns:
    Dict (dict): seq经过处理func函数后的字典数据.

    Raises:
    InvalidParamException: func、seq参数类型错误.
    TypeException: func处理后的结果不是dict类型时抛出异常.


    Notes:
    1、 该函数仅仅适用于MultipleThing中的list处理，传入的func返回值必须是dict.

    Examples:
    import TypeUnitCheck

    def func(seq):
    return {str(seq): seq+1}

    numberList = [1, 2, 3, [4, 5]]
    TypeUnitCheck.paramMap(func, numberList)

    Changes:
    2015-3-31 h90006090 增加Raise说明.

    """
    seqDict = {}

    # 函数检查.
    if not hasattr(func, '__call__'):
        raise InvalidParamException("The first argument(%s) must be function." % func)

    if not isinstance(seq, list):
        raise InvalidParamException("The second argument(%s) must be list." % seq)

    # 内嵌函数，处理seq参数(list)中元素有list类型的情况.
    def childMap(childFunc, childSeq, childDict):
        for child in childSeq:
            if isinstance(child, list):
                childMap(childFunc, child, childDict)
            else:
                # 此处要求函数处理后返回的值必须为字典类型.
                if not isinstance(childFunc(child), dict):
                    raise TypeException("listMap() failed, The childFunc() return is not dict, Can not use paramMap() in here. ")
                childDict.update(childFunc(child))
        return childDict
    return childMap(func, seq, seqDict)

if __name__ == "__main__":
    pass
