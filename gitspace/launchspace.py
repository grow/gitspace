import json
import requests


class Error(Exception):
  pass


class Launchspace(object):

  def __init__(self, host='growlaunches.com'):
    self.host = host

  def rpc(self, path, body=None):
    if body is None:
      body = {}
    headers = {'Content-Type': 'application/json'}
    url = 'http://{}/_api/{}'.format(self.host, path)
    resp = requests.post(url, data=json.dumps(body), headers=headers)
    if not (resp.status_code >= 200 and resp.status_code < 205):
      raise Error(resp.text)
    return resp.json()
