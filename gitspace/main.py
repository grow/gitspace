from dulwich import repo
from gitspace import git_http_backend
from gitspace import launchspace
import os


ROOT = os.getenv('GROWDATA_DIR', '/tmp/growdata')
LAUNCHSPACE_HOST = os.getenv('LAUNCHSPACE_HOST', 'localhost:8080')
REPOS_ROOT = os.path.join(ROOT, 'repos')


class Error(Exception):
  pass


class NotFoundError(Error):
  pass


class GitBackendApplication(object):

  def __init__(self):
    self.environ = None
    self.start_response = None

  def error(self, message):
    self.start_response('404', [('Content-Type', 'text/plain'),])
    return [str(message)]

  def __call__(self, environ, start_response):
    self.environ = environ
    self.start_response = start_response

    path = environ['PATH_INFO']
    assert '..' not in path
    path = path.lstrip('/')
    if path.endswith('.git'):
      path = path[:-4]

    owner_nickname, project_nickname, remainder = environ['PATH_INFO'].lstrip('/').split('/', 2)

    ls = launchspace.Launchspace(host=LAUNCHSPACE_HOST)
    try:
      resp = ls.rpc('projects.get', {
          'project': {
              'nickname': project_nickname,
              'owner': {'nickname': owner_nickname}
          }
      })
    except launchspace.RpcError as e:
      return self.error(e['error_message'])

    ident = str(resp['project']['ident'])
    path = os.path.join(REPOS_ROOT, ident)

    environ['PATH_TRANSLATED'] = path + '/.git'
    environ['PATH_INFO'] = '/' + remainder

    try:
      os.makedirs(path)
      repo.Repo.init_bare(path)
    except OSError:
      pass

    status_line, headers, response_generator = git_http_backend.wsgi_to_git_http_backend(
        environ, git_project_root=path)
    start_response(status_line, headers)
    return response_generator


application = GitBackendApplication()
