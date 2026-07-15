"""
api/urls.py  (version complète avec pointage)
=============================================
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────
    path('auth/login/',         views.LoginView.as_view(),        name='login'),
    path('auth/logout/',        views.LogoutView.as_view(),       name='logout'),
    path('auth/me/',            views.MeView.as_view(),           name='me'),
    path('auth/refresh/',       TokenRefreshView.as_view(),       name='token_refresh'),
    path('auth/profil/',        views.ProfilUpdateView.as_view(), name='profil-update'),
    path('auth/fcm-token/',     views.EnregistrerFCMTokenView.as_view(), name='fcm-token'),

    # ── Utilisateurs (Admin) ──────────────────────────
    path('utilisateurs/',                  views.UtilisateurListView.as_view(),   name='user-list'),
    path('utilisateurs/<int:pk>/',         views.UtilisateurDetailView.as_view(), name='user-detail'),
    path('utilisateurs/role/<str:role>/',  views.UtilisateurParRoleView.as_view(), name='users-by-role'),

    # ── Chantiers ─────────────────────────────────────
    path('chantiers/',           views.ChantierListView.as_view(),   name='chantier-list'),
    path('chantiers/<int:pk>/',  views.ChantierDetailView.as_view(), name='chantier-detail'),

    # ── Tâches ────────────────────────────────────────
    path('taches/',          views.TacheListView.as_view(),   name='tache-list'),
    path('taches/<int:pk>/', views.TacheDetailView.as_view(), name='tache-detail'),

    # ── Ouvriers ──────────────────────────────────────
    path('ouvriers/',          views.OuvrierListView.as_view(),   name='ouvrier-list'),
    path('ouvriers/<int:pk>/', views.OuvrierDetailView.as_view(), name='ouvrier-detail'),

    # ── Statistiques (Admin) ──────────────────────────
    path('stats/',          views.StatsView.as_view(),         name='stats'),

    # ── Notifications ─────────────────────────────────
    path('notifications/',               views.NotificationListView.as_view(),       name='notif-list'),
    path('notifications/lire-tout/',     views.NotificationMarquerLueView.as_view(), name='notif-lire-tout'),
    path('notifications/<int:pk>/lire/', views.NotificationMarquerLueView.as_view(), name='notif-lire'),

    # ── Rapports ──────────────────────────────────────
    path('rapports/',          views.RapportListView.as_view(),   name='rapport-list'),
    path('rapports/<int:pk>/', views.RapportDetailView.as_view(), name='rapport-detail'),

    # ── Factures ──────────────────────────────────────
    path('factures/',          views.FactureListView.as_view(),   name='facture-list'),
    path('factures/<int:pk>/', views.FactureDetailView.as_view(), name='facture-detail'),

    # ══════════════════════════════════════════════════
    # NOUVELLES ROUTES — ASSIGNATION & POINTAGE
    # ══════════════════════════════════════════════════

    # ── Assignation Pointeur → Chantier (Admin) ───────
    path('assignations/',          views.AssignationPointeurListView.as_view(),   name='assignation-list'),
    path('assignations/<int:pk>/', views.AssignationPointeurDetailView.as_view(), name='assignation-detail'),

    # ── Mon chantier (Pointeur connecté) ──────────────
    path('mon-chantier/', views.MonChantierView.as_view(), name='mon-chantier'),

    # ── Pointage ──────────────────────────────────────
    path('pointages/',          views.PointageListView.as_view(),   name='pointage-list'),
    path('pointages/<int:pk>/', views.PointageDetailView.as_view(), name='pointage-detail'),

    # ── Stats pointage (Pointeur) ─────────────────────
    path('stats-pointage/', views.StatsPointageView.as_view(), name='stats-pointage'),

    # ── Stats Chef Chantier ──────────────────────────────
    path('stats-chef-chantier/', views.StatsChefChantierView.as_view(), name='stats-chef-chantier'),

    # ── Bulletin de paie PDF (Admin + Chef Chantier) ──
    path('bulletin-paie/', views.BulletinPaieView.as_view(), name='bulletin-paie'),
]
