import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent / 'smartbiz'

sys.path.insert(0, str(PROJECT_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbiz.settings')

if os.environ.get('VERCEL') and not os.environ.get('DATABASE_URL'):
    import django
    from django.core.management import call_command

    django.setup()
    call_command('migrate', interactive=False, verbosity=0)

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
