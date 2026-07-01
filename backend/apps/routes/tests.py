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
        # The response reports the awards granted by the completion signal.
        self.assertIn('awards', response.data)
        self.assertIn('points', response.data['awards'])
        self.assertIn('badges', response.data['awards'])
        self.assertGreaterEqual(response.data['awards']['points'], 0)

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

class RouteF3Tests(TestCase):
    """F3: non-destructive stop diff, geometry generation, exports, nearby, archive, geo check-in."""

    def setUp(self):
        self.client = APIClient()
        self.creator = User.objects.create_user(username='c', password='pw', email='c@example.com')
        self.user = User.objects.create_user(username='u', password='pw', email='u@example.com')
        self.type = HeritageType.objects.create(name='T', slug='t')
        self.category = HeritageCategory.objects.create(name='C', slug='c')
        self.parish = Parish.objects.create(name='P')
        # Riobamba-ish coordinates so distances are realistic (metres, not degrees).
        self.item1 = HeritageItem.objects.create(
            title='Catedral', description='d', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish,
            location=Point(-78.6483, -1.6742, srid=4326))
        self.item2 = HeritageItem.objects.create(
            title='Parque', description='d', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish,
            location=Point(-78.6470, -1.6738, srid=4326))
        self.item3 = HeritageItem.objects.create(
            title='Museo', description='d', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish,
            location=Point(-78.6455, -1.6725, srid=4326))

    def test_update_preserves_progress_on_surviving_stops(self):
        """The crux: editing stops must NOT orphan an in-progress user's FKs."""
        route = HeritageRoute.objects.create(title='R', creator=self.creator, status='published')
        s1 = RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        s2 = RouteStop.objects.create(route=route, heritage_item=self.item2, order=2)
        s3 = RouteStop.objects.create(route=route, heritage_item=self.item3, order=3)

        progress = UserRouteProgress.objects.create(user=self.user, route=route, current_stop=s2)
        progress.visited_stops.add(s1, s2)

        # Reorder (swap 1&2), keep s2, drop s3, add nothing new. Send stop ids so
        # the diff matches by identity.
        self.client.force_authenticate(user=self.creator)
        payload = {'stops': [
            {'id': str(s2.id), 'heritage_item_id': str(self.item2.id), 'order': 1},
            {'id': str(s1.id), 'heritage_item_id': str(self.item1.id), 'order': 2},
        ]}
        resp = self.client.patch(f'/api/v1/routes/{route.id}/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # s1 and s2 keep their PKs; s3 is gone.
        self.assertTrue(RouteStop.objects.filter(id=s1.id).exists())
        self.assertTrue(RouteStop.objects.filter(id=s2.id).exists())
        self.assertFalse(RouteStop.objects.filter(id=s3.id).exists())

        progress.refresh_from_db()
        # current_stop (s2) survived and visited_stops still reference the kept rows.
        self.assertEqual(progress.current_stop_id, s2.id)
        visited = set(progress.visited_stops.values_list('id', flat=True))
        self.assertEqual(visited, {s1.id, s2.id})
        # Order was reassigned.
        self.assertEqual(RouteStop.objects.get(id=s2.id).order, 1)
        self.assertEqual(RouteStop.objects.get(id=s1.id).order, 2)

    def test_duplicate_heritage_item_in_stops_is_rejected(self):
        """A route cannot list the same heritage item twice (would collapse silently)."""
        self.client.force_authenticate(user=self.creator)
        payload = {
            'title': 'Dup', 'description': 'd',
            'stops': [
                {'heritage_item_id': str(self.item1.id), 'order': 1},
                {'heritage_item_id': str(self.item1.id), 'order': 2},
            ],
        }
        resp = self.client.post('/api/v1/routes/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_shrinking_below_two_stops_clears_geometry(self):
        """Editing down to <2 stops clears the previously auto-generated geometry."""
        self.client.force_authenticate(user=self.creator)
        create = self.client.post('/api/v1/routes/', {
            'title': 'Shrink', 'description': 'd',
            'stops': [
                {'heritage_item_id': str(self.item1.id), 'order': 1},
                {'heritage_item_id': str(self.item2.id), 'order': 2},
            ],
        }, format='json')
        route = HeritageRoute.objects.get(title='Shrink')
        self.assertIsNotNone(route.path)  # generated on create

        # Keep only one stop.
        self.client.patch(f'/api/v1/routes/{route.id}/', {
            'stops': [{'heritage_item_id': str(self.item1.id), 'order': 1}],
        }, format='json')
        route.refresh_from_db()
        self.assertIsNone(route.path)
        self.assertIsNone(route.distance)

    def test_create_autogenerates_path_and_distance(self):
        """With ROUTING_PROVIDER=straight_line (default), a path + distance are derived."""
        self.client.force_authenticate(user=self.creator)
        payload = {
            'title': 'Auto', 'description': 'd', 'difficulty': 'easy',
            'stops': [
                {'heritage_item_id': str(self.item1.id), 'order': 1},
                {'heritage_item_id': str(self.item2.id), 'order': 2},
                {'heritage_item_id': str(self.item3.id), 'order': 3},
            ],
        }
        resp = self.client.post('/api/v1/routes/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        route = HeritageRoute.objects.get(id=resp.data['id']) if 'id' in resp.data else HeritageRoute.objects.get(title='Auto')
        self.assertIsNotNone(route.path)
        self.assertEqual(len(route.path.coords), 3)
        self.assertIsNotNone(route.distance)
        self.assertGreater(route.distance, 0)
        self.assertIsNotNone(route.estimated_duration)

    def test_client_supplied_distance_is_respected(self):
        """An explicit distance is not overwritten by generation."""
        self.client.force_authenticate(user=self.creator)
        payload = {
            'title': 'Manual', 'description': 'd', 'distance': 9.9,
            'stops': [
                {'heritage_item_id': str(self.item1.id), 'order': 1},
                {'heritage_item_id': str(self.item2.id), 'order': 2},
            ],
        }
        resp = self.client.post('/api/v1/routes/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        route = HeritageRoute.objects.get(title='Manual')
        self.assertEqual(route.distance, 9.9)

    def test_export_gpx(self):
        route = HeritageRoute.objects.create(title='Ruta GPX', creator=self.creator, status='published')
        RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        RouteStop.objects.create(route=route, heritage_item=self.item2, order=2)
        resp = self.client.get(f'/api/v1/routes/{route.id}/export-gpx/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/gpx+xml')
        self.assertIn('attachment', resp['Content-Disposition'])
        from xml.etree import ElementTree as ET
        root = ET.fromstring(resp.content)
        self.assertTrue(root.tag.endswith('gpx'))

    def test_export_kml(self):
        route = HeritageRoute.objects.create(title='Ruta KML', creator=self.creator, status='published')
        RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        RouteStop.objects.create(route=route, heritage_item=self.item2, order=2)
        resp = self.client.get(f'/api/v1/routes/{route.id}/export-kml/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/vnd.google-earth.kml+xml')
        from xml.etree import ElementTree as ET
        ET.fromstring(resp.content)  # parses => well-formed

    def test_nearby_returns_route_with_close_stop(self):
        route = HeritageRoute.objects.create(title='Near', creator=self.creator, status='published')
        RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        RouteStop.objects.create(route=route, heritage_item=self.item2, order=2)
        # A far-away route should be excluded.
        far = HeritageRoute.objects.create(title='Far', creator=self.creator, status='published')
        far_item = HeritageItem.objects.create(
            title='Far item', description='d', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish, location=Point(10, 10, srid=4326))
        RouteStop.objects.create(route=far, heritage_item=far_item, order=1)

        resp = self.client.get('/api/v1/routes/nearby/', {'latitude': -1.6740, 'longitude': -78.6480, 'radius': 2})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = {r['title'] for r in resp.data['results']}
        self.assertIn('Near', titles)
        self.assertNotIn('Far', titles)

    def test_archive_by_creator(self):
        route = HeritageRoute.objects.create(title='Arch', creator=self.creator, status='published')
        self.client.force_authenticate(user=self.creator)
        resp = self.client.post(f'/api/v1/routes/{route.id}/archive/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        route.refresh_from_db()
        self.assertEqual(route.status, 'archived')

    def test_archive_rejected_for_draft(self):
        route = HeritageRoute.objects.create(title='Draft', creator=self.creator, status='draft')
        self.client.force_authenticate(user=self.creator)
        resp = self.client.post(f'/api/v1/routes/{route.id}/archive/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_in_far_coords_warns_but_succeeds(self):
        route = HeritageRoute.objects.create(title='Geo', creator=self.creator, status='published')
        stop = RouteStop.objects.create(route=route, heritage_item=self.item1, order=1)
        UserRouteProgress.objects.create(user=self.user, route=route)
        self.client.force_authenticate(user=self.user)
        # Coordinates far from item1 -> warning, but check-in still recorded.
        resp = self.client.post(
            f'/api/v1/routes/{route.id}/check-in/',
            {'stop_id': str(stop.id), 'latitude': 0.0, 'longitude': 0.0},
            format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get('warning'), 'far_from_stop')
        self.assertIn('distance_m', resp.data)
        progress = UserRouteProgress.objects.get(user=self.user, route=route)
        self.assertTrue(progress.visited_stops.filter(id=stop.id).exists())


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
