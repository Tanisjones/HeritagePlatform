from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from apps.gamification.services import add_points, award_badge
from apps.gamification.models import Badge, UserBadge, PointTransaction
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish

User = get_user_model()

class GamificationServicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='gamer@example.com', password='password')
        # Manually create profile as there's no signal handling this automatically in test env yet
        from apps.users.models import UserProfile
        UserProfile.objects.create(user=self.user)
        
    def test_add_points_logic(self):
        # Initial state
        self.assertEqual(self.user.profile.points, 0)
        self.assertEqual(self.user.profile.level, 1)

        # Add points
        add_points(self.user, 50, "Test reason")
        
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 50)
        
        # Verify Level up logic (defaults: 0-100 level 1)
        # Add more points to reach next level threshold if configured (default levels created in migration/seed might apply)
        # Assuming minimal implementation, points should just increase here.

    def test_add_unique_points(self):
        add_points(self.user, 10, "Unique", unique_reason=True)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 10)
        
        # Try adding again
        add_points(self.user, 10, "Unique", unique_reason=True)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 10) # Should not increase

    def test_award_badge(self):
        badge = Badge.objects.create(name="Hero", points_value=100)
        award_badge(self.user, badge)
        
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge=badge).exists())
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 100) # Points from badge

    def test_award_badge_duplicate(self):
        badge = Badge.objects.create(name="Hero", points_value=100)
        award_badge(self.user, badge)
        result = award_badge(self.user, badge) # Should return None
        
        self.assertIsNone(result)
        self.assertEqual(UserBadge.objects.count(), 1)
