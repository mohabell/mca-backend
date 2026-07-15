"""
api/migrations/0002_prix_heure_assignation_pointage.py
=======================================================
Migration ajoutant :
  - Ouvrier.prix_heure
  - AssignationPointeur
  - Pointage
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [

        # ── 1. Ajouter prix_heure sur Ouvrier ──
        migrations.AddField(
            model_name='ouvrier',
            name='prix_heure',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),

        # ── 2. Créer AssignationPointeur ──
        migrations.CreateModel(
            name='AssignationPointeur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_assignation', models.DateTimeField(auto_now_add=True)),
                ('chantier', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pointeurs_assignes',
                    to='api.chantier',
                )),
                ('pointeur', models.OneToOneField(
                    limit_choices_to={'role': 'pointeur'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignation_chantier',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Assignation Pointeur',
                'verbose_name_plural': 'Assignations Pointeurs',
            },
        ),

        # ── 3. Créer Pointage ──
        migrations.CreateModel(
            name='Pointage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('heure_debut', models.TimeField()),
                ('heure_fin', models.TimeField()),
                ('prix_heure', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_heures', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('total_prix', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('ouvrier', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pointages',
                    to='api.ouvrier',
                )),
                ('chantier', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pointages',
                    to='api.chantier',
                )),
                ('pointeur', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='pointages_effectues',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Pointage',
                'ordering': ['-date', '-date_creation'],
                'unique_together': {('ouvrier', 'date')},
            },
        ),
    ]
