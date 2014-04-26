import os
from dulwich import web
from dulwich import repo
from dulwich import server


class Backend(server.Backend):

  @classmethod
  def open_repository(cls, path):
    path = path.lstrip('/')
    return repo.Repo(path)


def get_git_app(environ):
  if environ['REQUEST_METHOD'] == 'GET':
    print environ['PATH_INFO']
  repo.MemoryRepo.init_bare([], {})
  return web.HTTPGitApplication(Backend())


def repo_application():
  def middleware(environ, start_response):
    git_app = get_git_app(environ)
    return git_app(environ, start_response)
  return middleware


app = repo_application()
