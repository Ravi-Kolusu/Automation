"""
Description :: base class of Restful
"""

import requests
import json

from Libs.ApiBase import ApiBase
from Libs.TypeCheck import validateParam, validateDict
from Libs import Log
from Libs.Exception.CustomExceptions import InvalidParamException
from Libs.Exception import UniAutosException

class RESTBase(ApiBase):
    """
    Base class of Restful

    1xx : Informational
    2xx : Success
    3xx : Redirection
    4xx : Client Error
    5xx : Server Error
    """
    HttpErrorCode = {
        200: 'OK action with content returned',
        201: 'OK Create with content returned',
        202: 'Accepted as an async process',
        204: 'OK no content returned',
        400: 'Bad Request, Badly formed URI, parameters, headers or body content',
        403: 'Forbidden, authentication or authorization failure',
        404: 'Not Found, Resource doesnt exist',
        405: 'Method not allowed',
        406: 'Not Acceptable, Accept headers are not satisfiable',
        409: 'The request could not be completed due to a',
        422: 'Unprocessable Entity, Semantically invalid content on a POST',
        500: 'Internal Server Error',
        503: 'Service Unavailable'
    }

    def __init__(self, params=None):
        super(ApiBase, self).__init__()
        self.logger = Log.getLogger(str(self.__module__))
        self.methodReleaseRequirement = []
        self.session = requests.Session()
        self.updateSession = 'no'

    def can(self, methodName):
        """
        Check if methodName exist, return reference of the method if it exist

        Args:
             methodName (str) :: name of method
        """
        dev = self.getDevice()
        if not dev:
            if hasattr(self, methodName):
                return eval("self."+methodName)
            else:
                return
        if methodName not in self.methodReleaseRequirement:
            if hasattr(self, methodName):
                return eval("self."+methodName)
            else:
                return
        if hasattr(self, methodName):
            return eval("self."+methodName)
        else:
            return

    def _convertJsonListToTable(self, jsonList):
        """
        Convert json list to table
        """
        # calculate column width
        headers = self._calculateColumnWidth(jsonList)
        textString = "----------Title----------\n"
        pattern = '{0:{width}s}'

        # format headers
        for name, width in headers.items():
            textString = textString + pattern.format(name, width=width)

        # print split
        textString = textString + "\n"
        for name,width in headers.items():
            split = '_'*(width-4)
            textString = textString + pattern.format(split, width=width)

        # format values
        for item in jsonList:
            textString = textString + "\n"
            for name,width in headers.items():
                textString = textString + pattern.format(str(item.get(name)), width=width)
        return textString + "\n"

    def _calculateColumnWidth(self, jsonList):
        """
        Calculate table column width according to json's key-value
        """
        headers = {}
        if not isinstance(jsonList, list):
            return headers
        # At least 5 chars for each column, in the commonParser
        minHeaderWidth = 5
        fixedSpaceWidth = 4
        for json in jsonList:
            for key,value in json.items():
                valueLength = len(str(value)) + fixedSpaceWidth
                if key in headers.keys():
                    headers[key] = max(valueLength, headers[key])
                else:
                    keyLength = len(str(key)) + fixedSpaceWidth
                    headers[key] = max(keyLength, valueLength, minHeaderWidth+fixedSpaceWidth)
        return headers

    def _convertDictItemsToJson(self, params):
        """
        Convert dict type parameters in given Http parameters to json type
        """
        for key,value in params.items():
            if key.lower() not in ['data', 'params']:
                continue
            if isinstance(value, dict):
                 params[key] = json.dumps(value)
        return params

    def _logRequest(self, method=None, url=None, params=None):
        """
        Log out user's request parameters
        """
        msg = 'Rest request. method: %s, url:%s, params:%s'%(method, url, params)
        self.logger.cmd(str(msg))

    def _logResponse(self, response):
        """
        Log out response message according to response status code

        1xx : Informational
        2xx : Success
        3xx : Redirection
        4xx : Client Error
        5xx : Server Error
        """
        if not self.isResponseOK(response.status_code):
            msg='Rest response error.Status code: %s, elapsed:%s, message:%s'%(response.status_code,
                                                                               response.elapsed,
                                                                               self.handleHttpErrorCode(response.status_code))
            self.logger.error(str(msg))
        else:
            # Circumventing a problem with a download file interface
            if response.text.find('{') < 0:
                msg = 'Rest response ok. status code: %s, elapsed: %s, message: %s'%(response.status_code,
                                                                                     response.elapsed,
                                                                                     "This interface is used to download file, no json response data")
            else:
                msg = 'Rest response ok. Status code: %s, elapsed: %s, message: %s'%(response.status_code,
                                                                                     response.elapsed,
                                                                                     response.text)
                msg = msg.encode('utf-8').replace('. ', '.')
                self.logger.debug(str(msg))

    def isResponseOK(self, status_code):
        return status_code == requests.codes.ok

    def convertJsonToTable(self, jsonObj):
        """
        Convert json object to table text string

        Args:
            jsonObj (list) :: Json list to be convert

        Returns:
              A pretty formatted table text string
        """
        jsonList = jsonObj
        if isinstance(jsonObj, dict):
            jsonList = [jsonObj]

        # json is an array means it contains many tables
        if len(jsonList) > 0:
            if not all(isinstance(x, dict) for x in jsonList):
                raise InvalidParamException('Can not deal with json object which contains array, data:%s'%(json))
            return self._convertJsonListToTable(jsonList)
        else:
            return []

    def encodeJsonToUtf8(self, unicodeJson):
        """
        Convert unicode json encoding to utf-8
        """
        if isinstance(unicodeJson, dict):
            return {self.encodeJsonToUtf8(key):self.encodeJsonToUtf8(value) for key, value in unicodeJson.iteritems()}
        elif isinstance(unicodeJson, list):
            return [self.encodeJsonToUtf8(item) for item in unicodeJson]
        elif isinstance(unicodeJson, unicode):
            return unicodeJson.encode('utf-8')\
                .replace('(', '(')\
                .replace(')', ')')\
                .replace('&gt;', '>')\
                .replace('&lt;', '<')\
                .replace('&', '&')\
                .replace('\r', '')\
                .replace('\n', '')
        else:
            return unicodeJson

    def request(self, method, url, **kwargs):
        """
        Make a Http request according to given method

        Args:
             method (str) :: Http method, values: get/post/put/delete
             url (str) :: url for the request
             kwargs (dict) :: (Optional) parameters

        Returns:
              Http response (response) :: a response object
              usage :
                  r.ok (bool) :: whether request is ok, return True or False
                  r.status_code (int) :: Http response code
                  r.elapsed (time) :: request used time
                  r.json (json) :: response content as json format
                  r.text (str) :: response content as text string format
        """
        kwargs['verify'] = False
        kwargs = self._convertDictItemsToJson(kwargs)
        method = str(method).lower()

        def sendRequest():
            self._logRequest(method, url, kwargs)
            if method == 'get':
                r = self.session.get(url, **kwargs)
            elif method == 'post':
                r = self.session.post(url, **kwargs)
            elif method == 'put':
                r = self.session.put(url, **kwargs)
            elif method == 'delete':
                r = self.session.delete(url, **kwargs)
            else:
                raise InvalidParamException("RestBase not implement %s method"%(method))

            self._logResponse(r)
            return r
        try:
            result = sendRequest()
        except:
            self.logger.info('send resquest fail, retry...')
            result = sendRequest()
        return result

    def handleHttpErrorCode(self, statusCode):
        """
        Return error message according to http status code
        """
        statusCode = int(statusCode)
        if self.HttpErrorCode.has_key(statusCode):
            return self.HttpErrorCode[statusCode]
        else:
            return "Non-defined Error"

    def getHeaders(self):
        """
        Get restful request headers
        """
        return self.session.headers

    validateParam(params=dict)
    def updateHeaders(self, params):
        """
        Update restful request headers

        Args:
             params (dict) :: Http header options.
                              more info (wikipedia, List of HTTP header fields)

        """
        self.session.headers.update(params)

    def changeUpdateSession(self, updateSession='no'):
        """
        Update the value of the property updateSession

        Args:
             updateSession type (str) [yes/no] :: whether to automatically log in again when encountering a session
                                                  timeout error
        """
        if not isinstance(updateSession, str):
            raise UniAutosException('Parameter updateSession must be str, please check')
        self.updateSession = updateSession.lower()






