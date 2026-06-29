import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
application = get_wsgi_application()
