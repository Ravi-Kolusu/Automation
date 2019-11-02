import re
import copy
from Units import Units
from Libs.Exception.CustomExceptions import DictKeyException
from Libs.Exception.CustomExceptions import InvalidParamException

def validateParam(**types):
    """
    Type detection of the passed argument, throwing an exception if it is not the expected argument type

    Args:
         Types (type) :: the type of the parameter passed in

    Returns:
          validateParamTypes :: returns the wrapped function

    Raises:
          InvalidParamException: The number of parameters passed in is inconsistent with the expected number of parameters
          InvalidParamException: The argument passed in is not the expected type

    Example:
          @validateParam(a=int, b=str)
          def test(a, b):
              pass
    """
    def validateParamTypes(function):
        # Whether the number of parameters of the detection method is consistent with the expected nnumber of parameters,
        # self does not calculate
        argCount = function.func_code.co_argcount
        for varName in function.func_code.co_varnames:
            if varName == 'self':
                argCount -= 1
        # Check if the incoming parameter is consistent with the expected number of parameters, otherwise an exception will be
        # thrown
        if len(types) != argCount:
            raise InvalidParamException('accept number of arguments not equal with function number of arguments in %s'%(function.func_name))

        def newFunction(*args, **kwargs):
            # Determine if the type of the parameter is the same as expected or it will throw an exception
            for incr, var in enumerate(args):
                if function.func_code.co_varnames[incr] in types and not isinstance(var,
                                                                                    types[function.func_code.co_varnames[incr]]):
                    raise InvalidParamException('arguments %s type is error. it is %s'%(var,
                                                                                        types[function.func_code.co_varnames[incr]]))
            for key, var in kwargs.iteritems():
                if key in types and not isinstance(var, types[key]):
                    raise InvalidParamException('arguments %s type is error.it is %s'%(var, types[key]))
            return function(*args, **kwargs)
        newFunction.func_name = function.func_name
        return newFunction
    return validateParamTypes

def validateDict(resource, template):
    """
    Detection of the dictionary, including the name detection of the key, the detection of the key type,
    whether it is the key of the value that must be passed in

    Args:
        resource (dict) :: the dictionary to be tested
        template (dict) :: a template for the dictionary containing the keywords, types, required of the desired dictionary

    Raises:
        InvalidParamException : The passed argument is not a dictionary type
        DictKeyException : dictionary template definition error
        DictKeyException : the passed in dictionary does not contain a passable key
        DictKeyException : an unknown key was passed in
        InvalidParamException : the value passed in is not the expected type

    Examples:
      pass in the dict of the desired detection, and the template of the dict, where the template needs to be written
      in mode
      {key: {"types": xxxx, "optional": xxxxx, "child": xxxx}}
      a keyword followed by a dictionary contains three keywords:
         types : the expected type of the value of the key. If the value is None, no type detection is performed
         optional : whether the key is optional (True: optional, False:required)
         child : if the value is a dic type, you must pass in the type expected by this dict here
         enum : if the value type is None, you can add a range of expected values for that type later.
                need to be with the list type, such as "enum":["str", 1, 100]
         default : set the default value

      dicts = {"name": {"types":str, "optional":False},
                "age": {"types":int, "optional":True, "default":1},
                "male": {types":None, "optional":True, "enum":["male", "female"]},
                "path": {types":int, "optional":True,
                                     "child":{"path_dir":{"types":str, "optional":True, "default":1}}}}
    """
    # Throws an exception if the passed argument is not a dictionary type
    if not isinstance(resource, dict) or not isinstance(template, dict):
        raise InvalidParamException("arguments %s or %s type is error.it must be dict type"%(resource, template))
    for item in template:
        if 'types' not in template[item] or 'optional' not in template[item]:
            raise DictKeyException('template dict is error. miss key in %s'%(item))
        if isinstance(template[item]['types'], dict) and 'child' not in template[item]:
            raise DictKeyException('template dict is error. miss key in %s'%(item))
        # check if there is a required keyword in the template but the detected dict does not contain
        if item not in resource and not template[item]['optional']:
            raise DictKeyException('miss required key %s'%(item))

        # Add default value
        if item not in resource and 'default' in template[item]:
            resource[item] = template[item]['default']
        # check if keywords that are not in the template are included
    for item in resource:
        # Throws an exception if no keyword is detexted
        if item not in template:
            continue

        # If the type of the expected value in the template is detected to be None
        if template[item]['types'] == None:
            if 'enum' in template[item]:
                if resource[item] not in template[item]['enum']:
                    raise DictKeyException('this value %s is not include in key %s'%(resource[item], item))
                continue

        if not isinstance(resource[item], template[item]['types']):
            raise InvalidParamException('dict value %s in key: %s type is error. Expected type:%s, real type:%s'%(resource[item],
                                                                                                                  item,
                                                                                                                      template[item]['types'],
                                                                                                              type(resource[item])))
    return resource

