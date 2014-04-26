import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import mimetypes

mimetypes.add_type('image/svg+xml', '.svg')
