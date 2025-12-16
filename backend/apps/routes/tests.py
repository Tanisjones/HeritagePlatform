from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.contrib.gis.geos import Point
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish
from apps.routes.models import HeritageRoute, RouteStop, UserRouteProgress, RouteRating

User = get_user_model()

class RouteViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.creator = User.objects.create_user(username='creator', password='password', email='creator@example.com')
        self.curator = User.objects.create_user(username='curator', password='password', email='curator@example.com', is_staff=True)
        self.user = User.objects.create_user(username='user', password='password', email='user@example.com')
        self.other_user = User.objects.create_user(username='other', password='password', email='other@example.com')
        
        # Create heritage item dependencies
        self.type = HeritageType.objects.create(name='Type', slug='type')
        self.category = HeritageCategory.objects.create(name='Category', slug='category')
        self.parish = Parish.objects.create(name='Parish')
        
        # Create HeritageItems for stops
        self.item1 = HeritageItem.objects.create(
            title='Item 1', description='Desc 1', heritage_type=self.type, 
            heritage_category=self.category, parish=self.parish, location=Point(0, 0, srid=4326)
        )
        self.item2 = HeritageItem.objects.create(
            title='Item 2', description='Desc 2', heritage_type=self.type, 
            heritage_category=self.category, parish=self.parish, location=Point(1, 1, srid=4326)
        )
        self.item3 = HeritageItem.objects.create(
            title='Item 3', description='Desc 3', heritage_type=self.type, 
            heritage_category=self.category, parish=self.parish, location=Point(2, 2, srid=4326)
        )
        
        # Base route data
        self.route_data = {
            'title': 'Test Route',
            'description': 'Test Description',
            'difficulty': 'easy',
            'stops': [
                {'heritage_item_id': str(self.item1.id), 'order': 1, 'arrival_instructions': 'Start here', 'suggested_time': '00:30:00'},
                {'heritage_item_id': str(self.item2.id), 'order': 2}
            ]
        }

    # --- CRUD Tests ---
    def test_create_route(self):
        """Test creating a route with stops."""
        self.client.force_authenticate(user=self.creator)
        response = self.client.post('/api/v1/routes/', self.route_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HeritageRoute.objects.count(), 1)
        route = HeritageRoute.objects.first()
        self.assertEqual(route.title, 'Test Route')
        self.assertEqual(route.creator, self.creator)
        self.assertEqual(route.status, 'draft')
        self.assertEqual(route.stops.count(), 2)

    def test_update_route(self):
        """Test updating route fields and modifying stops."""
        route = HeritageRoute.objects.create(title='Old Title', creator=self.creator, status='draft')
        RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        
        self.client.force_authenticate(user=self.creator)
        update_data = {
            'title': 'New Title',
            'stops': [
                {'heritage_item_id': str(self.item2.id), 'order': 1} # Changing stops completely
            ]
        }
        response = self.client.patch(f'/api/v1/routes/{route.id}/', update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.title, 'New Title')
        self.assertEqual(route.stops.count(), 1)
        self.assertEqual(route.stops.first().heritage_item, self.item2)

    def test_delete_route(self):
        """Test deleting a route."""
        route = HeritageRoute.objects.create(title='To Delete', creator=self.creator, status='draft')
        
        self.client.force_authenticate(user=self.creator)
        response = self.client.delete(f'/api/v1/routes/{route.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(HeritageRoute.objects.count(), 0)

    def test_list_routes_permissions(self):
        """Test valid visibility of routes."""
        # Published route (visible to all)
        HeritageRoute.objects.create(title='Published', creator=self.user, status='published')
        # Draft route (visible only to creator)
        HeritageRoute.objects.create(title='Draft', creator=self.creator, status='draft')
        
        # Unauthenticated - see only published
        self.client.logout()
        response = self.client.get('/api/v1/routes/')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Published')
        
        # Authenticated as creator - see published + own draft
        self.client.force_authenticate(user=self.creator)
        response = self.client.get('/api/v1/routes/')
        self.assertEqual(len(response.data['results']), 2)

    def test_increment_view_count_on_retrieve(self):
        """Test retrieving a route increments view_count."""
        route = HeritageRoute.objects.create(title='Views', creator=self.creator, status='published', view_count=0)
        response = self.client.get(f'/api/v1/routes/{route.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.view_count, 1)

    # --- Governance Tests ---
    def test_submit_for_review(self):
        """Test submitting a draft route."""
        route = HeritageRoute.objects.create(title='Draft', creator=self.creator, status='draft')
        self.client.force_authenticate(user=self.creator)
        
        response = self.client.post(f'/api/v1/routes/{route.id}/submit_for_review/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.status, 'pending')

    def test_submit_for_review_not_owner(self):
        """Test non-owner cannot submit route for review (not found due to queryset filtering)."""
        route = HeritageRoute.objects.create(title='Draft', creator=self.creator, status='draft')
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(f'/api/v1/routes/{route.id}/submit_for_review/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_approve_route(self):
        """Test curator approving a route."""
        route = HeritageRoute.objects.create(title='Pending', creator=self.creator, status='pending')
        self.client.force_authenticate(user=self.curator)
        
        response = self.client.post(f'/api/v1/routes/{route.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.status, 'published')
        self.assertEqual(route.curator, self.curator)

    def test_approve_requires_staff(self):
        """Test approve endpoint requires staff."""
        route = HeritageRoute.objects.create(title='Pending', creator=self.creator, status='pending')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/routes/{route.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_route(self):
        """Test curator rejecting a route."""
        route = HeritageRoute.objects.create(title='Pending', creator=self.creator, status='pending')
        self.client.force_authenticate(user=self.curator)
        
        response = self.client.post(f'/api/v1/routes/{route.id}/reject/', {'feedback': 'Bad quality'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.status, 'rejected')
        self.assertEqual(route.curator_feedback, 'Bad quality')

    def test_request_changes(self):
        """Test curator requesting changes."""
        route = HeritageRoute.objects.create(title='Pending', creator=self.creator, status='pending')
        self.client.force_authenticate(user=self.curator)
        
        response = self.client.post(f'/api/v1/routes/{route.id}/request-changes/', {'feedback': 'Add more stops'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.status, 'changes_requested')
        self.assertEqual(route.curator_feedback, 'Add more stops')

    # --- Progress Tests ---
    def test_start_route(self):
        """Test starting a route."""
        route = HeritageRoute.objects.create(title='Walk', creator=self.creator, status='published')
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(f'/api/v1/routes/{route.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserRouteProgress.objects.filter(user=self.user, route=route).exists())

    def test_start_route_not_published(self):
        """Test starting a non-published route fails (not found for regular user)."""
        route = HeritageRoute.objects.create(title='Draft', creator=self.creator, status='draft')
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(f'/api/v1/routes/{route.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_check_in_stop(self):
        """Test checking in to a stop."""
        route = HeritageRoute.objects.create(title='Walk', creator=self.creator, status='published')
        stop1 = RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        UserRouteProgress.objects.create(user=self.user, route=route) # Started
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/routes/{route.id}/check-in/', {'stop_id': stop1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        progress = UserRouteProgress.objects.get(user=self.user, route=route)
        self.assertEqual(progress.current_stop, stop1)
        self.assertTrue(progress.visited_stops.filter(id=stop1.id).exists())

    def test_skip_stop(self):
        """Test skipping a stop."""
        route = HeritageRoute.objects.create(title='Walk', creator=self.creator, status='published')
        stop1 = RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        stop2 = RouteStop.objects.create(route=route, heritage_item=self.item2, order=2)
        progress = UserRouteProgress.objects.create(user=self.user, route=route)
        
        self.client.force_authenticate(user=self.user)
        # Skip stop 1
        response = self.client.post(f'/api/v1/routes/{route.id}/skip-stop/', {'stop_id': stop1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        progress.refresh_from_db()
        self.assertTrue(progress.visited_stops.filter(id=stop1.id).exists()) # Marked as visited
        self.assertEqual(progress.current_stop, stop2) # Advanced to next

    def test_complete_route(self):
        """Test completing a route."""
        route = HeritageRoute.objects.create(title='Walk', creator=self.creator, status='published', completion_count=0)
        UserRouteProgress.objects.create(user=self.user, route=route)
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/routes/{route.id}/complete/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        progress = UserRouteProgress.objects.get(user=self.user, route=route)
        self.assertIsNotNone(progress.completed_at)
        
        route.refresh_from_db()
        self.assertEqual(route.completion_count, 1)

    def test_restart_route_after_completion(self):
        """Test user can restart a route after completing it."""
        route = HeritageRoute.objects.create(title='Restart', creator=self.creator, status='published')
        stop1 = RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        progress = UserRouteProgress.objects.create(user=self.user, route=route, completed_at=timezone.now())
        progress.visited_stops.add(stop1)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/routes/{route.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        progress.refresh_from_db()
        self.assertIsNone(progress.completed_at)
        self.assertEqual(progress.visited_stops.count(), 0)

    def test_active_routes_filter(self):
        """Test filtering active routes."""
        route1 = HeritageRoute.objects.create(title='Active', creator=self.creator, status='published')
        route2 = HeritageRoute.objects.create(title='Completed', creator=self.creator, status='published')
        
        # Active progress
        UserRouteProgress.objects.create(user=self.user, route=route1)
        # Completed progress
        UserRouteProgress.objects.create(user=self.user, route=route2, completed_at=timezone.now())
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/routes/active-routes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(route1.id))

    # --- Rating Tests ---
    def test_rate_route(self):
        """Test rating a route."""
        route = HeritageRoute.objects.create(title='Rate Me', creator=self.creator, status='published')
        
        self.client.force_authenticate(user=self.user)
        data = {'rating': 5, 'comment': 'Great route!'}
        response = self.client.post(f'/api/v1/routes/{route.id}/rate/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(RouteRating.objects.filter(user=self.user, route=route, rating=5).exists())
        
        route.refresh_from_db()
        self.assertEqual(route.average_rating, 5.0)

    def test_average_rating_multiple_users(self):
        """Test average_rating is recalculated across users."""
        route = HeritageRoute.objects.create(title='Average', creator=self.creator, status='published')
        self.client.force_authenticate(user=self.user)
        self.client.post(f'/api/v1/routes/{route.id}/rate/', {'rating': 5, 'comment': ''})
        self.client.force_authenticate(user=self.other_user)
        self.client.post(f'/api/v1/routes/{route.id}/rate/', {'rating': 3, 'comment': ''})
        route.refresh_from_db()
        self.assertEqual(route.average_rating, 4.0)

    def test_get_my_rating(self):
        """Test retrieving my own rating."""
        route = HeritageRoute.objects.create(title='Rate Me', creator=self.creator, status='published')
        RouteRating.objects.create(user=self.user, route=route, rating=4)
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/routes/{route.id}/rate/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rating'], 4)

    def test_get_my_rating_none(self):
        """Test retrieving rating when none exists."""
        route = HeritageRoute.objects.create(title='No Rate', creator=self.creator, status='published')
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/routes/{route.id}/rate/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

class RouteProgressViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user', password='password', email='user@example.com')
        self.other = User.objects.create_user(username='other', password='password', email='other@example.com')
        self.route = HeritageRoute.objects.create(title='Route', status='published')
        
    def test_list_my_progress(self):
        """Test user can only see their own progress."""
        UserRouteProgress.objects.create(user=self.user, route=self.route)
        UserRouteProgress.objects.create(user=self.other, route=self.route)
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/route-progress/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['route'], self.route.id)
