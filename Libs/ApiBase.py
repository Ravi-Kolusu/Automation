"""
Function: Provide the base class of the API
"""

from Libs.WrapperBase import WrapperBase

class ApiBase(WrapperBase):
    def __init__(self, params=None):
        super(ApiBase, self).__init__(params)