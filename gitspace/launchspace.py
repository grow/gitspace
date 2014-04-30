import os
import json
import requests


HOST = os.getenv('LAUNCHSPACE_HOST', 'growlaunches.com')


class Error(Exception):
  pass


class RpcError(Error):

  def __init__(self, status, data):
    self.status = status
    self.text = data['error_message']
    self.data = data

  def __str__(self):
    return self.text

  def __getitem__(self, name):
    return self.data[name]


class Launchspace(object):

  def __init__(self, host=HOST):
    self.host = host

  def rpc(self, path, body=None):
    if body is None:
      body = {}
    headers = {'Content-Type': 'application/json'}
    url = 'http://{}/_api/{}'.format(self.host, path)
    resp = requests.post(url, data=json.dumps(body), headers=headers)
    if not (resp.status_code >= 200 and resp.status_code < 205):
      data = resp.json()
      raise RpcError(resp.status_code, data=data)
    return resp.json()
