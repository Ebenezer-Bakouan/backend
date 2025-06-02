from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('dictation.urls')),  # Les URLs de l'app dictation sont sous /api/
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Pour le débogage
print("URLs principales:")
for url in urlpatterns:
    print(f"- {url.pattern}") 