import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent / 'smartbiz'

sys.path.insert(0, str(PROJECT_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbiz.settings')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
