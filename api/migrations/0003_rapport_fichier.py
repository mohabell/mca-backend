from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_prix_heure_assignation_pointage'),
    ]

    operations = [
        migrations.AddField(
            model_name='rapport',
            name='fichier',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='rapports/%Y/%m/',
                verbose_name='Document joint'
            ),
        ),
    ]
