import launchspace
import mimetypes
import base64
import md5
import os
import requests
import threading


class GoogleStorageSigningSession(object):

  @staticmethod
  def create_unsigned_request(verb, path, content=None):
    req = {
      'path': path,
      'verb': verb,
    }
    if verb == 'PUT':
      if path.endswith('/'):
        mimetype = 'text/html'
      else:
        mimetype = mimetypes.guess_type(path)[0]
        mimetype = mimetype or 'application/octet-stream'
      md5_digest = base64.b64encode(md5.new(content).digest())
      req['headers'] = {}
      req['headers']['content_length'] = str(len(content))
      req['headers']['content_md5'] = md5_digest
      req['headers']['content_type'] = mimetype
    return req

  def create_sign_requests_request(self, fileset, paths_to_contents):
    unsigned_requests = []
    for path, content in paths_to_contents.iteritems():
      req = self.create_unsigned_request('PUT', path, content)
      unsigned_requests.append(req)
    return {
        'fileset': fileset,
        'unsigned_requests': unsigned_requests,
    }

  @staticmethod
  def execute_signed_upload(signed_request, content):
    req = signed_request
    params = {
        'GoogleAccessId': req['params']['google_access_id'],
        'Signature': req['params']['signature'],
        'Expires': req['params']['expires'],
    }
    headers = {
        'Content-Type': req['headers']['content_type'],
        'Content-MD5': req['headers']['content_md5'],
        'Content-Length': req['headers']['content_length'],
    }
    resp = requests.put(req['url'], params=params, headers=headers, data=content)
    if not (resp.status_code >= 200 and resp.status_code < 205):
      raise Exception(resp.text)
    return resp


class Builder(object):

  def __init__(self, root, branch, project, owner):
    self.root = root
    self.branch = branch
    self.project = project
    self.owner = owner
    self.gs_session = GoogleStorageSigningSession()
    self.launchspace = launchspace.Launchspace()

  def create_fileset(self):
    fileset = {
        'name': self.branch,
        'project': {
            'nickname': self.project,
            'owner': {'nickname': self.owner}
        },
    }
    paths_to_contents = self.get_paths_to_contents_from_build(self.root)
    print 'Signing requests for {} files.'.format(len(paths_to_contents))
    sign_requests_request = self.gs_session.create_sign_requests_request(
        fileset, paths_to_contents)
    resp = self.launchspace.rpc('filesets.sign_requests', sign_requests_request)
    self.upload_build(resp['signed_requests'], paths_to_contents)

  def upload_build(self, signed_requests, paths_to_contents):
    # TODO(jeremydw): Thread pool.
    threads = []
    for req in signed_requests:
      file_path = req['path']
      thread = threading.Thread(
          target=self.gs_session.execute_signed_upload,
          args=(req, paths_to_contents[file_path]))
      threads.append(thread)
      print 'Uploading {}'.format(file_path)
      thread.start()
    for thread in threads:
      thread.join()

  def get_paths_to_contents_from_build(self, root):
    paths_to_contents = {}
    for root, _, files in os.walk(root):
      for f in files:
        path = os.path.join(root, f)
        fp = open(path)
        path = path.replace(root, '')
        if not path.startswith('/'):
          path = '/{}'.format(path)
        content = fp.read()
        fp.close()
        if isinstance(content, unicode):
          content = content.encode('utf-8')
        paths_to_contents[path] = content
    return paths_to_contents
