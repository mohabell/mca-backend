"""
AJOUTS À api/models.py
======================
Copier ces deux classes à la fin de models.py (après Facture),
et ajouter le champ prix_heure à la classe Ouvrier existante.

── MODIFICATION SUR Ouvrier ──────────────────────────────────
Ajouter dans la classe Ouvrier, après le champ `disponible` :

    prix_heure = models.DecimalField(max_digits=8, decimal_places=2, default=0)

── NOUVELLES CLASSES ─────────────────────────────────────────
"""

from django.db import models


# ══════════════════════════════════════════════════════════════════
# ASSIGNATION POINTEUR → CHANTIER
# ══════════════════════════════════════════════════════════════════

class AssignationPointeur(models.Model):
    """
    Lie un pointeur (utilisateur avec role='pointeur') à un seul chantier.
    Règle : un pointeur = un chantier.
    """
    pointeur = models.OneToOneField(
        'Utilisateur',
        on_delete=models.CASCADE,
        related_name='assignation_chantier',
        limit_choices_to={'role': 'pointeur'},
    )
    # chantier = models.ForeignKey(
    #     'Chantier',
    #     on_delete=models.CASCADE,
    #     related_name='pointeurs_assignes',
    # )
    chantier = models.OneToOneField(
    'Chantier',
    on_delete=models.CASCADE,
    related_name='pointeur_assigne',
    )
    date_assignation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Assignation Pointeur'
        verbose_name_plural = 'Assignations Pointeurs'

    def __str__(self):
        return f"{self.pointeur.get_nom_complet()} → {self.chantier.nom}"


# ══════════════════════════════════════════════════════════════════
# POINTAGE
# ══════════════════════════════════════════════════════════════════

class Pointage(models.Model):
    """
    Enregistre les heures travaillées d'un ouvrier sur un chantier.
    Calcul automatique de total_heures et total_prix dans save().
    Gestion travail de nuit si heure_fin < heure_debut.
    """
    ouvrier    = models.ForeignKey(
        'Ouvrier',
        on_delete=models.CASCADE,
        related_name='pointages',
    )
    chantier   = models.ForeignKey(
        'Chantier',
        on_delete=models.CASCADE,
        related_name='pointages',
    )
    pointeur   = models.ForeignKey(
        'Utilisateur',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='pointages_effectues',
    )

    date        = models.DateField()
    heure_debut = models.TimeField()
    heure_fin   = models.TimeField()

    # Calculés automatiquement dans save()
    total_heures = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_prix   = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Prix heure snapshot au moment du pointage
    prix_heure   = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pointage'
        ordering = ['-date', '-date_creation']
        # Empêcher doublon : même ouvrier + même date
        unique_together = [('ouvrier', 'date')]

    def __str__(self):
        return f"Pointage {self.ouvrier} — {self.date}"

    def save(self, *args, **kwargs):
        from decimal import Decimal
        import datetime

        # ── Snapshot du prix heure de l'ouvrier ──
        if not self.prix_heure and self.ouvrier_id:
            try:
                from api.models import Ouvrier
                self.prix_heure = Ouvrier.objects.get(pk=self.ouvrier_id).prix_heure
            except Exception:
                self.prix_heure = Decimal('0')

        # ── Calcul des heures totales ──
        debut = datetime.datetime.combine(datetime.date.today(), self.heure_debut)
        fin   = datetime.datetime.combine(datetime.date.today(), self.heure_fin)

        if self.heure_fin < self.heure_debut:
            # Travail de nuit : on ajoute 24h à la fin
            fin += datetime.timedelta(days=1)

        delta = fin - debut
        heures = Decimal(str(round(delta.total_seconds() / 3600, 2)))

        self.total_heures = heures
        self.total_prix   = round(heures * self.prix_heure, 2)

        super().save(*args, **kwargs)
