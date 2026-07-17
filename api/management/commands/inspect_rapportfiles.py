from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Print raw DB value of RapportFile.fichier and the .url produced by the storage backend'

    def handle(self, *args, **options):
        # 1. Raw value straight from the database — no storage backend involved
        with connection.cursor() as cursor:
            cursor.execute('SELECT id, rapport_id, fichier FROM api_rapportfile ORDER BY id DESC LIMIT 10')
            rows = cursor.fetchall()

        self.stdout.write('=== RAW DATABASE VALUES (api_rapportfile.fichier) ===')
        for row in rows:
            self.stdout.write(f'  id={row[0]}  rapport_id={row[1]}  fichier={row[2]!r}')

        # 2. Value returned by the storage backend (.name and .url)
        self.stdout.write('')
        self.stdout.write('=== STORAGE BACKEND VALUES (.name / .url) ===')
        from api.models import RapportFile
        for rf in RapportFile.objects.order_by('-id')[:10]:
            name = rf.fichier.name if rf.fichier else None
            try:
                url = rf.fichier.url if rf.fichier else None
            except Exception as e:
                url = f'ERROR: {e}'
            self.stdout.write(f'  id={rf.id}  .name={name!r}  .url={url!r}')
