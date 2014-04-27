from gitspace import launchspace
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
    if path.endswith('.git'):
      path = path[:-4]

    owner_nickname, project_nickname = path.split('/')
    ls = launchspace.Launchspace()
    resp = ls.rpc('projects.get', {
        'project': {
            'nickname': project_nickname,
            'owner': {'nickname': owner_nickname}
        }
    })

    ident = resp['project']['ident']
    path = os.path.join(GIT_ROOT, ident)
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
