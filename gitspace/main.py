import os
from dulwich import web
from dulwich import repo
from dulwich import server


os.environ['GITSPACE_ROOT'] = 'gitroot'


class Backend(server.Backend):

  @classmethod
  def open_repository(cls, path):
    assert '..' not in path
    path = path.lstrip('/')
    path = path.rstrip('.git')
    path = os.path.join(os.getenv('GITSPACE_ROOT', path))
    return repo.Repo(path)


def get_git_app(environ):
  return web.HTTPGitApplication(Backend())


def repo_application():
  def middleware(environ, start_response):
    git_app = get_git_app(environ)
    return git_app(environ, start_response)
  return middleware


application = repo_application()
