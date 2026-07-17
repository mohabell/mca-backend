"""
api/views.py  (version complète avec pointage)
===============================================
Ajouts :
  - AssignationPointeurView   : CRUD assignation pointeur→chantier (admin)
  - MonChantierView           : chantier du pointeur connecté
  - PointageListView          : créer/lister les pointages
  - PointageDetailView        : modifier/supprimer un pointage
  - StatsPointageView         : statistiques globales + par chantier
  - BulletinPaieView          : génération PDF bulletin de paie
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Sum, Count, Q
from django.utils import timezone
import datetime

from .serializers import (
    UtilisateurSerializer, UtilisateurCreateSerializer, UtilisateurSimpleSerializer,
    ChantierListSerializer, ChantierDetailSerializer, ChantierCreateSerializer,
    TacheSerializer, OuvrierSerializer,
    NotificationSerializer, RapportSerializer, FactureSerializer,
    AssignationPointeurSerializer, PointageSerializer,
)
from .models import (
    Utilisateur, Chantier, Tache, Ouvrier,
    Notification, Rapport, Facture, RapportFile,
    AssignationPointeur, Pointage,
)


# ──────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────

def ok(data=None, msg=None, code=200):
    body = {'success': True}
    if msg:  body['message'] = msg
    if data is not None: body['data'] = data
    return Response(body, status=code)

def err(msg, code=400):
    return Response({'success': False, 'message': msg}, status=code)

def not_found(msg='Introuvable'):
    return Response({'success': False, 'message': msg}, status=404)

def forbidden(msg='Accès interdit.'):
    return Response({'success': False, 'message': msg}, status=403)


# ══════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return err('Email et mot de passe requis.')

        try:
            user = Utilisateur.objects.get(email=email, is_active=True)
        except Utilisateur.DoesNotExist:
            return err('Email ou mot de passe incorrect.', 401)

        if not user.check_password(password):
            return err('Email ou mot de passe incorrect.', 401)

        refresh = RefreshToken.for_user(user)
        return ok({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user':    UtilisateurSerializer(user).data,
        })


class MeView(APIView):
    def get(self, request):
        return ok(UtilisateurSerializer(request.user).data)


# class LogoutView(APIView):
#     def post(self, request):
#         try:
#             RefreshToken(request.data.get('refresh', '')).blacklist()
#         except Exception:
#             pass
#         return ok(msg='Déconnexion réussie.')



class LogoutView(APIView):
    def post(self, request):
        try:
            RefreshToken(request.data.get('refresh', '')).blacklist()
        except Exception:
            pass
        # حذف FCM Token عند تسجيل الخروج
        request.user.fcm_token = ''
        request.user.save(update_fields=['fcm_token'])
        
        return ok(msg='Déconnexion réussie.')

# ══════════════════════════════════════════════════════
# UTILISATEURS  (Admin seulement)
# ══════════════════════════════════════════════════════

class UtilisateurListView(APIView):
    def get(self, request):
        if not request.user.is_admin:
            return forbidden()
        users = Utilisateur.objects.all()
        role  = request.query_params.get('role')
        if role:
            users = users.filter(role=role)
        return ok(UtilisateurSerializer(users, many=True).data)

    def post(self, request):
        if not request.user.is_admin:
            return forbidden()
        s = UtilisateurCreateSerializer(data=request.data)
        if s.is_valid():
            user = s.save()
            return ok(UtilisateurSerializer(user).data, 'Utilisateur créé.', 201)
        return Response({'success': False, 'errors': s.errors}, status=400)


class UtilisateurDetailView(APIView):
    def _get(self, pk):
        try:
            return Utilisateur.objects.get(pk=pk)
        except Utilisateur.DoesNotExist:
            return None

    def get(self, request, pk):
        if not request.user.is_admin:
            return forbidden()
        u = self._get(pk)
        if not u:
            return not_found('Utilisateur introuvable.')
        return ok(UtilisateurSerializer(u).data)

    def put(self, request, pk):
        if not request.user.is_admin:
            return forbidden()
        u = self._get(pk)
        if not u:
            return not_found()
        s = UtilisateurSerializer(u, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return ok(s.data, 'Utilisateur modifié.')
        return Response({'success': False, 'errors': s.errors}, status=400)

    def delete(self, request, pk):
        if not request.user.is_admin:
            return forbidden()
        u = self._get(pk)
        if not u:
            return not_found()
        if u == request.user:
            return err('Vous ne pouvez pas supprimer votre propre compte.')
        u.is_active = False
        u.save()
        return ok(msg=f'Utilisateur {u.get_nom_complet()} désactivé.')


class UtilisateurParRoleView(APIView):
    def get(self, request, role):
        users = Utilisateur.objects.filter(role=role, is_active=True)
        return ok(UtilisateurSimpleSerializer(users, many=True).data)


# ══════════════════════════════════════════════════════
# CHANTIERS
# ══════════════════════════════════════════════════════

class ChantierListView(APIView):
    def get(self, request):
        user = request.user
        status_filter = request.query_params.get('status')

        if user.is_admin:
            chantiers = Chantier.objects.all()
        elif user.is_chef_projet:
            chantiers = Chantier.objects.filter(chef_projet=user)
        elif user.is_chef_chantier:
            chantiers = Chantier.objects.filter(chef_chantier=user)
        else:
            return forbidden('Vous n\'avez pas accès à cette ressource.')

        if status_filter:
            chantiers = chantiers.filter(statut=status_filter)

        return ok(ChantierListSerializer(chantiers, many=True).data)

    def post(self, request):
        if not request.user.is_admin:
            return forbidden('Seul l\'administrateur peut créer un chantier.')

        s = ChantierCreateSerializer(data=request.data)
        if s.is_valid():
            chantier = s.save()
            if chantier.chef_projet:
                creer_notification(
                    chantier.chef_projet,
                    f'🏗️ Nouveau chantier assigné : {chantier.nom}',
                    f'Vous avez été assigné comme Chef de Projet sur le chantier "{chantier.nom}" ({chantier.lieu}).'
                )
            if chantier.chef_chantier:
                creer_notification(
                    chantier.chef_chantier,
                    f'🏗️ Nouveau chantier assigné : {chantier.nom}',
                    f'Vous avez été assigné comme Chef de Chantier sur le chantier "{chantier.nom}" ({chantier.lieu}).'
                )
            return ok(ChantierDetailSerializer(chantier).data, 'Chantier créé.', 201)
        return Response({'success': False, 'errors': s.errors}, status=400)


class ChantierDetailView(APIView):
    def _get_chantier(self, pk, user):
        try:
            c = Chantier.objects.get(pk=pk)
        except Chantier.DoesNotExist:
            return None, not_found('Chantier introuvable.')

        if user.is_admin:
            return c, None
        if user.is_chef_projet and c.chef_projet == user:
            return c, None
        if user.is_chef_chantier and c.chef_chantier == user:
            return c, None

        return None, forbidden('Vous n\'avez pas accès à ce chantier.')

    def get(self, request, pk):
        c, error = self._get_chantier(pk, request.user)
        if error:
            return error
        return ok(ChantierDetailSerializer(c).data)

    def put(self, request, pk):
        if not request.user.is_admin:
            return forbidden('Seul l\'administrateur peut modifier un chantier.')
        try:
            c = Chantier.objects.get(pk=pk)
        except Chantier.DoesNotExist:
            return not_found()

        s = ChantierCreateSerializer(c, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return ok(ChantierDetailSerializer(c).data, 'Chantier modifié.')
        return Response({'success': False, 'errors': s.errors}, status=400)

    def delete(self, request, pk):
        if not request.user.is_admin:
            return forbidden()
        try:
            c = Chantier.objects.get(pk=pk)
        except Chantier.DoesNotExist:
            return not_found()
        nom = c.nom
        c.delete()
        return ok(msg=f'Chantier "{nom}" supprimé.')


# ══════════════════════════════════════════════════════
# TÂCHES
# ══════════════════════════════════════════════════════

class TacheListView(APIView):
    def get(self, request):
        user = request.user
        taches = Tache.objects.all()

        chantier_id = request.query_params.get('chantier')
        if chantier_id:
            taches = taches.filter(chantier_id=chantier_id)

        if user.is_admin:
            pass
        elif user.is_chef_projet:
            taches = taches.filter(chantier__chef_projet=user)
        elif user.is_chef_chantier:
            taches = taches.filter(chantier__chef_chantier=user)
        elif user.is_chef_equipe:
            taches = taches.filter(chef_equipe=user)
        else:
            return forbidden()

        return ok(TacheSerializer(taches, many=True).data)

    def post(self, request):
        if not request.user.is_chef_chantier:
            return forbidden('Seul le chef de chantier peut créer des tâches.')

        s = TacheSerializer(data=request.data)
        if s.is_valid():
            chantier_id = s.validated_data.get('chantier').id
            try:
                chantier = Chantier.objects.get(pk=chantier_id, chef_chantier=request.user)
            except Chantier.DoesNotExist:
                return forbidden('Vous ne pouvez ajouter des tâches qu\'à vos chantiers.')

            tache = s.save()
            if tache.chef_equipe:
                creer_notification(
                    tache.chef_equipe,
                    f'📌 Nouvelle tâche assignée : {tache.titre}',
                    f'Tâche assignée sur le chantier "{chantier.nom}" (priorité : {tache.get_priorite_display()}).'
                )
            return ok(TacheSerializer(tache).data, 'Tâche créée.', 201)
        return Response({'success': False, 'errors': s.errors}, status=400)


class TacheDetailView(APIView):
    def _get_tache(self, pk, user):
        try:
            t = Tache.objects.get(pk=pk)
        except Tache.DoesNotExist:
            return None, not_found('Tâche introuvable.')

        if user.is_admin:
            return t, None
        if user.is_chef_chantier and t.chantier.chef_chantier == user:
            return t, None
        if user.is_chef_equipe and t.chef_equipe == user:
            return t, None
        if user.is_chef_projet and t.chantier.chef_projet == user:
            return t, None

        return None, forbidden()

    def get(self, request, pk):
        t, error = self._get_tache(pk, request.user)
        if error:
            return error
        return ok(TacheSerializer(t).data)

    def put(self, request, pk):
        t, error = self._get_tache(pk, request.user)
        if error:
            return error

        if request.user.is_chef_equipe:
            data = {'statut': request.data.get('statut', t.statut)}
        else:
            data = request.data

        s = TacheSerializer(t, data=data, partial=True)
        if s.is_valid():
            s.save()
            return ok(TacheSerializer(t).data, 'Tâche modifiée.')
        return Response({'success': False, 'errors': s.errors}, status=400)

    def delete(self, request, pk):
        if not (request.user.is_admin or request.user.is_chef_chantier):
            return forbidden()
        t, error = self._get_tache(pk, request.user)
        if error:
            return error
        t.delete()
        return ok(msg='Tâche supprimée.')


# ══════════════════════════════════════════════════════
# OUVRIERS
# ══════════════════════════════════════════════════════

class OuvrierListView(APIView):
    def get(self, request):
        user     = request.user
        ouvriers = Ouvrier.objects.all()
        fonction = request.query_params.get('fonction')

        chantier_id = request.query_params.get('chantier')
        if chantier_id:
            ouvriers = ouvriers.filter(chantier_id=chantier_id)
        if fonction:
            ouvriers = ouvriers.filter(fonction=fonction)

        if user.is_pointeur:
            # Le pointeur voit uniquement les ouvriers de SON chantier assigné
            try:
                assignation = AssignationPointeur.objects.get(pointeur=user)
                ouvriers    = ouvriers.filter(chantier=assignation.chantier)
            except AssignationPointeur.DoesNotExist:
                ouvriers = ouvriers.none()
        elif user.is_chef_chantier:
            ouvriers = ouvriers.filter(chantier__chef_chantier=user)

        return ok(OuvrierSerializer(ouvriers, many=True).data)

    def post(self, request):
        if not request.user.is_pointeur:
            return forbidden('Seul le pointeur peut ajouter des ouvriers.')

        # Vérifier que le pointeur est bien assigné à un chantier
        try:
            assignation = AssignationPointeur.objects.get(pointeur=request.user)
        except AssignationPointeur.DoesNotExist:
            return err('Vous n\'êtes pas assigné à un chantier. Contactez l\'administrateur.', 403)

        s = OuvrierSerializer(data=request.data)
        if s.is_valid():
            ouvrier = s.save(
                pointeur=request.user,
                chantier=assignation.chantier,
            )
            return ok(OuvrierSerializer(ouvrier).data, 'Ouvrier ajouté.', 201)
        return Response({'success': False, 'errors': s.errors}, status=400)


class OuvrierDetailView(APIView):
    def _get(self, pk):
        try:
            return Ouvrier.objects.get(pk=pk)
        except Ouvrier.DoesNotExist:
            return None

    def get(self, request, pk):
        o = self._get(pk)
        if not o:
            return not_found()
        return ok(OuvrierSerializer(o).data)

    def put(self, request, pk):
        if not request.user.is_pointeur:
            return forbidden('Seul le pointeur peut modifier un ouvrier.')
        o = self._get(pk)
        if not o:
            return not_found()
        s = OuvrierSerializer(o, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return ok(OuvrierSerializer(o).data, 'Ouvrier modifié.')
        return Response({'success': False, 'errors': s.errors}, status=400)

    def delete(self, request, pk):
        if not request.user.is_pointeur:
            return forbidden()
        o = self._get(pk)
        if not o:
            return not_found()
        o.delete()
        return ok(msg='Ouvrier supprimé.')


# ══════════════════════════════════════════════════════
# STATISTIQUES GLOBALES (Admin)
# ══════════════════════════════════════════════════════

class StatsView(APIView):
    def get(self, request):
        if not request.user.is_admin:
            return forbidden()

        aujourd_hui = datetime.date.today()
        ce_mois     = aujourd_hui.replace(day=1)

        # ── Stats classiques ──
        data = {
            'chantiers': {
                'total':    Chantier.objects.count(),
                'planifie': Chantier.objects.filter(statut='planifie').count(),
                'en_cours': Chantier.objects.filter(statut='en_cours').count(),
                'termine':  Chantier.objects.filter(statut='termine').count(),
                'suspendu': Chantier.objects.filter(statut='suspendu').count(),
            },
            'taches': {
                'total':    Tache.objects.count(),
                'a_faire':  Tache.objects.filter(statut='a_faire').count(),
                'en_cours': Tache.objects.filter(statut='en_cours').count(),
                'fait':     Tache.objects.filter(statut='fait').count(),
            },
            'ouvriers':     Ouvrier.objects.count(),
            'utilisateurs': Utilisateur.objects.filter(is_active=True).count(),
        }

        # ── Stats pointage globales ──
        total_aujourd_hui = (
            Pointage.objects
            .filter(date=aujourd_hui)
            .aggregate(h=Sum('total_heures'), p=Sum('total_prix'))
        )
        total_mois = (
            Pointage.objects
            .filter(date__gte=ce_mois)
            .aggregate(h=Sum('total_heures'), p=Sum('total_prix'))
        )

        data['pointage'] = {
            'total_pointages':          Pointage.objects.count(),
            'heures_aujourd_hui':       float(total_aujourd_hui['h'] or 0),
            'heures_mois':              float(total_mois['h'] or 0),
            'salaires_mois':            float(total_mois['p'] or 0),
        }

        # ── Stats pointage par chantier ──
        chantiers_stats = []
        for chantier in Chantier.objects.all():
            agg = (
                Pointage.objects
                .filter(chantier=chantier)
                .aggregate(
                    total_heures=Sum('total_heures'),
                    total_prix=Sum('total_prix'),
                )
            )
            agg_jour = (
                Pointage.objects
                .filter(chantier=chantier, date=aujourd_hui)
                .aggregate(cout=Sum('total_prix'))
            )
            agg_mois = (
                Pointage.objects
                .filter(chantier=chantier, date__gte=ce_mois)
                .aggregate(cout=Sum('total_prix'))
            )
            chantiers_stats.append({
                'id':              chantier.id,
                'nom':             chantier.nom,
                'nombre_ouvriers': chantier.ouvriers.count(),
                'total_heures':    float(agg['total_heures'] or 0),
                'cout_journalier': float(agg_jour['cout'] or 0),
                'cout_mensuel':    float(agg_mois['cout'] or 0),
            })

        data['stats_par_chantier'] = chantiers_stats
        return ok(data)


# ══════════════════════════════════════════════════════
# ASSIGNATION POINTEUR → CHANTIER  ← NOUVEAU
# ══════════════════════════════════════════════════════

class AssignationPointeurListView(APIView):
    """Liste toutes les assignations + créer/remplacer une assignation."""

    def get(self, request):
        if not request.user.is_admin:
            return forbidden()
        assignations = AssignationPointeur.objects.select_related('pointeur', 'chantier').all()
        return ok(AssignationPointeurSerializer(assignations, many=True).data)

    def post(self, request):
        """
        Assigne un pointeur à un chantier.
        Si une assignation existe déjà pour ce pointeur, elle est remplacée.
        """
        if not request.user.is_admin:
            return forbidden()

        pointeur_id = request.data.get('pointeur')
        chantier_id = request.data.get('chantier')

        try:
            pointeur = Utilisateur.objects.get(pk=pointeur_id, role='pointeur')
        except Utilisateur.DoesNotExist:
            return not_found('Pointeur introuvable ou rôle invalide.')

        try:
            chantier = Chantier.objects.get(pk=chantier_id)
        except Chantier.DoesNotExist:
            return not_found('Chantier introuvable.')

        # Upsert : mettre à jour si existe déjà
        assignation, created = AssignationPointeur.objects.update_or_create(
            pointeur=pointeur,
            defaults={'chantier': chantier},
        )

        # Notifier le pointeur
        creer_notification(
            pointeur,
            f'📋 Assignation chantier : {chantier.nom}',
            f'Vous avez été assigné au chantier "{chantier.nom}" ({chantier.lieu}).'
        )

        msg = 'Pointeur assigné au chantier.' if created else 'Assignation mise à jour.'
        return ok(AssignationPointeurSerializer(assignation).data, msg, 201 if created else 200)


class AssignationPointeurDetailView(APIView):
    """Supprimer une assignation."""

    def delete(self, request, pk):
        if not request.user.is_admin:
            return forbidden()
        try:
            a = AssignationPointeur.objects.get(pk=pk)
        except AssignationPointeur.DoesNotExist:
            return not_found('Assignation introuvable.')
        nom = a.pointeur.get_nom_complet()
        a.delete()
        return ok(msg=f'Assignation de {nom} supprimée.')


class MonChantierView(APIView):
    """Retourne le chantier assigné au pointeur connecté."""

    def get(self, request):
        if not request.user.is_pointeur:
            return forbidden('Réservé aux pointeurs.')
        try:
            assignation = AssignationPointeur.objects.select_related(
                'chantier'
            ).get(pointeur=request.user)
        except AssignationPointeur.DoesNotExist:
            return err('Vous n\'êtes pas encore assigné à un chantier.', 403)

        chantier = assignation.chantier
        return ok({
            'chantier':    ChantierDetailSerializer(chantier).data,
            'assignation': AssignationPointeurSerializer(assignation).data,
        })


# ══════════════════════════════════════════════════════
# POINTAGE  ← NOUVEAU
# ══════════════════════════════════════════════════════

class PointageListView(APIView):
    """
    GET  : liste des pointages (filtrables par chantier, date, ouvrier)
    POST : enregistrer un pointage (pointeur uniquement)
    """

    def get(self, request):
        user     = request.user
        pointages = Pointage.objects.select_related('ouvrier', 'chantier', 'pointeur')

        # Filtres optionnels
        chantier_id = request.query_params.get('chantier')
        ouvrier_id  = request.query_params.get('ouvrier')
        date_str    = request.query_params.get('date')
        mois        = request.query_params.get('mois')   # format YYYY-MM
        annee       = request.query_params.get('annee')

        if chantier_id:
            pointages = pointages.filter(chantier_id=chantier_id)
        if ouvrier_id:
            pointages = pointages.filter(ouvrier_id=ouvrier_id)
        if date_str:
            pointages = pointages.filter(date=date_str)
        if mois:
            try:
                y, m = mois.split('-')
                pointages = pointages.filter(date__year=y, date__month=m)
            except ValueError:
                pass
        if annee:
            pointages = pointages.filter(date__year=annee)

        # Restriction par rôle
        if user.is_pointeur:
            try:
                assignation = AssignationPointeur.objects.get(pointeur=user)
                pointages   = pointages.filter(chantier=assignation.chantier)
            except AssignationPointeur.DoesNotExist:
                return err('Aucun chantier assigné.', 403)
        elif user.is_chef_chantier:
            pointages = pointages.filter(chantier__chef_chantier=user)
        elif user.is_chef_projet:
            pointages = pointages.filter(chantier__chef_projet=user)
        elif not user.is_admin:
            return forbidden()

        return ok(PointageSerializer(pointages, many=True).data)

    def post(self, request):
        if not request.user.is_pointeur:
            return forbidden('Seul le pointeur peut enregistrer un pointage.')

        # Vérifier assignation
        try:
            assignation = AssignationPointeur.objects.get(pointeur=request.user)
        except AssignationPointeur.DoesNotExist:
            return err('Vous n\'êtes pas assigné à un chantier.', 403)

        data = request.data.copy()
        # Forcer le chantier à celui du pointeur
        data['chantier'] = assignation.chantier.id

        s = PointageSerializer(data=data)
        if s.is_valid():
            # Vérifier que l'ouvrier appartient bien au chantier du pointeur
            ouvrier = s.validated_data['ouvrier']
            if ouvrier.chantier_id != assignation.chantier.id:
                return err('Cet ouvrier n\'appartient pas à votre chantier.')

            pointage = s.save(pointeur=request.user)
            return ok(PointageSerializer(pointage).data, 'Pointage enregistré.', 201)

        return Response({'success': False, 'errors': s.errors}, status=400)


class PointageDetailView(APIView):
    def _get(self, pk):
        try:
            return Pointage.objects.get(pk=pk)
        except Pointage.DoesNotExist:
            return None

    def get(self, request, pk):
        p = self._get(pk)
        if not p:
            return not_found()
        return ok(PointageSerializer(p).data)

    def put(self, request, pk):
        p = self._get(pk)
        if not p:
            return not_found()

        # Seul le pointeur qui a créé ou l'admin peut modifier
        if not (request.user.is_admin or p.pointeur == request.user):
            return forbidden()

        s = PointageSerializer(p, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return ok(PointageSerializer(p).data, 'Pointage modifié.')
        return Response({'success': False, 'errors': s.errors}, status=400)

    def delete(self, request, pk):
        p = self._get(pk)
        if not p:
            return not_found()
        if not (request.user.is_admin or p.pointeur == request.user):
            return forbidden()
        p.delete()
        return ok(msg='Pointage supprimé.')


# ══════════════════════════════════════════════════════
# STATISTIQUES POINTAGE PAR POINTEUR  ← NOUVEAU
# ══════════════════════════════════════════════════════

class StatsPointageView(APIView):
    """Stats de pointage pour le pointeur connecté (son chantier uniquement)."""

    def get(self, request):
        if not request.user.is_pointeur:
            return forbidden()

        try:
            assignation = AssignationPointeur.objects.get(pointeur=request.user)
        except AssignationPointeur.DoesNotExist:
            return err('Aucun chantier assigné.', 403)

        chantier    = assignation.chantier
        aujourd_hui = datetime.date.today()
        ce_mois     = aujourd_hui.replace(day=1)

        qs = Pointage.objects.filter(chantier=chantier)

        agg_jour = qs.filter(date=aujourd_hui).aggregate(
            h=Sum('total_heures'), p=Sum('total_prix')
        )
        agg_mois = qs.filter(date__gte=ce_mois).aggregate(
            h=Sum('total_heures'), p=Sum('total_prix')
        )

        # ── Liste des absences du mois (Ouvriers sans pointage certains jours) ──
        absents_details = []
        d = ce_mois
        jours = []
        while d <= aujourd_hui:
            jours.append(d)
            d += datetime.timedelta(days=1)

        tous_les_ouvriers = chantier.ouvriers.all()
        for jour in jours:
            presents_ce_jour = set(qs.filter(date=jour).values_list('ouvrier_id', flat=True))
            for o in tous_les_ouvriers:
                if o.id not in presents_ce_jour:
                    absents_details.append({
                        'ouvrier_id':  o.id,
                        'ouvrier_nom': o.get_nom_complet(),
                        'date':        jour.strftime('%Y-%m-%d'),
                    })

        return ok({
            'chantier':            {'id': chantier.id, 'nom': chantier.nom},
            'nombre_ouvriers':     tous_les_ouvriers.count(),
            'pointages_aujourd_hui': qs.filter(date=aujourd_hui).count(),
            'heures_aujourd_hui':  float(agg_jour['h'] or 0),
            'cout_aujourd_hui':    float(agg_jour['p'] or 0),
            'heures_mois':         float(agg_mois['h'] or 0),
            'cout_mois':           float(agg_mois['p'] or 0),
            'total_pointages':     qs.count(),
            'absences_details':    absents_details,
        })


# ══════════════════════════════════════════════════════
# BULLETIN DE PAIE PDF  ← NOUVEAU
# ══════════════════════════════════════════════════════

class BulletinPaieView(APIView):
    """
    Génère un PDF du bulletin de paie pour un chantier et un mois donnés.
    Paramètres GET : chantier (id), mois (1-12), annee (YYYY)
    Accessible : admin + chef_chantier (son chantier uniquement)
    """

    def get(self, request):
        user = request.user
        if not (user.is_admin or user.is_chef_chantier):
            return forbidden()

        chantier_id = request.query_params.get('chantier')
        mois        = request.query_params.get('mois')
        annee       = request.query_params.get('annee')

        if not all([chantier_id, mois, annee]):
            return err('Paramètres requis : chantier, mois, annee.')

        try:
            chantier = Chantier.objects.get(pk=chantier_id)
        except Chantier.DoesNotExist:
            return not_found('Chantier introuvable.')

        # Chef chantier : vérifier que c'est son chantier
        if user.is_chef_chantier and chantier.chef_chantier != user:
            return forbidden('Ce chantier ne vous appartient pas.')

        try:
            mois_int  = int(mois)
            annee_int = int(annee)
        except ValueError:
            return err('Mois et année doivent être des entiers.')

        # Récupérer les pointages du mois pour ce chantier
        pointages = (
            Pointage.objects
            .filter(chantier=chantier, date__month=mois_int, date__year=annee_int)
            .select_related('ouvrier')
        )

        # Agréger par ouvrier
        from django.db.models import Sum as S
        ouvriers_data = (
            pointages
            .values(
                'ouvrier__id', 'ouvrier__prenom', 'ouvrier__nom',
                'prix_heure',
            )
            .annotate(
                total_heures=S('total_heures'),
                total_salaire=S('total_prix'),
            )
            .order_by('ouvrier__nom', 'ouvrier__prenom')
        )

        # Totaux généraux
        totaux = pointages.aggregate(
            heures=S('total_heures'),
            salaires=S('total_prix'),
        )

        # ── Générer le PDF avec ReportLab ──
        from io import BytesIO
        from django.http import HttpResponse
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle,
            Paragraph, Spacer,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        import calendar

        buffer = BytesIO()
        doc    = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        styles   = getSampleStyleSheet()
        elements = []

        # Couleur principale
        BLUE    = colors.HexColor('#1A3C6B')
        LBLUE   = colors.HexColor('#E8F0FB')
        ACCENT  = colors.HexColor('#00B4D8')

        # ── En-tête ──
        style_titre = ParagraphStyle(
            'titre', parent=styles['Title'],
            fontSize=20, textColor=BLUE,
            spaceAfter=4, alignment=TA_CENTER,
        )
        style_sub = ParagraphStyle(
            'sub', parent=styles['Normal'],
            fontSize=11, textColor=colors.grey,
            alignment=TA_CENTER, spaceAfter=2,
        )
        style_info = ParagraphStyle(
            'info', parent=styles['Normal'],
            fontSize=10, textColor=BLUE,
        )

        nom_mois = calendar.month_name[mois_int].capitalize()

        elements.append(Paragraph('🏗️  BULLETIN DE PAIE', style_titre))
        elements.append(Paragraph(f'Chantier : <b>{chantier.nom}</b>', style_sub))
        elements.append(Paragraph(f'Lieu : {chantier.lieu}', style_sub))
        elements.append(Paragraph(f'Période : {nom_mois} {annee_int}', style_sub))
        elements.append(Spacer(1, 0.5*cm))

        # ── Ligne de séparation ──
        elements.append(Table(
            [['']],
            colWidths=[17*cm],
            style=TableStyle([('LINEABOVE', (0,0), (-1,-1), 2, ACCENT)])
        ))
        elements.append(Spacer(1, 0.4*cm))

        # ── Tableau des ouvriers ──
        header = ['Ouvrier', 'Fonction', 'Heures travaillées', 'Prix/Heure (DH)', 'Total Salaire (DH)']
        rows   = [header]

        for od in ouvriers_data:
            rows.append([
                f"{od['ouvrier__prenom']} {od['ouvrier__nom']}",
                '',
                f"{float(od['total_heures'] or 0):.2f} h",
                f"{float(od['prix_heure'] or 0):.2f}",
                f"{float(od['total_salaire'] or 0):.2f}",
            ])

        # Ligne totaux
        rows.append([
            'TOTAL GÉNÉRAL', '',
            f"{float(totaux['heures'] or 0):.2f} h",
            '—',
            f"{float(totaux['salaires'] or 0):.2f}",
        ])

        col_widths = [5*cm, 3*cm, 3.5*cm, 3*cm, 3.5*cm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND',   (0,0), (-1,0),  BLUE),
            ('TEXTCOLOR',    (0,0), (-1,0),  colors.white),
            ('FONTNAME',     (0,0), (-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',     (0,0), (-1,0),  10),
            ('ALIGN',        (0,0), (-1,0),  'CENTER'),
            ('BOTTOMPADDING',(0,0), (-1,0),  8),
            ('TOPPADDING',   (0,0), (-1,0),  8),
            # Corps
            ('FONTNAME',     (0,1), (-1,-2), 'Helvetica'),
            ('FONTSIZE',     (0,1), (-1,-2), 9),
            ('ALIGN',        (2,1), (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS',(0,1),(-1,-2), [colors.white, LBLUE]),
            ('GRID',         (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            # Ligne totaux
            ('BACKGROUND',   (0,-1),(-1,-1), colors.HexColor('#1E40AF')),
            ('TEXTCOLOR',    (0,-1),(-1,-1), colors.white),
            ('FONTNAME',     (0,-1),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',     (0,-1),(-1,-1), 10),
            ('TOPPADDING',   (0,-1),(-1,-1), 8),
            ('BOTTOMPADDING',(0,-1),(-1,-1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.8*cm))

        # ── Pied de page ──
        style_pied = ParagraphStyle(
            'pied', parent=styles['Normal'],
            fontSize=8, textColor=colors.grey,
            alignment=TA_CENTER,
        )
        from django.utils.timezone import now
        elements.append(Paragraph(
            f'Document généré le {now().strftime("%d/%m/%Y à %H:%M")} — Système MCA',
            style_pied
        ))

        doc.build(elements)

        # ── Réponse PDF avec tous les headers nécessaires ──
        pdf_bytes = buffer.getvalue()
        # Nettoyer le nom pour les headers HTTP
        import re
        safe_nom = re.sub(r'[^\w\-]', '_', chantier.nom)
        filename = f'bulletin_paie_{safe_nom}_{nom_mois}_{annee_int}.pdf'

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length']      = len(pdf_bytes)
        # Exposer Content-Disposition aux clients cross-origin (Flutter/mobile)
        response['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Length'
        return response


# ══════════════════════════════════════════════════════
# HELPER : créer une notification + push Firebase
# ══════════════════════════════════════════════════════

def creer_notification(destinataire, titre, message, data=None):
    from .fcm_service import envoyer_push, UnregisteredTokenError
    Notification.objects.create(
        destinataire=destinataire,
        titre=titre,
        message=message,
    )
    if destinataire.fcm_token:
        try:
            envoyer_push(
                token_appareil=destinataire.fcm_token,
                titre=titre,
                message=message,
                data=data
            )
        except UnregisteredTokenError:
            # Si le token est invalide, on le supprime côté backend
            destinataire.fcm_token = None
            destinataire.save()
        except Exception as e:
            print(f"⚠️ Erreur notification non critique: {e}")


# ══════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════

class NotificationListView(APIView):
    def get(self, request):
        notifs = Notification.objects.filter(destinataire=request.user)
        return ok(NotificationSerializer(notifs, many=True).data)


class NotificationMarquerLueView(APIView):
    def post(self, request, pk=None):
        if pk:
            try:
                notif = Notification.objects.get(pk=pk, destinataire=request.user)
            except Notification.DoesNotExist:
                return not_found('Notification introuvable.')
            notif.lue = True
            notif.save()
        else:
            Notification.objects.filter(
                destinataire=request.user, lue=False
            ).update(lue=True)
        return ok(msg='Notification(s) marquée(s) comme lue(s).')


# ══════════════════════════════════════════════════════
# RAPPORTS
# ══════════════════════════════════════════════════════

class RapportListView(APIView):
    def get(self, request):
        user = request.user
        if user.is_admin:
            rapports = Rapport.objects.all()
        else:
            if user.is_chef_chantier:
                ids = Chantier.objects.filter(chef_chantier=user).values_list('id', flat=True)
            elif user.is_chef_projet:
                ids = Chantier.objects.filter(chef_projet=user).values_list('id', flat=True)
            else:
                return forbidden()
            rapports = Rapport.objects.filter(chantier_id__in=ids)
        return ok(RapportSerializer(rapports, many=True, context={'request': request}).data)

    def post(self, request):
        user        = request.user
        chantier_id = request.data.get('chantier')
        try:
            chantier = Chantier.objects.get(pk=chantier_id)
        except Chantier.DoesNotExist:
            return not_found('Chantier introuvable.')

        if not (user.is_admin or
                (user.is_chef_chantier and chantier.chef_chantier == user) or
                (user.is_chef_projet and chantier.chef_projet == user)):
            return forbidden()

        rapport = Rapport.objects.create(
            chantier=chantier,
            titre=request.data.get('titre', ''),
            contenu=request.data.get('contenu', ''),
            cree_par=user,
            fichier=request.FILES.get('fichier', None),  # Garde l'ancien comportement
        )

        # ── MULTIPLES FICHIERS ───────────────────────────────
        attached_files = request.FILES.getlist('attached_files')
        for f in attached_files:
            RapportFile.objects.create(rapport=rapport, fichier=f)

        for admin in Utilisateur.objects.filter(role='admin'):
            creer_notification(
                admin,
                f'📋 Nouveau rapport : {rapport.titre}',
                f'{user.get_nom_complet()} a créé un rapport pour le chantier "{chantier.nom}".'
            )
        return ok(RapportSerializer(rapport, context={'request': request}).data, 'Rapport créé.', 201)


class RapportDetailView(APIView):
    def patch(self, request, pk):
        """Modifier un rapport et/ou son document joint (ModifierDoc UML)"""
        user = request.user
        try:
            rapport = Rapport.objects.get(pk=pk)
        except Rapport.DoesNotExist:
            return not_found('Rapport introuvable.')
        if not (user.is_admin or rapport.cree_par == user):
            return forbidden()

        if 'titre' in request.data:
            rapport.titre = request.data['titre']
        if 'contenu' in request.data:
            rapport.contenu = request.data['contenu']

        # Ancien comportement (fichier unique principal)
        if 'fichier' in request.FILES:
            rapport.modifier_doc(request.FILES['fichier'])
        else:
            rapport.save()

        # ── AJOUTER DES FICHIERS SUPPLÉMENTAIRES ─────────────
        attached_files = request.FILES.getlist('attached_files')
        for f in attached_files:
            RapportFile.objects.create(rapport=rapport, fichier=f)

        return ok(RapportSerializer(rapport, context={'request': request}).data, 'Rapport mis à jour.')

    def delete(self, request, pk):
        if not request.user.is_admin:
            return forbidden()
        try:
            r = Rapport.objects.get(pk=pk)
        except Rapport.DoesNotExist:
            return not_found()
        if r.fichier:
            try:
                import os
                if os.path.isfile(r.fichier.path):
                    os.remove(r.fichier.path)
            except Exception:
                pass
        r.delete()
        return ok(msg='Rapport supprimé.')


# ══════════════════════════════════════════════════════
# FACTURES
# ══════════════════════════════════════════════════════

class FactureListView(APIView):
    def get(self, request):
        user = request.user
        if user.is_admin:
            factures = Facture.objects.all()
        else:
            if user.is_chef_chantier:
                ids = Chantier.objects.filter(chef_chantier=user).values_list('id', flat=True)
            elif user.is_chef_projet:
                ids = Chantier.objects.filter(chef_projet=user).values_list('id', flat=True)
            else:
                return forbidden()
            factures = Facture.objects.filter(chantier_id__in=ids)
        return ok(FactureSerializer(factures, many=True).data)

    def post(self, request):
        user        = request.user
        chantier_id = request.data.get('chantier')
        try:
            chantier = Chantier.objects.get(pk=chantier_id)
        except Chantier.DoesNotExist:
            return not_found('Chantier introuvable.')

        if not (user.is_admin or
                (user.is_chef_chantier and chantier.chef_chantier == user) or
                (user.is_chef_projet and chantier.chef_projet == user)):
            return forbidden()

        facture = Facture.objects.create(
            chantier=chantier,
            numero=request.data.get('numero', ''),
            description=request.data.get('description', ''),
            montant=request.data.get('montant', 0),
            statut=request.data.get('statut', 'en_attente'),
            cree_par=user,
            fichier=request.FILES.get('fichier'),
        )
        for admin in Utilisateur.objects.filter(role='admin'):
            creer_notification(
                admin,
                f'🧾 Nouvelle facture : {facture.numero}',
                f'{user.get_nom_complet()} a créé une facture de {facture.montant} DH pour "{chantier.nom}".'
            )
        return ok(FactureSerializer(facture).data, 'Facture créée.', 201)


class FactureDetailView(APIView):
    def put(self, request, pk):
        try:
            f = Facture.objects.get(pk=pk)
        except Facture.DoesNotExist:
            return not_found()

        user = request.user
        if not (user.is_admin or f.cree_par == user):
            return forbidden()

        # Admin peut tout modifier, le créateur seulement la description
        if user.is_admin:
            fields = ['statut', 'description', 'montant', 'numero']
        else:
            fields = ['description']

        for field in fields:
            if field in request.data:
                setattr(f, field, request.data[field])

        if 'fichier' in request.FILES:
            if f.fichier:
                try:
                    import os
                    if os.path.isfile(f.fichier.path):
                        os.remove(f.fichier.path)
                except Exception:
                    pass
            f.fichier = request.FILES['fichier']

        f.save()
        return ok(FactureSerializer(f).data, 'Facture modifiée.')

    def patch(self, request, pk):
        return self.put(request, pk)

    def delete(self, request, pk):
        if not request.user.is_admin:
            return forbidden()
        try:
            f = Facture.objects.get(pk=pk)
        except Facture.DoesNotExist:
            return not_found()

        if f.fichier:
            try:
                import os
                if os.path.isfile(f.fichier.path):
                    os.remove(f.fichier.path)
            except Exception:
                pass

        f.delete()
        return ok(msg='Facture supprimée.')


# ══════════════════════════════════════════════════════
# PROFIL UTILISATEUR
# ══════════════════════════════════════════════════════

class ProfilUpdateView(APIView):
    def put(self, request):
        user = request.user
        for field in ['prenom', 'nom', 'telephone']:
            if field in request.data:
                setattr(user, field, request.data[field])
        if 'password' in request.data and request.data['password']:
            user.set_password(request.data['password'])
        user.save()
        return ok(UtilisateurSerializer(user).data, 'Profil mis à jour.')


# ══════════════════════════════════════════════════════
# FCM TOKEN
# ══════════════════════════════════════════════════════

# class EnregistrerFCMTokenView(APIView):
#     def post(self, request):
#         token = request.data.get('fcm_token', '').strip()
#         if not token:
#             return Response({'success': False, 'message': 'Token manquant.'}, status=400)
#         request.user.fcm_token = token
#         request.user.save(update_fields=['fcm_token'])
#         return ok(msg='Token FCM enregistré.')


class EnregistrerFCMTokenView(APIView):
    def post(self, request):
        token = request.data.get('fcm_token', '').strip()

        if not token:
            return Response(
                {'success': False, 'message': 'Token manquant.'},
                status=400,
            )

        # حذف نفس الـ token من أي مستخدم آخر
        Utilisateur.objects.filter(fcm_token=token).exclude(pk=request.user.pk).update(
            fcm_token=''
        )

        # تسجيله عند المستخدم الحالي فقط
        request.user.fcm_token = token
        request.user.save(update_fields=['fcm_token'])

        return ok(msg='Token FCM enregistré.')


# ══════════════════════════════════════════════════════
# STATS CHEF CHANTIER  ← NOUVEAU
# ══════════════════════════════════════════════════════

class StatsChefChantierView(APIView):
    """
    Statistiques complètes de pointage pour le chef de chantier.
    Présences / absences / retards / heures / coût — par chantier et par ouvrier.
    Accessible aussi par l'admin (paramètre chantier= obligatoire dans ce cas).
    """

    HEURE_REFERENCE = datetime.time(8, 30)   # seuil retard

    def get(self, request):
        user = request.user
        if not (user.is_chef_chantier or user.is_admin):
            return forbidden()

        chantier_id = request.query_params.get('chantier')
        mois_param  = request.query_params.get('mois')   # YYYY-MM

        # ── Récupérer les chantiers accessibles ──
        if user.is_admin:
            base_qs = Chantier.objects.all()
        else:
            base_qs = Chantier.objects.filter(chef_chantier=user)

        if chantier_id:
            try:
                chantiers = [base_qs.get(pk=chantier_id)]
            except Chantier.DoesNotExist:
                return not_found('Chantier introuvable ou accès refusé.')
        else:
            chantiers = list(base_qs)

        # ── Période d'analyse ──
        aujourd_hui = datetime.date.today()
        if mois_param:
            try:
                y, m      = mois_param.split('-')
                mois_debut = datetime.date(int(y), int(m), 1)
            except (ValueError, TypeError):
                mois_debut = aujourd_hui.replace(day=1)
        else:
            mois_debut = aujourd_hui.replace(day=1)

        result = []
        for chantier in chantiers:
            ouvriers      = Ouvrier.objects.filter(chantier=chantier)
            total_ouvriers = ouvriers.count()
            ouvriers_ids   = list(ouvriers.values_list('id', flat=True))

            # ── Présents / absents / retards aujourd'hui ──
            qs_auj = Pointage.objects.filter(chantier=chantier, date=aujourd_hui)
            presents_ids    = set(qs_auj.values_list('ouvrier_id', flat=True))
            presents_count  = len(presents_ids)
            absents_count   = total_ouvriers - presents_count
            retards_auj     = qs_auj.filter(
                heure_debut__gt=self.HEURE_REFERENCE
            ).count()

            # ── Agrégats journée ──
            agg_auj = qs_auj.aggregate(
                h=Sum('total_heures'), p=Sum('total_prix')
            )
            # ── Agrégats mois (Calcul strict de la période) ──
            if mois_debut.month == 12:
                mois_fin = datetime.date(mois_debut.year + 1, 1, 1)
            else:
                mois_fin = datetime.date(mois_debut.year, mois_debut.month + 1, 1)

            qs_mois = Pointage.objects.filter(
                chantier=chantier, date__gte=mois_debut, date__lt=mois_fin
            )
            agg_mois = qs_mois.aggregate(
                h=Sum('total_heures'), p=Sum('total_prix'),
                nb=Count('id'),
            )

            # ── Statistiques par ouvrier ──
            ouvriers_stats = []
            for ouvrier in ouvriers:
                agg_o = Pointage.objects.filter(
                    ouvrier=ouvrier, chantier=chantier, 
                    date__gte=mois_debut, date__lt=mois_fin
                ).aggregate(
                    h=Sum('total_heures'),
                    p=Sum('total_prix'),
                    jours=Count('id'),
                )
                retards_o = Pointage.objects.filter(
                    ouvrier=ouvrier, chantier=chantier,
                    date__gte=mois_debut, date__lt=mois_fin,
                    heure_debut__gt=self.HEURE_REFERENCE,
                ).count()
                ouvriers_stats.append({
                    'id':                 ouvrier.id,
                    'nom':                ouvrier.get_nom_complet(),
                    'fonction':           ouvrier.get_fonction_display(),
                    'prix_heure':         float(ouvrier.prix_heure),
                    'heures_mois':        float(agg_o['h'] or 0),
                    'salaire_mois':       float(agg_o['p'] or 0),
                    'jours_travailles':   agg_o['jours'] or 0,
                    'retards_mois':       retards_o,
                    'present_aujourd_hui': ouvrier.id in presents_ids,
                })

            result.append({
                'chantier': {
                    'id':     chantier.id,
                    'nom':    chantier.nom,
                    'lieu':   chantier.lieu,
                    'statut': chantier.statut,
                },
                'total_ouvriers':      total_ouvriers,
                'presents_aujourd_hui': presents_count,
                'absents_aujourd_hui': absents_count,
                'retards_aujourd_hui': retards_auj,
                'heures_aujourd_hui':  float(agg_auj['h'] or 0),
                'cout_aujourd_hui':    float(agg_auj['p'] or 0),
                'heures_mois':         float(agg_mois['h'] or 0),
                'cout_mois':           float(agg_mois['p'] or 0),
                'nb_pointages_mois':   agg_mois['nb'] or 0,
                'ouvriers_stats':      ouvriers_stats,
                'mois_analyse':        mois_debut.strftime('%Y-%m'),
            })

        return ok(result[0] if len(result) == 1 else result)
