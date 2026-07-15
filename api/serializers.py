"""
api/serializers.py  (version complète avec pointage)
=====================================================
"""
from rest_framework import serializers
from .models import (
    Utilisateur, Chantier, Tache, Ouvrier,
    Notification, Rapport, Facture, RapportFile,
    AssignationPointeur, Pointage,
)


# ── Utilisateur ───────────────────────────────────────────────────
class UtilisateurSerializer(serializers.ModelSerializer):
    role_label  = serializers.CharField(source='get_role_display', read_only=True)
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model  = Utilisateur
        fields = ['id', 'email', 'prenom', 'nom', 'nom_complet',
                  'telephone', 'role', 'role_label', 'is_active', 'date_creation']
        read_only_fields = ['id', 'date_creation']

    def get_nom_complet(self, obj):
        return obj.get_nom_complet()


class UtilisateurCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model  = Utilisateur
        fields = ['email', 'prenom', 'nom', 'telephone', 'role', 'password']

    def create(self, validated_data):
        pwd  = validated_data.pop('password')
        user = Utilisateur(**validated_data)
        user.set_password(pwd)
        user.save()
        return user


class UtilisateurSimpleSerializer(serializers.ModelSerializer):
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model  = Utilisateur
        fields = ['id', 'nom_complet', 'role']

    def get_nom_complet(self, obj):
        return obj.get_nom_complet()


# ── Tâche ─────────────────────────────────────────────────────────
class TacheSerializer(serializers.ModelSerializer):
    statut_label    = serializers.CharField(source='get_statut_display',   read_only=True)
    priorite_label  = serializers.CharField(source='get_priorite_display', read_only=True)
    chef_equipe_nom = serializers.SerializerMethodField()

    class Meta:
        model  = Tache
        fields = ['id', 'chantier', 'titre', 'description',
                  'statut', 'statut_label', 'priorite', 'priorite_label',
                  'chef_equipe', 'chef_equipe_nom', 'date_creation']

    def get_chef_equipe_nom(self, obj):
        return obj.chef_equipe.get_nom_complet() if obj.chef_equipe else None


# ── Chantier ──────────────────────────────────────────────────────
class ChantierListSerializer(serializers.ModelSerializer):
    statut_label      = serializers.CharField(source='get_statut_display', read_only=True)
    avancement        = serializers.ReadOnlyField()
    nombre_taches     = serializers.ReadOnlyField()
    nombre_ouvriers   = serializers.ReadOnlyField()
    chef_projet_nom   = serializers.SerializerMethodField()
    chef_chantier_nom = serializers.SerializerMethodField()

    class Meta:
        model  = Chantier
        fields = ['id', 'nom', 'lieu', 'statut', 'statut_label',
                  'budget', 'date_debut', 'date_fin',
                  'avancement', 'nombre_taches', 'nombre_ouvriers',
                  'chef_projet', 'chef_projet_nom',
                  'chef_chantier', 'chef_chantier_nom',
                  'date_creation']

    def get_chef_projet_nom(self, obj):
        return obj.chef_projet.get_nom_complet() if obj.chef_projet else None

    def get_chef_chantier_nom(self, obj):
        return obj.chef_chantier.get_nom_complet() if obj.chef_chantier else None


class ChantierDetailSerializer(ChantierListSerializer):
    taches = TacheSerializer(many=True, read_only=True)

    class Meta(ChantierListSerializer.Meta):
        fields = ChantierListSerializer.Meta.fields + ['description', 'taches']


class ChantierCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Chantier
        fields = ['nom', 'lieu', 'description', 'budget',
                  'statut', 'date_debut', 'date_fin',
                  'chef_projet', 'chef_chantier']

    def validate(self, attrs):
        if attrs.get('date_debut') and attrs.get('date_fin'):
            if attrs['date_fin'] < attrs['date_debut']:
                raise serializers.ValidationError(
                    {'date_fin': 'La date de fin doit être après la date de début.'}
                )
        return attrs


# ── Ouvrier ───────────────────────────────────────────────────────
class OuvrierSerializer(serializers.ModelSerializer):
    fonction_label = serializers.CharField(source='get_fonction_display', read_only=True)
    chantier_nom   = serializers.SerializerMethodField()

    class Meta:
        model  = Ouvrier
        fields = ['id', 'prenom', 'nom', 'cin', 'telephone',
                  'fonction', 'fonction_label', 'disponible',
                  'prix_heure',                          # ← NOUVEAU
                  'chantier', 'chantier_nom', 'pointeur',
                  'date_arrivee', 'date_creation']
        read_only_fields = ['id', 'date_arrivee', 'date_creation', 'pointeur']

    def get_chantier_nom(self, obj):
        return obj.chantier.nom if obj.chantier else None


