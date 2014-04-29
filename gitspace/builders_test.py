import os
import unittest
import builders

BUILD_ROOT = os.path.join(os.path.dirname(__file__), 'testdata', 'build')


class BuildersTestCase(unittest.TestCase):

  def test(self):
    builder = builders.Builder(
        root=BUILD_ROOT, branch='master', project='test', owner='test')
    builder.create_fileset()


if __name__ == '__main__':
  unittest.main()
