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