# ── Notification ──────────────────────────────────────────────────
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['id', 'titre', 'message', 'lue', 'date_creation']


    def get_fichier_nom(self, obj):
        return obj.fichier_nom


class RapportFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RapportFile
        fields = ['id', 'fichier', 'fichier_nom', 'date_creation']


# ── Rapport ───────────────────────────────────────────────────────
class RapportSerializer(serializers.ModelSerializer):
    chantier_nom = serializers.CharField(source='chantier.nom', read_only=True)
    cree_par_nom = serializers.CharField(source='cree_par.get_nom_complet', read_only=True)
    # ── NOUVEAU : fichier joint ──────────────────────────
    fichier      = serializers.FileField(required=False, allow_null=True)
    fichier_nom  = serializers.SerializerMethodField()
    # ── MULTIPLES FICHIERS ───────────────────────────────
    fichiers     = RapportFileSerializer(source='attachments', many=True, read_only=True)

    class Meta:
        model  = Rapport
        fields = ['id', 'chantier', 'chantier_nom', 'titre', 'contenu',
                  'cree_par_nom', 'date_creation', 'fichier', 'fichier_nom', 'fichiers']

    def get_fichier_nom(self, obj):
        return obj.fichier_nom


# ── Facture ───────────────────────────────────────────────────────
class FactureSerializer(serializers.ModelSerializer):
    chantier_nom = serializers.CharField(source='chantier.nom', read_only=True)
    cree_par_nom = serializers.CharField(source='cree_par.get_nom_complet', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    fichier      = serializers.FileField(required=False, allow_null=True)
    fichier_nom  = serializers.SerializerMethodField()

    class Meta:
        model  = Facture
        fields = ['id', 'chantier', 'chantier_nom', 'numero', 'description',
                  'montant', 'statut', 'statut_label', 'cree_par_nom', 'date_creation',
                  'fichier', 'fichier_nom']

    def get_fichier_nom(self, obj):
        return obj.fichier_nom


# ══════════════════════════════════════════════════════════════════
# NOUVEAUX SERIALIZERS — ASSIGNATION & POINTAGE
# ══════════════════════════════════════════════════════════════════

class AssignationPointeurSerializer(serializers.ModelSerializer):
    pointeur_nom  = serializers.CharField(source='pointeur.get_nom_complet', read_only=True)
    chantier_nom  = serializers.CharField(source='chantier.nom', read_only=True)

    class Meta:
        model  = AssignationPointeur
        fields = ['id', 'pointeur', 'pointeur_nom',
                  'chantier', 'chantier_nom', 'date_assignation']
        read_only_fields = ['id', 'date_assignation']

    def validate_pointeur(self, value):
        if value.role != 'pointeur':
            raise serializers.ValidationError(
                "L'utilisateur sélectionné n'a pas le rôle pointeur."
            )
        return value


class PointageSerializer(serializers.ModelSerializer):
    ouvrier_nom   = serializers.CharField(source='ouvrier.get_nom_complet', read_only=True)
    chantier_nom  = serializers.CharField(source='chantier.nom', read_only=True)
    pointeur_nom  = serializers.SerializerMethodField()
    ouvrier_fonction_label = serializers.CharField(source='ouvrier.get_fonction_display', read_only=True)

    class Meta:
        model  = Pointage
        fields = [
            'id', 'ouvrier', 'ouvrier_nom', 'ouvrier_fonction_label',
            'chantier', 'chantier_nom',
            'pointeur', 'pointeur_nom',
            'date', 'heure_debut', 'heure_fin',
            'prix_heure', 'total_heures', 'total_prix',
            'date_creation',
        ]
        read_only_fields = [
            'id', 'total_heures', 'total_prix', 'date_creation',
            'pointeur',
        ]

    def get_pointeur_nom(self, obj):
        return obj.pointeur.get_nom_complet() if obj.pointeur else None

    def validate(self, attrs):
        ouvrier  = attrs.get('ouvrier')
        chantier = attrs.get('chantier')
        date     = attrs.get('date')

        # 1. Vérifier que l'ouvrier appartient bien au chantier
        if ouvrier and chantier:
            if ouvrier.chantier_id != chantier.id:
                raise serializers.ValidationError(
                    "Cet ouvrier n'appartient pas à ce chantier."
                )

        # 2. Vérifier doublon (exclure l'instance en cours si update)
        if ouvrier and date:
            qs = Pointage.objects.filter(ouvrier=ouvrier, date=date)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"Un pointage existe déjà pour {ouvrier.get_nom_complet()} le {date}."
                )

        return attrs
