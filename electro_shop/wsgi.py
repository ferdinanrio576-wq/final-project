import os
from pathlib import Path
from shutil import copy2
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'electro_shop.settings')

if os.environ.get('VERCEL'):
    base_dir = Path(__file__).resolve().parent.parent
    source_db = base_dir / 'db.sqlite3'
    target_db = Path('/tmp/db.sqlite3')
    if source_db.exists() and not target_db.exists():
        target_db.parent.mkdir(parents=True, exist_ok=True)
        copy2(source_db, target_db)
        
    source_media = base_dir / 'media'
    target_media = Path('/tmp/media')
    if source_media.exists() and not target_media.exists():
        import shutil
        shutil.copytree(source_media, target_media)

application = get_wsgi_application()

app = application
