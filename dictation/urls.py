from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from .views import (
    DictationViewSet,
    UserProfileViewSet, UserFeedbackViewSet,
    RegisterView,
    correct_dictation_view,
    generate_dictation_view,
    process_image
)

router = DefaultRouter()
router.register(r'dictations', DictationViewSet, basename='dictation')
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'feedback', UserFeedbackViewSet, basename='feedback')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/user-info/', UserInfoView.as_view(), name='user-info'),
    path('dictation/correct/', correct_dictation_view, name='correct-dictation'),
    path('dictation/generate/', generate_dictation_view, name='generate-dictation'),
    path('process-image/', process_image, name='process-image'),
]

# Pour le débogage
print("URLs de l'app dictation:")
for url in urlpatterns:
    print(f"- {url.pattern}")