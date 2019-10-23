import urllib
import urllib2
import json

"""
Function: Provide the basic function to operate http request: GET, PUT, POST, DELETE.
"""

def httpGet(url):
    """
    Get http request

    Args:
        url (str) :: http request url

    Returns:
          response (str) :: Http request response
    """
    response = urllib2.urlopen(url)
    return response.read()

def httpPost(url, jsonObject):
    """
    Send post rest request

    Args:
         url        (str)  :: Http post request url
         jsonObject (str)  :: the json object will be post

    Returns:
          response (str)
    """
    headers = {'X-Parse-Application-Id':'someID',
               'X-Parse-REST-API-Key':'someKey',
               'Content-Type':'application/json'}
    jdata = json.dumps(jsonObject)
    req = urllib2.Request(url, jdata, headers)
    response = urllib2.urlopen(req)
    return response.read()

def httpPut(url, jsonObject):
    """
    Send put http request

    Args:
         url        (str)  :: Http put request url
         jsonObject (str)  :: the json object will be put

    Returns:
        None
    """
    request = urllib2.Request(url, jsonObject)
    request.add_header('Content-Type', 'sss/sss')
    request.get_method = lambda:'PUT'
    request = urllib2.urlopen(request)
    return request.read()