def newValidateDict(resource, template):
    """对字典的检测，包含key的名称检测，key类型的检测，是否为必须传入的value的key

    Args:
    resource (dict): 检测的字典
    template (dict)：字典的模板，包含期望的字典的各个关键字，类型，是否为必选

    Raises:
    InvalidParamException: 传入参数不是字典类型
    DictKeyException: 字典模板定义错误
    DictKeyException: 传入的字典中没有包含必传的key
    DictKeyException: 传入了未知的key
    InvalidParamException: 传入的value值不是期望的类型

    Examples:
    传入期望检测的dict,以及dict的模板,其中模板需按下模式编写 {key: {"types": xxxxx, "optional": xxxxxx}}

    types：该key的value期望的类型，如果该值为None,则不做类型检测(该关键字必须存在)
    optional: 该key是否为可选 True:可选，False:必选(该关键字必须存在)
    child: 如果该value是字典类型，则必须在这里传入这个字典期望的类型
    enum: 如果该value类型是None，则可以在后面添加该类型的期望值范围。需跟list类型，如“enum”: ["str", 1, 100.23]
    default: 设置默认值,传入的字典中没有包含该参数，则将模板中的该参数传入，并附上默认值
    depend: 参数依赖关系检测，后面跟参数关系列表。[a,b]表示a或者b [(a,b)]表示a和b
    mutex: 参数互斥关系检测，后面跟参数关系列表。[a,b]表示a或者b [(a,b)]表示a和b
    other: 简短的代码执行，后面跟str型。直接运行该字符串，变量名必须为input：如：" if input > 100: raise: Exception("Error")"

    dicts = {"name": {"types": str, "optional": False},
    "age": {"types": int, "optional": True。"default":1},
    "male": {"types": None, "optional": True, "enum": ["male", "famale"]},
    "path": {"types": dict, "optional": True, "child": {"path_dir": {"types": str,"optional": False}}}}

    dit = {"name": "test", "age": 12, "male": "male", "path": {"path_dir": "xxxx"}}

    validateDict(dit, dicts)

    Changes:
    2015-3-25 twx195475 创建

    Return :
    resource (dict): 返回处理好的参数字典
    """
    resourceKeyList = list(resource)
    templateKeyList = list(template)

    if not isinstance(resource, dict) or not isinstance(template, dict):
        raise Exception("arguments resource or 'template type is error.it must be dict type." )

    for key in template:
        # 检测是否每个参数都至少包含了关键字 optional和types
        if 'optional' not in template[key] or 'types' not in template[key]:
            raise Exception("params 'optional' or 'types' must in params '%s'." % key)

        # 检测传入的参数中没有包含模板中的必选参数则抛出异常。
        if template[key]['optional'] is False and key not in resourceKeyList:
            raise Exception("miss required params '%s'." % key)

        # 检测传入的参数中没有值但是模板中包含有默认值的参数，则在传入的参数中添加默认值。
        if 'default' in template[key] and key not in resourceKeyList:
            resource[key] = template[key]['default']

    # 重新刷新resourceKeyList列表
    resourceKeyList = list(resource)

    for key in resourceKeyList:
        # 如果传入了模板里面没有的参数，否则抛出异常。
        if key not in templateKeyList:
            raise Exception("not found this params '%s'!"% key)

        value = resource[key]

        # 关键字'types'处理
        if 'types' in template[key] and template[key] is not None:
            checkValueTypes(value, template[key]['types'])

        # 关键字'enum'处理。
        if 'enum' in template[key]:
            checkValueEnum(value, template[key]['enum'])

        # 关键字'depends'处理。
        if 'depends' in template[key]:
            checkValueDepend(key, template[key]['depends'], resourceKeyList)

        # 关键字'mutex'处理。
        if 'mutex' in template[key]:
            checkValueMutex(key, template[key]['mutex'], resourceKeyList)

        # 关键字'other'处理。
        if 'other' in template[key]:
            checkValueOther(value, template[key]['other'])

        # 关键字'child'处理。
        if 'child' in template[key]:
            if isinstance(value, dict) is False :
                raise Exception('child is not dicts !')

            NewDict = newValidateDict(value, template[key]['child'])
            resource[key] = NewDict

    return resource

