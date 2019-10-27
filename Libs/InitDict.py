class InitDict(dict):
    """
    Initialize the dictionary class

    This class inherits dict and is used to initialize an empty dictionary or to convert data to a directory type

    Args:
        initdict (dict) :: The default is None
                            can be specified as a dictionary type of data

    Returns:
          Dict : The initdict parameter returns an empty dictionary when default and returns a dictionary with the
                 specified data when specified as a dictionary type.

    Examples:

          1. Initialize an empty dictionary:
            >>> dictClass = InitDict()
            dictClass = {}

          2. Convert data to dictionary type:
            >>> score = {"Languages":"100", "Mathematics":"100"}
            >>> name = "Jackie"
            myDict = InitDict({name:score})
            myDict = {"Jackie": {"Languages":"100", "Mathematics":"100"}}

          3. Define an alias for InitDict:
              >>> myDictClass = InitDict
    """
    def __init__(self, initDict=None):
        """
        InitDict Constructor

        Override the dict constructor to initialize an empty dictionary or convert data to a dict type
        """
        if initDict is None:
            initDict = {}
        dict.__init__(self, initDict)

if __name__ == '__main__':
    pass
