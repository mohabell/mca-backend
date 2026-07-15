# Migration Django — Rapport fichier joint

## 1. Appliquer la migration

```bash
cd backend
python manage.py makemigrations api --name="rapport_fichier"
python manage.py migrate
```

## 2. Configurer MEDIA dans settings.py

```python
import os
MEDIA_URL  = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## 3. Configurer urls.py (projet, pas api)

```python
from django.conf import settings
from django.conf.urls.static import static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## Fichiers modifiés
- `api/models.py`     → classe Rapport + FileField + importer_document() + modifier_doc()
- `api/serializers.py` → RapportSerializer + champs fichier + fichier_nom
- `api/views.py`      → RapportListView.post (accepte fichier) + RapportDetailView.patch (modifier doc)