def checkValueEnum(value, enumList):
    """对字典的中的关键字enum处理

    Args:
    value (instance): 要检测的对象
    enumList (list)：可允许的列表

    Raises:
    InvalidParamException: 传入参数没有在模板中找到

    Examples:
    checkValueEnum（"test", ["test", 10, [], "xx"]）

    Changes:
    2015-3-25 twx195475 创建
    """
    if value not in enumList:
        raise InvalidParamException("the value '%s' not in tempDict %s list!" %(value, enumList))

def checkValueTypes(value, types):
    """对字典的中的关键字Types处理

    Args:
    value (instance): 要检测的对象
    types (type, str)：期望的类型,
    类型一系统默认：str, int, list, dict, None, tuple, float
    类型二自定义： 'Time', 'Size', 'Number', 'instance', 'function', 'classobj'

    Raises:
    InvalidParamException: 传入的值不是期望的类型

    Examples:
    checkValueTypes("test", str)

    Changes:
    2015-3-25 twx195475 创建
    """
    if types == None:
        return

    if isinstance(types, str):
        listTypeForSys = ['instance', 'function', 'classobj']
        listTypeForUnits = ['Time', 'Size', 'number']

        if types not in listTypeForSys and types not in listTypeForUnits:
            raise InvalidParamException("unkown types %s" %types)
        elif types in listTypeForSys:
            valueType = re.search('' ,str(type(value))).groups()[0]
            if valueType == types:
                return
        elif types in listTypeForUnits:
            if types is 'Time' and Units.isTime(value) is False:
                raise InvalidParamException("the value %s is not Time types!" %value)
            elif types is 'Size' and Units.isSize(value) is False:
                raise InvalidParamException("the value %s is not Size types!" %value)
            elif types is 'Number' and Units.isNumber(value) is False:
                raise InvalidParamException("the value %s is not Number types!" %value)
    else:
        if isinstance(value, types) is True:
            return
    raise InvalidParamException("the value '%s' is not %s!" %(value, types))

# 需要修改之前的代码，暂时不做考虑这种实现方式
def checkValueTypes_other(value, types):
    listType = ['Null', 'instance', 'function', 'int', 'str', 'list', 'tuple', 'dict', 'float', 'None',
                'classobj', 'type']
    for t in types:
        if t == 'Null':
            return
        if t in listType:
            valueTypes = type(value)
            valueType = re.search('' ,valueTypes).groups()[0]
            if valueType != t:
                raise Exception("the value %s in Error types!" %value)
        else:
            if isinstance(value ,t) == False:
                raise Exception("the value %s in Error types!" %value)

# 依赖关系
def checkValueDepend(value, templateList, resourceKeyList):
    """对字典的中的关键字Depend处理,参数的依赖关系。 依赖关系列表如：templateList = [a, b, (c, d)]，
    该参数需要依赖于a参数 或者 依赖于b参数 或者 依赖于c和d，（c, d参数都必须存在）。

    Args:
    value (instance): 要检测的对象
    templateList (list)：模板中参数依赖列表
    resourceKeyList (list)：传入的参数列表

    Raises:
    InvalidParamException: 没有找到该参数所依赖的其他参数

    Examples:
    checkValueDepend("name", ["age","path"], resource)
    checkValueDepend("age", ["path"], resource)

    Changes:
    2015-3-25 twx195475 创建
    """
    if isinstance(templateList, list) is False or isinstance(resourceKeyList, list) is False:
        raise InvalidParamException("the params must be list type~!")
    for key in templateList:
        if isinstance(key, tuple) is False:
            if key in resourceKeyList:
                return
        else:
            for item in key:
                if item not in resourceKeyList:
                    raise InvalidParamException("the params '%s' must depend on other params %s, but not found them." %(value , templateList))
            return
    raise InvalidParamException("the params '%s' must depend on other params %s, but not found them." %(value, templateList))

