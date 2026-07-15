"""
api/models.py  (version complète avec pointage)
================================================
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ══════════════════════════════════════════════════════════════════
# UTILISATEUR PERSONNALISÉ
# ══════════════════════════════════════════════════════════════════

class UtilisateurManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', 'admin')
        return self.create_user(email, password, **extra)


class Utilisateur(AbstractBaseUser, PermissionsMixin):

    ROLES = [
        ('admin',         'Administrateur'),
        ('chef_projet',   'Chef de Projet'),
        ('chef_chantier', 'Chef de Chantier'),
        ('chef_equipe',   "Chef d'Équipe"),
        ('pointeur',      'Pointeur'),
    ]

    email     = models.EmailField(unique=True)
    prenom    = models.CharField(max_length=100)
    nom       = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    role      = models.CharField(max_length=20, choices=ROLES, default='pointeur')
    fcm_token = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    objects = UtilisateurManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['prenom', 'nom']

    class Meta:
        verbose_name = 'Utilisateur'
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.get_role_display()})"

    def get_nom_complet(self):
        return f"{self.prenom} {self.nom}"

    @property
    def is_admin(self):         return self.role == 'admin' or self.is_superuser
    @property
    def is_chef_projet(self):   return self.role == 'chef_projet'
    @property
    def is_chef_chantier(self): return self.role == 'chef_chantier'
    @property
    def is_chef_equipe(self):   return self.role == 'chef_equipe'
    @property
    def is_pointeur(self):      return self.role == 'pointeur'


# ══════════════════════════════════════════════════════════════════
# CHANTIER
# ══════════════════════════════════════════════════════════════════

class Chantier(models.Model):

    STATUTS = [
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('termine',  'Terminé'),
        ('suspendu', 'Suspendu'),
    ]

    nom         = models.CharField(max_length=200)
    lieu        = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')
    budget      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    statut      = models.CharField(max_length=20, choices=STATUTS, default='planifie')

    date_debut  = models.DateField(null=True, blank=True)
    date_fin    = models.DateField(null=True, blank=True)

    chef_projet   = models.ForeignKey(
        Utilisateur, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='chantiers_en_tant_que_chef_projet',
        limit_choices_to={'role': 'chef_projet'},
    )
    chef_chantier = models.ForeignKey(
        Utilisateur, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='chantiers_en_tant_que_chef_chantier',
        limit_choices_to={'role': 'chef_chantier'},
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Chantier'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.nom} [{self.get_statut_display()}]"

    @property
    def avancement(self):
        total = self.taches.count()
        if total == 0:
            return 0
        faites = self.taches.filter(statut='fait').count()
        return round(faites / total * 100)

    @property
    def nombre_taches(self):
        return self.taches.count()

    @property
    def nombre_ouvriers(self):
        return self.ouvriers.count()


# ══════════════════════════════════════════════════════════════════
# TÂCHE
# ══════════════════════════════════════════════════════════════════

class Tache(models.Model):

    STATUTS = [
        ('a_faire',  'À faire'),
        ('en_cours', 'En cours'),
        ('fait',     'Terminée'),
    ]

    PRIORITES = [
        ('basse',   'Basse'),
        ('moyenne', 'Moyenne'),
        ('haute',   'Haute'),
        ('urgente', 'Urgente 🔴'),
    ]

    chantier    = models.ForeignKey(Chantier, on_delete=models.CASCADE, related_name='taches')
    titre       = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    statut      = models.CharField(max_length=20, choices=STATUTS, default='a_faire')
    priorite    = models.CharField(max_length=10, choices=PRIORITES, default='moyenne')

    chef_equipe = models.ForeignKey(
        Utilisateur, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='taches_assignees',
        limit_choices_to={'role': 'chef_equipe'},
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tâche'
        ordering = ['priorite', '-date_creation']

    def __str__(self):
        return f"{self.titre} [{self.chantier.nom}]"


# ══════════════════════════════════════════════════════════════════
# OUVRIER
# ══════════════════════════════════════════════════════════════════

class Ouvrier(models.Model):

    FONCTIONS = [
        ('macon',       'Maçon'),
        ('electricien', 'Électricien'),
        ('plombier',    'Plombier'),
        ('charpentier', 'Charpentier'),
        ('peintre',     'Peintre'),
        ('ferrailleur', 'Ferrailleur'),
        ('autre',       'Autre'),
    ]

    prenom      = models.CharField(max_length=100)
    nom         = models.CharField(max_length=100)
    cin         = models.CharField(max_length=20, unique=True)
    telephone   = models.CharField(max_length=20, blank=True)
    fonction    = models.CharField(max_length=20, choices=FONCTIONS, default='macon')
    disponible  = models.BooleanField(default=True)

    # ── NOUVEAU : taux horaire de l'ouvrier ──
    prix_heure  = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    chantier = models.ForeignKey(
        Chantier, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='ouvriers',
    )

    pointeur = models.ForeignKey(
        Utilisateur, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='ouvriers_ajoutes',
    )

    date_arrivee  = models.DateField(auto_now_add=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ouvrier'
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.get_fonction_display()})"

    def get_nom_complet(self):
        return f"{self.prenom} {self.nom}"


# ══════════════════════════════════════════════════════════════════
# NOTIFICATION
# ══════════════════════════════════════════════════════════════════

class Notification(models.Model):
    destinataire = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE, related_name='notifications'
    )
    titre   = models.CharField(max_length=200)
    message = models.TextField()
    lue     = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Notif → {self.destinataire} : {self.titre}"


# ══════════════════════════════════════════════════════════════════
# RAPPORT
# ══════════════════════════════════════════════════════════════════

class Rapport(models.Model):
    chantier    = models.ForeignKey(Chantier, on_delete=models.CASCADE, related_name='rapports')
    titre       = models.CharField(max_length=200)
    contenu     = models.TextField()
    cree_par    = models.ForeignKey(
        Utilisateur, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='rapports_crees'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    # ── NOUVEAU : document joint ──────────────────────────
    fichier     = models.FileField(
        upload_to='rapports/%Y/%m/',
        null=True, blank=True,
        verbose_name='Document joint'
    )

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Rapport : {self.titre} [{self.chantier.nom}]"

    @property
    def fichier_nom(self):
        if self.fichier:
            import os
            return os.path.basename(self.fichier.name)
        return None

    def importer_document(self, fichier_file):
        """Attache un document au rapport (ImporterDocument UML)"""
        self.fichier = fichier_file
        self.save(update_fields=['fichier'])

    def modifier_doc(self, fichier_file):
        """Remplace le document existant (ModifierDoc UML)"""
        if self.fichier:
            try:
                import os
                if os.path.isfile(self.fichier.path):
                    os.remove(self.fichier.path)
            except Exception:
                pass
        self.fichier = fichier_file
        self.save(update_fields=['fichier'])


class RapportFile(models.Model):
    rapport = models.ForeignKey(Rapport, on_delete=models.CASCADE, related_name='attachments')
    fichier = models.FileField(upload_to='rapports/%Y/%m/')
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for Rapport {self.rapport_id}"

    @property
    def fichier_nom(self):
        if self.fichier:
            import os
            return os.path.basename(self.fichier.name)
        return ""


# ══════════════════════════════════════════════════════════════════
# FACTURE
# ══════════════════════════════════════════════════════════════════

class Facture(models.Model):
    STATUTS = [
        ('en_attente', 'En attente'),
        ('payee',      'Payée'),
        ('annulee',    'Annulée'),
    ]

    chantier    = models.ForeignKey(Chantier, on_delete=models.CASCADE, related_name='factures')
    numero      = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    montant     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    statut      = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    cree_par    = models.ForeignKey(
        Utilisateur, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='factures_creees'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    # ── NOUVEAU : document joint ──────────────────────────
    fichier     = models.FileField(
        upload_to='factures/%Y/%m/',
        null=True, blank=True,
        verbose_name='Document joint'
    )

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Facture {self.numero} — {self.chantier.nom}"

    @property
    def fichier_nom(self):
        if self.fichier:
            import os
            return os.path.basename(self.fichier.name)
        return None


# ══════════════════════════════════════════════════════════════════
# ASSIGNATION POINTEUR → CHANTIER  ← NOUVEAU
# ══════════════════════════════════════════════════════════════════

class AssignationPointeur(models.Model):
    """
    Lie un pointeur à un seul chantier (OneToOne).
    L'admin assigne, le pointeur voit uniquement ce chantier.
    """
    pointeur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='assignation_chantier',
        limit_choices_to={'role': 'pointeur'},
    )
    chantier = models.ForeignKey(
        Chantier,
        on_delete=models.CASCADE,
        related_name='pointeurs_assignes',
    )
    date_assignation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Assignation Pointeur'
        verbose_name_plural = 'Assignations Pointeurs'

    def __str__(self):
        return f"{self.pointeur.get_nom_complet()} → {self.chantier.nom}"


# ══════════════════════════════════════════════════════════════════
# POINTAGE  ← NOUVEAU
# ══════════════════════════════════════════════════════════════════

class Pointage(models.Model):
    """
    Enregistrement des heures travaillées.
    total_heures et total_prix sont calculés automatiquement dans save().
    Travail de nuit géré si heure_fin < heure_debut.
    """
    ouvrier  = models.ForeignKey(
        Ouvrier, on_delete=models.CASCADE, related_name='pointages'
    )
    chantier = models.ForeignKey(
        Chantier, on_delete=models.CASCADE, related_name='pointages'
    )
    pointeur = models.ForeignKey(
        Utilisateur, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='pointages_effectues'
    )

    date        = models.DateField()
    heure_debut = models.TimeField()
    heure_fin   = models.TimeField()

    # Snapshot du prix heure au moment du pointage
    prix_heure   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    # Calculés automatiquement
    total_heures = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_prix   = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pointage'
        ordering = ['-date', '-date_creation']
        unique_together = [('ouvrier', 'date')]  # un seul pointage par ouvrier par jour

    def __str__(self):
        return f"Pointage {self.ouvrier} — {self.date}"

    def save(self, *args, **kwargs):
        from decimal import Decimal
        import datetime

        # ── Snapshot prix heure depuis l'ouvrier si non renseigné ──
        if not self.prix_heure and self.ouvrier_id:
            try:
                self.prix_heure = Ouvrier.objects.get(pk=self.ouvrier_id).prix_heure
            except Ouvrier.DoesNotExist:
                self.prix_heure = Decimal('0')

        # ── Calcul des heures ──
        debut = datetime.datetime.combine(datetime.date.today(), self.heure_debut)
        fin   = datetime.datetime.combine(datetime.date.today(), self.heure_fin)

        if self.heure_fin < self.heure_debut:
            # Travail de nuit
            fin += datetime.timedelta(days=1)

        delta  = fin - debut
        heures = Decimal(str(round(delta.total_seconds() / 3600, 2)))

        self.total_heures = heures
        self.total_prix   = round(heures * Decimal(str(self.prix_heure)), 2)

        super().save(*args, **kwargs)
