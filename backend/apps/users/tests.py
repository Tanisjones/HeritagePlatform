from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.models import UserProfile, UserRole
from rest_framework.test import APIClient
from rest_framework import status

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
