import launchspace
import logging
import json
import os
import shutil
import subprocess
import sys
import threading
import git_utils

GROWDATA_DIR = os.getenv('GROWDATA_DIR', '/tmp/growdata')


class Builder(object):

  def __init__(self, ident, build_dir, branch, pod_dir):
    self.ident = ident
    self.build_dir = build_dir
    self.pod_dir = pod_dir
    self.branch = branch
    self.gs_session = launchspace.GoogleStorageSigningSession()
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
    version = '0.0.29'
    path = os.path.join(root, version, 'grow')
    return path

  @classmethod
  def run(cls, ident, repo_dir, branch):
    builder = cls.create(ident, repo_dir, branch)
    builder.upload()

  @classmethod
  def create(cls, ident, repo_dir, branch):
    work_dir = os.path.join(GROWDATA_DIR, 'work', ident, branch)
    if not os.path.exists(work_dir):
      os.makedirs(work_dir)

    # Clone the branch into the pod directory.
    pod_dir = os.path.join(work_dir, 'pod')
    if os.path.exists(pod_dir):
      shutil.rmtree(pod_dir)
    subprocess.call(['/usr/bin/git', 'clone', '-b', branch, repo_dir, pod_dir])

    # Build the pod into the build directory.
    build_dir = os.path.join(work_dir, 'build')
    print 'Building to: {}...'.format(build_dir)
    growsdk = cls.get_growsdk_path()
    if not os.path.exists(build_dir):
      os.makedirs(build_dir)
    subprocess.call([growsdk, 'build', '--dot_grow_dir', pod_dir, build_dir])

    return cls(ident=ident, build_dir=build_dir, branch=branch, pod_dir=pod_dir)

  def upload(self):
    fileset = {
        'name': self.branch,
        'project': {'ident': self.ident},
    }
    paths_to_contents = self.get_paths_to_contents_from_build(self.build_dir)

    sign_requests_request = self.gs_session.create_sign_requests_request(
        fileset, paths_to_contents)
    resp = self.launchspace.rpc('filesets.sign_requests', sign_requests_request)
    if 'signed_requests' not in resp:
      print 'Nothing to upload.'
      return

    if os.getenv('SERVER_SOFTWARE') == 'Production':
      self.upload_build(resp['signed_requests'], paths_to_contents)
      preview_url = resp['fileset']['url']
      print 'Preview at: {}'.format(preview_url)

    items = git_utils.get_formatted_log_items(self.pod_dir, branch=self.branch)
    stats = json.load(open(os.path.join(self.build_dir, '.grow', 'stats.json')))
    resources = git_utils.get_resources(os.path.join(self.build_dir, '.grow', 'index.yaml'))
    resp = self.launchspace.rpc('filesets.finalize', {
        'fileset': {
            'ident': resp['fileset']['ident'],
            'resources': resources,
            'log': {'items': items},
            'stats': stats,
        },
    })


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

  def get_paths_to_contents_from_build(self, build_dir):
    paths_to_contents = {}
    for pre, _, files in os.walk(build_dir):
      for f in files:
        path = os.path.join(pre, f)
        fp = open(path)
        path = path.replace(build_dir, '')
        if not path.startswith('/'):
          path = '/{}'.format(path)
        content = fp.read()
        fp.close()
        if isinstance(content, unicode):
          content = content.encode('utf-8')
        paths_to_contents[path] = content
    return paths_to_contents
