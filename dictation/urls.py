from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DictationViewSet,
    UserFeedbackViewSet,
    correct_dictation_view,
    generate_dictation_view,
    process_image
)

router = DefaultRouter()
router.register(r'dictations', DictationViewSet, basename='dictation')
router.register(r'feedback', UserFeedbackViewSet, basename='feedback')

urlpatterns = [
    path('', include(router.urls)),
    path('dictation/correct/', correct_dictation_view, name='correct-dictation'),
    path('dictation/generate/', generate_dictation_view, name='generate-dictation'),
    path('process-image/', process_image, name='process-image'),
]

# Pour le débogage
print("URLs de l'app dictation:")
for url in urlpatterns:
    print(f"- {url.pattern}")