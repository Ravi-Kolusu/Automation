"""
Custom exception base class
"""
import traceback

class UniAutosException(Exception):
    """
    Custom exception base class, all exceptions inherit this exception

    Args:
        msg (str) :: custom prompt information, default value None

    Returns:
          UniAutosException.instance
    """
    def __init__(self, msg=None):
        if msg:
            self.message = msg

        # if msg is not None:
        #     self.message = msg + '\n'
        #     detail = traceback.format_exc()
        #     self.message += 'Details:\n%s'%(detail)
        #     del detail

    def __str__(self):
        """
        Override object.__str__ method, object no string
        """
        return self.message