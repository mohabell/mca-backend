from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur, Chantier, Tache, Ouvrier, Notification, Rapport, Facture

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    model = Utilisateur
    list_display  = ['email', 'prenom', 'nom', 'role', 'is_active']
    list_filter   = ['role', 'is_active']
    search_fields = ['email', 'prenom', 'nom']
    ordering      = ['nom']
    # fieldsets = (
    #     (None, {'fields': ('email', 'password')}),
    #     ('Informations', {'fields': ('prenom', 'nom', 'telephone', 'role')}),
    #     ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    # )

    fieldsets = (
    (None, {'fields': ('email', 'password')}),
    ('Informations', {'fields': ('prenom', 'nom', 'telephone', 'role')}),
    ('Firebase', {'fields': ('fcm_token',)}),  # ← AJOUTE CETTE LIGNE
    ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'prenom', 'nom', 'role', 'password1', 'password2')}),
    )

@admin.register(Chantier)
class ChantierAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'lieu', 'statut', 'chef_projet', 'chef_chantier']
    list_filter   = ['statut']
    search_fields = ['nom', 'lieu']

@admin.register(Tache)
class TacheAdmin(admin.ModelAdmin):
    list_display  = ['titre', 'chantier', 'statut', 'priorite', 'chef_equipe']
    list_filter   = ['statut', 'priorite']

@admin.register(Ouvrier)
class OuvrierAdmin(admin.ModelAdmin):
    list_display  = ['prenom', 'nom', 'cin', 'fonction', 'chantier', 'disponible']
    list_filter   = ['fonction', 'disponible']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['destinataire', 'titre', 'lue', 'date_creation']
    list_filter   = ['lue']

@admin.register(Rapport)
class RapportAdmin(admin.ModelAdmin):
    list_display  = ['titre', 'chantier', 'cree_par', 'date_creation']

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display  = ['numero', 'chantier', 'montant', 'statut', 'cree_par']
    list_filter   = ['statut']
