from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DictationViewSet,
    correct_dictation_view,
    generate_dictation_view,
    process_image,
    process_image_gemini
)

router = DefaultRouter()
router.register(r'dictations', DictationViewSet, basename='dictation')

urlpatterns = [
    path('', include(router.urls)),
    path('dictation/correct/', correct_dictation_view, name='correct-dictation'),
    path('dictation/generate/', generate_dictation_view, name='generate-dictation'),
    path('dictation/process-image/', process_image, name='process-image'),
    path('dictation/process-image-gemini/', process_image_gemini, name='process-image-gemini'),
]

# Pour le débogage
print("URLs de l'app dictation:")
for url in urlpatterns:
    print(f"- {url.pattern}")