# 互斥关系
def checkValueMutex(value, templateList, resourceKeyList):
    """对字典的中的关键字Mutex处理,参数的互斥关系。 依赖关系列表如：templateList = [a, b, (c, d)]，
    该参数与 a参数 或者 依赖于b参数 或者 于c和d，（c,d参数都必须存在）参数不能一起存在。

    Args:
    value (instance): 要检测的对象
    templateList (list)：模板中参数依赖列表
    resourceKeyList (list)：传入的参数列表

    Raises:
    InvalidParamException: 找到了与该参数互斥的参数，他们不能一起存在

    Examples:
    checkValueMutex("name", ["age","path"], resource)
    checkValueMutex("age", ["path"], resource)

    Changes:
    2015-3-25 twx195475 创建
    """
    if isinstance(templateList, list) is False or isinstance(resourceKeyList, list) is False:
        raise InvalidParamException("the params must be list type~!")

    for key in templateList:
        if isinstance(key, tuple) is False:
            if key in resourceKeyList:
                raise InvalidParamException("the params '%s' can not with some another params %s" %(value, templateList))
        else:
            isfound = 0
            for item in key:
                if item in resourceKeyList:
                    isfound += 1
            if isfound == len(key):
                raise InvalidParamException("the params '%s' can not with some another params %s" %(value, templateList))
    return

# 执行语句
def checkValueOther(value, templateMethod):
    """对字典的中的关键字other处理,templateMethod 必须为str,并且替换的关键字为 input
    例如："if input > 10: raise Exception('Error Numbers!!')"

    Args:
    value (instance): 要处理的对象
    templateMethod (str)：模板中参数依赖列表
    Raises:
    None

    Examples:
    checkValueOther(11, "if input > 10: raise Exception('Error Numbers!!')")
    Changes:
    2015-3-25 twx195475 创建
    """
    if isinstance(templateMethod, str) is False:
        return

    strs = re.sub('input', str(value), templateMethod )
    exec(strs)

def mySub(line, characters):
    '''剔除字符串开头部分的乱码'''

    # 避免剔除分隔符
    if re.search('\w+', line):
        for searcher in characters:
            line = re.sub(searcher, '', line)
    return line

def removeSpecialCharacters(*cmds):
    '''剔除指定命令回显当中出现的指定特殊字符

    Args:
    cmds type(tuple): 需要处理的命令,以及需要处理的特殊字符的正则匹配表达式

    Example:
    @removeSpecialCharacters(
    ('show_alarm', ('\b', '^[-/\\\\|]+', '^Processing\.{3}\s{2}'))
    )
    def func():

    '''
    def decoratorRemoveCharacters(function):
        def removeCharacters(*args, **kwargs):
            if 'rawOutput' in kwargs:
                output = kwargs['rawOutput']
            else:
                output = args[-1]

            # 回显类型不对时不做处理
            if not output or not isinstance(output, list):
                return function(*args, **kwargs)

            cmd = [cmd for cmd in cmds if re.sub('_', ' ', cmd[0]) in output[0]]
            # 不属于指定处理命令集不作处理
            if not cmd:
                return function(*args, **kwargs)

            # 剔除处理前的回显列表
            if 'rawOutput' in kwargs:
                del kwargs['rawOutput']
            else:
                args = args[:-1]
            # 对回显进行剔除特殊字符处理
            characters = [cmd[0][1] for i in xrange(len(output))]
            rawOutput = map(mySub, output, characters)
            return function(*args, rawOutput=rawOutput, **kwargs)
        return removeCharacters
    return decoratorRemoveCharacters

def getEventAlarmDetailDecorator(*fields):
    '''适配修改报警命令中的指定字段
    Args :
    fields type(dict) : 需要处理的命令,以及需要处理的特殊字符的正则匹配表达式

    Example:
    @getEventAlarmDetailDecorator(
    ('en_particular',('(\[.+?\])+','%s'))
    )
    def fun
    '''
    def decoratorGetEventAlarmDetail(func):
        def getDetail(*arges, **kwargs):
            reslut = func(*arges, **kwargs)
            if not reslut:
                return reslut
            value = []
            # 属于指定命令集则做以下处理
            for field in fields:
                if isinstance(field, tuple):
                    for i in range(0, len(field[1]), 2):
                        if isinstance(reslut[field[0]], list):
                            value = [re.sub(field[1][i], field[1][i + 1], data) for data in reslut[field[0]]]
                            if field[0] == 'en_particular':
                                # 剔除对比阵列上多余的信息
                                value = [re.sub('(\{.+?\})+', '', val) for val in value]
            # 去除空行
            value = [line for line in value if line]
            # 将处理好后的命令集添加到reslut
            reslut["detail"] = "\n".join(value)
            return reslut
        return getDetail
    return decoratorGetEventAlarmDetail