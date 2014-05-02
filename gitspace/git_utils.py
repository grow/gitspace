import git
import os
os.environ.pop('GIT_DIR', '')


def get_formatted_log_items(root, branch):
  branch = str(branch)
  items = []
  repo = git.Repo(root)
  for item in repo.iter_commits(branch):
    items.append({
        'author': {
            'name': item.author.name,
            'email': item.author.email,
        },
        'commit': item.hexsha,
        'message': item.message,
    })
  return items

