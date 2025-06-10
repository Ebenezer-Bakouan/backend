from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('dictation.urls')),  # Les URLs de l'app dictation sont sous /api/
    # URLs d'authentification
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/', include('dictation.auth_urls')),  # URLs personnalisées d'authentification
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Pour le débogage
print("URLs principales:")
for url in urlpatterns:
    print(f"- {url.pattern}")