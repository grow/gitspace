import logging
import os
from dulwich import errors
from dulwich import web
from dulwich import repo
from dulwich import server


ROOT = os.getenv('GROWDATA_DIR')
GIT_ROOT = os.path.join(ROOT, 'repos')


def setup():
  if not os.path.exists(GIT_ROOT):
    os.makedirs(GIT_ROOT)
    logging.info('Creating directory: {}'.format(GIT_ROOT))


class Backend(server.Backend):

  @classmethod
  def open_repository(cls, path):
    assert '..' not in path
    path = path.lstrip('/')
    path = path.rstrip('.git')
    path = os.path.join(GIT_ROOT, path)
    try:
      return repo.Repo(path)
    except errors.NotGitRepository:
      os.makedirs(path)
      return repo.Repo.init_bare(path)


def get_git_app(environ):
  return web.HTTPGitApplication(Backend())


def repo_application():
  def middleware(environ, start_response):
    git_app = get_git_app(environ)
    return git_app(environ, start_response)
  return middleware


application = repo_application()
