from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import UserViewSet, UserRoleViewSet
from apps.heritage.views import (
    HeritageCategoryViewSet, HeritageTypeViewSet, ParishViewSet,
    MediaFileViewSet, HeritageItemViewSet, HeritageRelationViewSet,
    ContributionViewSet, AnnotationViewSet
)
from apps.education.views import (
    LOMGeneralViewSet, LOMLifeCycleViewSet, LOMContributorViewSet,
    LOMEducationalViewSet, LOMRightsViewSet, LOMClassificationViewSet,
    EducationalResourceViewSet, ResourceTypeViewSet, ResourceCategoryViewSet,
    LOMPackageViewSet,
    LOMRelationViewSet,
    SCORMPackageViewSet,
)
from apps.moderation.views import ModerationViewSet, ReviewChecklistViewSet, ContributionFlagViewSet
from apps.routes.views import RouteViewSet, UserRouteProgressViewSet
from apps.gamification import views as gamification_views
from apps.ai_services import views as ai_services_views
from apps.ai_services.assist_views import (
    ContributionDraftAssistView,
    ContributionMetadataAssistView,
    CuratorReviewAssistView,
)
from apps.ai_services.status_views import AIStatusView
from apps.notifications.views import NotificationTemplateViewSet, UserNotificationViewSet
from apps.contributions.views import MyContributionsViewSet

# Create router for automatic URL routing
router = DefaultRouter()

# User endpoints
router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', UserRoleViewSet, basename='role')

# Heritage endpoints
router.register(r'categories', HeritageCategoryViewSet, basename='category')
router.register(r'types', HeritageTypeViewSet, basename='type')
router.register(r'parishes', ParishViewSet, basename='parish')
router.register(r'media', MediaFileViewSet, basename='media')
router.register(r'heritage-items', HeritageItemViewSet, basename='heritage-item')
router.register(r'contributions', ContributionViewSet, basename='contribution')
router.register(r'relations', HeritageRelationViewSet, basename='relation')
router.register(r'annotations', AnnotationViewSet, basename='annotation')

# Education/LOM endpoints
router.register(r'lom', LOMGeneralViewSet, basename='lom')
router.register(r'lom-lifecycle', LOMLifeCycleViewSet, basename='lom-lifecycle')
router.register(r'lom-contributors', LOMContributorViewSet, basename='lom-contributor')
router.register(r'lom-educational', LOMEducationalViewSet, basename='lom-educational')
router.register(r'lom-rights', LOMRightsViewSet, basename='lom-rights')
router.register(r'lom-classifications', LOMClassificationViewSet, basename='lom-classification')
router.register(r'lom-relations', LOMRelationViewSet, basename='lom-relation')
router.register(r'educational-resources', EducationalResourceViewSet, basename='educational-resource')
router.register(r'resource-types', ResourceTypeViewSet, basename='resource-type')
router.register(r'resource-categories', ResourceCategoryViewSet, basename='resource-category')
router.register(r'education/lom-packages', LOMPackageViewSet, basename='lom-packages')
router.register(r'education/scorm-packages', SCORMPackageViewSet, basename='scorm-packages')

# Moderation endpoints
# router.register(r'moderation', ModerationViewSet, basename='moderation')
router.register(r'moderation/queue', ModerationViewSet, basename='moderation-queue')
router.register(r'moderation/checklists', ReviewChecklistViewSet, basename='moderation-checklists')
router.register(r'moderation/flags', ContributionFlagViewSet, basename='moderation-flags')

# Contributor self-service endpoints
router.register(r'my-contributions', MyContributionsViewSet, basename='my-contributions')

# Route endpoints
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'route-progress', UserRouteProgressViewSet, basename='route-progress')

# Gamification endpoints
router.register(r'badges', gamification_views.BadgeViewSet, basename='badge')
router.register(r'levels', gamification_views.LevelViewSet, basename='level')
router.register(r'user-badges', gamification_views.UserBadgeViewSet, basename='user-badge')
router.register(r'point-transactions', gamification_views.PointTransactionViewSet, basename='point-transaction')

# AI Service endpoints
router.register(r'ai-suggestions', ai_services_views.AISuggestionViewSet, basename='ai-suggestion')

# Notification endpoints
router.register(r'notification-templates', NotificationTemplateViewSet, basename='notification-template')
router.register(r'notifications', UserNotificationViewSet, basename='notification')

urlpatterns = [
    # JWT token endpoints
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Router URLs
    path('', include(router.urls)),

    # AI assist endpoints (Ollama-backed)
    path('ai/status/', AIStatusView.as_view(), name='ai-status'),
    path('ai/assist/contribution-draft/', ContributionDraftAssistView.as_view(), name='ai-contribution-draft'),
    path(
        'ai/assist/contribution-metadata/',
        ContributionMetadataAssistView.as_view(),
        name='ai-contribution-metadata',
    ),
    path('ai/assist/curator-review/', CuratorReviewAssistView.as_view(), name='ai-curator-review'),
]
