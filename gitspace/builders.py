import base64
import launchspace
import logging
import md5
import mimetypes
import os
import requests
import subprocess
import sys
import threading

GROWDATA_DIR = os.getenv('GROWDATA_DIR', '/tmp/growdata')


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

  def __init__(self, ident, root, branch):
    self.ident = ident
    self.root = root
    self.branch = branch
    self.gs_session = GoogleStorageSigningSession()
    self.launchspace = launchspace.Launchspace()

  @classmethod
  def get_growsdk_path(cls):
    root = os.path.join(os.path.dirname(__file__), 'growsdk')
    if sys.platform.startswith('linux'):
      platform = 'linux'
    elif sys.platform == 'darwin':
      platform = 'mac'
    else:
      raise ValueError('Platform unsupported.')
    root = os.path.join(root, platform)
    # TODO: Use version of Grow SDK that the pod is targeting.
    version = '0.0.28'
    path = os.path.join(root, version, 'grow')
    return path

  @classmethod
  def run(cls, ident, repo_dir, branch):
    builder = cls.create(ident, repo_dir, branch)
    builder.upload()

  @classmethod
  def create(cls, ident, repo_dir, branch):
    work_dir = os.path.join(GROWDATA_DIR, 'work', ident)
    if not os.path.exists(work_dir):
      os.makedirs(work_dir)

    # Clone the branch into the pod directory.
    pod_dir = os.path.join(work_dir, 'pod')
    if not os.path.exists(pod_dir):
      os.makedirs(pod_dir)
    subprocess.call(['/usr/bin/git', 'clone', '-b', branch, repo_dir, pod_dir])

    # Build the pod into the build directory.
    build_dir = os.path.join(work_dir, 'build')
    print 'Building to: {}...'.format(build_dir)
    growsdk = cls.get_growsdk_path()
    if not os.path.exists(build_dir):
      os.makedirs(build_dir)
    subprocess.call([growsdk, 'build', pod_dir, build_dir])

    return cls(ident=ident, root=build_dir, branch=branch)

  def upload(self):
    fileset = {
        'name': self.branch,
        'project': {'ident': self.ident},
    }
    paths_to_contents = self.get_paths_to_contents_from_build(self.root)

    print 'Signing requests for {} files.'.format(len(paths_to_contents))
    sign_requests_request = self.gs_session.create_sign_requests_request(
        fileset, paths_to_contents)
    resp = self.launchspace.rpc('filesets.sign_requests', sign_requests_request)
    self.upload_build(resp['signed_requests'], paths_to_contents)
    preview_url = resp['fileset']['url']
    print 'Preview at: {}'.format(preview_url)

  def upload_build(self, signed_requests, paths_to_contents):
    # TODO(jeremydw): Thread pool.
    print 'Uploading files...'
    threads = []
    for req in signed_requests:
      file_path = req['path']
      thread = threading.Thread(
          target=self.gs_session.execute_signed_upload,
          args=(req, paths_to_contents[file_path]))
      threads.append(thread)
      logging.info('Uploading: {}'.format(file_path))
      thread.start()
    for thread in threads:
      thread.join()

  def get_paths_to_contents_from_build(self, root):
    paths_to_contents = {}
    for pre, _, files in os.walk(root):
      for f in files:
        path = os.path.join(pre, f)
        fp = open(path)
        path = path.replace(pre, '')
        if not path.startswith('/'):
          path = '/{}'.format(path)
        content = fp.read()
        fp.close()
        if isinstance(content, unicode):
          content = content.encode('utf-8')
        paths_to_contents[path] = content
    return paths_to_contents
