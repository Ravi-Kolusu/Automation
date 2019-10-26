from UniAutosException import UniAutosException

class CommandException(UniAutosException):
    """
    command line exception class can be thrown when the command fails to be executed
    the echo or the command format is incorrect

    Args:
        msg (str) :: custom prompt information, default is None

    Returns:
          CommandException instance

    Example:
          1. Throw a commandexception when sending command "show lun general"
          if SendCmd('show lun general') == False:
              raise CommandException('command excute failed')

          Messgae value:
              command excute failed
    """
    def __init__(self, msg=None, result=None):
        self.result = result
        UniAutosException.__init__(self, msg)

class ConnecitonException(UniAutosException):
    """
        session exception linked to an object

        Args:
            msg (str) :: custom prompt information, default is None

        Returns:
              ConnectionException instance

        Example:
              1. when the channel state is fault, throw a connection exception

              Messgae value:
                  command excute failed
        """

    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)

class DeadComponentException(UniAutosException):
    """
    The business object to be operated should have been deleted fro some reason

    Args:
        msg (str) :: custom prompt information, default is None
    """
    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)

class DictKeyException(UniAutosException):
    """
    In the dictionary that is accessed, the expected key doesnot exist or the name
    is incorrect and this exception can be thrown

    Args:
        msg (str) :: custom prompt information, default is None
    """

    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)

class DictValueException(UniAutosException):
    """
    In the dictionary that is accessed, the value corresponding to a key is incorrect
    and this exception can be thrown

    Args:
        msg (str) :: custom prompt information, default is None
    """
    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)

class FileNotFoundException(UniAutosException):
    """
    Thrown when the file is not existed

    Args:
        msg (str) :: custom prompt information, default is None

    Examples:
          if os.path.exist(r'C:\s.txt') == False:
              raise FileNotFoundException('file does not exist')
    """
    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)


class InvalidParamException(UniAutosException):
    """
    It is thrown when an error parameter type or parameter value error is passed

    Args:
        msg (str) :: custom prompt information, default is None
    """
    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)


class ObjectNotFoundException(UniAutosException):
    """
    Determine whether the variable a exists, call the variable if exists,
    or this exception

    Args:
        msg (str) :: custom prompt information, default is None
    """
    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)


class PropertyException(UniAutosException):
    """
    Determine whether instance a contains the attribute 'property',
    if not exists it exists this exception

    Args:
        msg (str) :: custom prompt information, default is None

    Example:
          if hasattr(a, 'property') == False:
              raise PropertyException('property not found')
    """
    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)


class TimeoutException(UniAutosException):
    """
    Args:
        msg (str) :: custom prompt information, default is None
    """

    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)


class TypeException(UniAutosException):
    """
    Args:
        msg (str) :: custom prompt information, default is None
    """

    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)


class UnImplementedException(UniAutosException):
    """
    There is no method in the subclass this will be thrown

    Args:
        msg (str) :: custom prompt information, default is None
    """

    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)

class UnsupportedException(UniAutosException):
    """
    Args:
        msg (str) :: custom prompt information, default is None
    """

    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)


class ValueException(UniAutosException):
    """
    The local variable value is not the expected value,

    Args:
        msg (str) :: custom prompt information, default is None

    Example:
          if a is not "Type":
              raise ValueException('a is not type')
    """
    def __init__(self, msg=None):
        UniAutosException.__init__(self, msg)
