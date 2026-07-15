
"""Commande pour initialiser les données de démo."""
from django.core.management.base import BaseCommand
from api.models import Utilisateur, Chantier, Tache, Ouvrier

class Command(BaseCommand):
    help = 'Créer les données de démonstration'

    def handle(self, *args, **options):
        if Utilisateur.objects.filter(email='admin@mca.ma').exists():
            self.stdout.write('Données déjà existantes.')
            return

        # Créer les utilisateurs
        admin = Utilisateur.objects.create_superuser(
            email='admin@mca.ma', password='Admin123!',
            prenom='Admin', nom='MCA', role='admin'
        )
        cp = Utilisateur.objects.create_user(
            email='chef.projet@mca.ma', password='Chef123!',
            prenom='Karim', nom='Benali', role='chef_projet'
        )
        cc = Utilisateur.objects.create_user(
            email='chef.chantier@mca.ma', password='Chef123!',
            prenom='Hassan', nom='Mounir', role='chef_chantier'
        )
        ce = Utilisateur.objects.create_user(
            email='chef.equipe@mca.ma', password='Chef123!',
            prenom='Youssef', nom='El Fassi', role='chef_equipe'
        )
        pt = Utilisateur.objects.create_user(
            email='pointeur@mca.ma', password='Chef123!',
            prenom='Nadia', nom='Alaoui', role='pointeur'
        )

        # Créer les chantiers
        c1 = Chantier.objects.create(
            nom='Résidence Al Fath', lieu='Casablanca - Hay Hassani',
            budget=1500000, statut='en_cours',
            description='Construction de 24 appartements',
            chef_projet=cp, chef_chantier=cc
        )
        c2 = Chantier.objects.create(
            nom='Centre Commercial Atlas', lieu='Rabat - Agdal',
            budget=4500000, statut='planifie',
            chef_projet=cp, chef_chantier=cc
        )

        # Tâches pour c1
        Tache.objects.create(chantier=c1, titre='Fondations', statut='fait', priorite='haute', chef_equipe=ce)
        Tache.objects.create(chantier=c1, titre='Murs RDC', statut='en_cours', priorite='haute', chef_equipe=ce)
        Tache.objects.create(chantier=c1, titre='Plomberie', statut='a_faire', priorite='moyenne')
        Tache.objects.create(chantier=c1, titre='Peinture', statut='a_faire', priorite='basse')

        # Ouvriers
        Ouvrier.objects.create(
            prenom='Ahmed', nom='Berrada', cin='AA123', fonction='macon',
            chantier=c1, pointeur=pt
        )
        Ouvrier.objects.create(
            prenom='Omar', nom='Ziani', cin='BB456', fonction='electricien',
            chantier=c1, pointeur=pt
        )

        self.stdout.write(self.style.SUCCESS('''
✅ Données créées !
Comptes (mot de passe: Admin123! / Chef123!):
  admin@mca.ma          → Administrateur
  chef.projet@mca.ma    → Chef de Projet
  chef.chantier@mca.ma  → Chef de Chantier
  chef.equipe@mca.ma    → Chef d\'Équipe
  pointeur@mca.ma       → Pointeur
'''))
