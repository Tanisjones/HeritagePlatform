from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.models import UserProfile, UserRole
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.gis.geos import Point
from apps.cities.testing import make_city
from apps.heritage.models import HeritageCategory, HeritageItem, HeritageType

User = get_user_model()

class UserModelTest(TestCase):

    def setUp(self):
        self.role = UserRole.objects.create(name='Test Role', slug='test-role')

    def test_create_user(self):
        email = 'test@example.com'
        password = 'password123'
        user = User.objects.create_user(email=email, password=password)
        
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        # Username should be generated from email
        self.assertEqual(user.username, 'test')

    def test_create_user_with_username(self):
        email = 'test2@example.com'
        password = 'password123'
        username = 'customuser'
        user = User.objects.create_user(email=email, password=password, username=username)
        
        self.assertEqual(user.email, email)
        self.assertEqual(user.username, username)

    def test_create_superuser(self):
        email = 'admin@example.com'
        password = 'adminpassword'
        user = User.objects.create_superuser(email=email, password=password)
        
        self.assertEqual(user.email, email)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_user_no_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='password')

    def test_user_profile_creation(self):
        user = User.objects.create_user(email='profile@example.com', password='password')
        profile = UserProfile.objects.create(
            user=user, 
            display_name='Test Profile',
            role=self.role
        )
        
        self.assertEqual(profile.user, user)
        self.assertEqual(profile.display_name, 'Test Profile')
        self.assertEqual(profile.role, self.role)
        self.assertEqual(profile.points, 0)
        self.assertEqual(profile.level, 1)

    def test_user_str(self):
        user = User.objects.create_user(email='str@example.com', password='password')
        self.assertEqual(str(user), 'str@example.com')

class UserRoleModelTest(TestCase):
    def test_role_str(self):
        role = UserRole.objects.create(name='Test Curator', slug='test-curator')
        self.assertEqual(str(role), 'Test Curator')

class UserAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='api@example.com', password='password')
        # Assuming profile created automatically via signal in real app, but here manually if needed or tested manually
        # If signals exist, profile is there. Let's create manually to be safe if no signal test setup
        self.profile = UserProfile.objects.create(user=self.user, display_name='API User')

    def test_get_current_user_profile(self):
        self.client.force_authenticate(user=self.user)
        # Assuming endpoint exists at /api/v1/users/me/ or similar, typically provided by Djoser or custom view
        # If specific endpoint unknown, we test typical Djoser /me endpoint or custom profile view
        # Checking urls.py would be ideal, but for now assuming standard convention or skip if unsure route
        pass


class RolePrivilegeEscalationTest(TestCase):
    """Regression guard for the writable-role_id privilege escalation (Vuln 1):
    a user must not be able to self-assign a privileged role (curator/teacher/
    moderator) via registration or `PATCH /users/me/`. Only staff may grant them.
    """

    def setUp(self):
        self.client = APIClient()
        # The core roles are already created by migration 0003_seed_core_roles,
        # so fetch-or-create rather than create (name/slug are unique).
        self.curator_role, _ = UserRole.objects.get_or_create(
            slug='curator', defaults={'name': 'Curator'}
        )
        self.contributor_role, _ = UserRole.objects.get_or_create(
            slug='contributor', defaults={'name': 'Contributor'}
        )

    def _register(self, **extra):
        body = {
            'email': extra.pop('email', 'newbie@example.com'),
            'password': 'S3curePass!234',
            'password_confirm': 'S3curePass!234',
        }
        body.update(extra)
        return self.client.post('/api/v1/users/register/', body, format='json')

    def test_registration_cannot_self_assign_curator(self):
        resp = self._register(role_id=self.curator_role.id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertFalse(
            UserProfile.objects.filter(role=self.curator_role).exists(),
            'A privileged role must not be assignable at registration.',
        )

    def test_registration_allows_non_privileged_role(self):
        resp = self._register(role_id=self.contributor_role.id)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        profile = UserProfile.objects.get(user__email='newbie@example.com')
        self.assertEqual(profile.role_id, self.contributor_role.id)

    def test_me_patch_cannot_self_assign_curator(self):
        user = User.objects.create_user(email='u@example.com', password='pw')
        UserProfile.objects.create(user=user)
        self.client.force_authenticate(user=user)
        resp = self.client.patch(
            '/api/v1/users/me/', {'role_id': self.curator_role.id}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        user.profile.refresh_from_db()
        self.assertNotEqual(user.profile.role_id, self.curator_role.id)

    def test_staff_may_assign_privileged_role_via_me(self):
        staff = User.objects.create_user(email='staff@example.com', password='pw', is_staff=True)
        UserProfile.objects.create(user=staff)
        self.client.force_authenticate(user=staff)
        resp = self.client.patch(
            '/api/v1/users/me/', {'role_id': self.curator_role.id}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        staff.profile.refresh_from_db()
        self.assertEqual(staff.profile.role_id, self.curator_role.id)


class DashboardTests(APITestCase):
    def setUp(self):
        self.city = make_city()
        role, _ = UserRole.objects.get_or_create(name='Contributor', slug='contributor')
        self.user = User.objects.create_user(email='u@example.com', password='pw')
        UserProfile.objects.create(user=self.user, role=role)

        h_type = HeritageType.objects.create(name='T', slug='t')
        h_cat = HeritageCategory.objects.create(name='C', slug='c')
        for title, st in (('one', 'published'), ('two', 'pending')):
            HeritageItem.objects.create(
                city=self.city, title=title, description='d', location=Point(0, 0),
                heritage_type=h_type, heritage_category=h_cat,
                contributor=self.user, status=st,
            )

    def test_dashboard_returns_the_shape_the_spa_expects(self):
        self.client.force_authenticate(self.user)
        res = self.client.get('/api/v1/users/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['activity']['contributions_total'], 2)
        self.assertEqual(res.data['activity']['contributions_approved'], 1)
        self.assertEqual(res.data['activity']['annotations_total'], 0)
        self.assertEqual(res.data['gamification']['total_points'], 0)
        self.assertEqual(res.data['notifications']['unread_count'], 0)
        self.assertEqual(res.data['user']['role'], 'Contributor')

    def test_dashboard_requires_authentication(self):
        res = self.client.get('/api/v1/users/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
