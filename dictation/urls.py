from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('dictation/generate/', views.generate_dictation_view, name='generate_dictation'),
    path('dictation/correct/', views.correct_dictation_view, name='correct_dictation'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Pour le débogage
print("URLs de l'app dictation:")
for url in urlpatterns:
    print(f"- {url.pattern}") 