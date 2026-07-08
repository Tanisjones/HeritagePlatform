import json
from datetime import timedelta

from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from rest_framework import serializers
from rest_framework_gis.serializers import GeometryField

from .models import HeritageRoute, RouteStop, UserRouteProgress, RouteRating, RouteTheme
from .routing import build_path_for_stops
from apps.cities.serializers import CityRefSerializer
from apps.heritage.serializers import HeritageItemListSerializer


class RouteThemeSerializer(serializers.ModelSerializer):
    """Curated route theme (H.2). Read shape for the picker + nested route reads."""

    class Meta:
        model = RouteTheme
        fields = ['id', 'name', 'slug', 'description', 'color']


class UserPublicSerializer(serializers.Serializer):
    """Lightweight user info for creator display."""
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        """Custom representation for user data."""
        return {
            'id': instance.id,
            'email': instance.email,
            'name': f"{instance.first_name} {instance.last_name}".strip() or instance.email,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
        }


class RouteStopSerializer(serializers.ModelSerializer):
    """Serializer for RouteStop with nested heritage item preview."""
    heritage_item = HeritageItemListSerializer(read_only=True)
    heritage_item_id = serializers.UUIDField(write_only=True, source='heritage_item.id')
    # Optional-writable so a stop keeps a stable identity across route edits: the
    # non-destructive diff in RouteCreateSerializer.update() matches on it (see
    # _diff_stops) to update rows in place, preserving UserRouteProgress FKs.
    id = serializers.UUIDField(required=False)
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = RouteStop
        fields = [
            'id', 'heritage_item', 'heritage_item_id', 'order',
            'arrival_instructions', 'suggested_time', 'audio_url'
        ]

    def get_audio_url(self, obj):
        """Absolute URL of the stop's first audio file (for the audioguide), if any."""
        audio = obj.heritage_item.audio.first()
        if not audio or not getattr(audio, 'file', None):
            return None
        request = self.context.get('request')
        url = audio.file.url
        return request.build_absolute_uri(url) if request else url


class RouteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for route list views."""
    creator = UserPublicSerializer(read_only=True)
    stop_count = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    theme_category_detail = RouteThemeSerializer(source='theme_category', read_only=True)
    city = CityRefSerializer(read_only=True)

    class Meta:
        model = HeritageRoute
        fields = [
            'id', 'title', 'description', 'theme', 'theme_category', 'theme_category_detail',
            'difficulty',
            'estimated_duration', 'distance', 'is_official', 'status',
            'creator', 'city', 'stop_count', 'view_count', 'completion_count',
            'average_rating', 'wheelchair_accessible', 'best_season',
            'created_at', 'is_active'
        ]

    def get_stop_count(self, obj):
        """Return the number of stops in this route."""
        return obj.stops.count()

    def get_is_active(self, obj):
        """Check if the current user has an active progress on this route."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.user_progress.filter(
            user=request.user,
            completed_at__isnull=True
        ).exists()


class UserRouteProgressSerializer(serializers.ModelSerializer):
    """Serializer for tracking user progress through a route."""
    visited_stop_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=RouteStop.objects.all(),
        source='visited_stops',
        write_only=True,
        required=False
    )
    visited_stops = RouteStopSerializer(many=True, read_only=True)
    current_stop = RouteStopSerializer(read_only=True)

    class Meta:
        model = UserRouteProgress
        fields = [
            'id', 'route', 'started_at', 'completed_at',
            'current_stop', 'visited_stops', 'visited_stop_ids'
        ]
        read_only_fields = ['id', 'started_at']


class RouteRatingSerializer(serializers.ModelSerializer):
    """Serializer for route ratings."""
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = RouteRating
        fields = [
            'id', 'route', 'user', 'rating', 'comment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'route']


class RouteDetailSerializer(serializers.ModelSerializer):
    """Full route information serializer with all relationships."""
    creator = UserPublicSerializer(read_only=True)
    curator = UserPublicSerializer(read_only=True)
    stops = RouteStopSerializer(many=True, read_only=True)
    # Emit the LineString path as GeoJSON (the FE expects GeoJSONLineString).
    path = GeometryField(read_only=True)
    user_progress = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    theme_category_detail = RouteThemeSerializer(source='theme_category', read_only=True)
    city = CityRefSerializer(read_only=True)

    class Meta:
        model = HeritageRoute
        fields = '__all__'

    def get_user_progress(self, obj):
        """Get the current user's progress on this route if any."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        progress = obj.user_progress.filter(user=request.user).first()
        if not progress:
            return None
        return UserRouteProgressSerializer(progress, context=self.context).data

    def get_user_rating(self, obj):
        """Get the current user's rating for this route if any."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        rating = obj.ratings.filter(user=request.user).first()
        if not rating:
            return None
        return RouteRatingSerializer(rating, context=self.context).data


class RouteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating routes."""
    stops = RouteStopSerializer(many=True, required=False)
    # Accept a client-supplied path as GeoJSON. When omitted, it is auto-generated
    # from the ordered stops on save (see _apply_generated_geometry).
    path = GeometryField(required=False, allow_null=True)
    # Server-assigned from the request city context (see perform_create).
    city = CityRefSerializer(read_only=True)

    class Meta:
        model = HeritageRoute
        fields = [
            'title', 'description', 'theme', 'theme_category', 'difficulty',
            'estimated_duration', 'distance', 'path',
            'wheelchair_accessible', 'public_transit_accessible',
            'accessibility_notes', 'best_season', 'estimated_cost',
            'cost_notes', 'available_languages', 'stops', 'city'
        ]

    @staticmethod
    def _normalize_stops(stops_data):
        """
        Flatten each nested-serializer stop dict into
        ``(stop_id, heritage_item_id, fields)`` where ``fields`` holds the writable
        RouteStop attributes. ``heritage_item_id`` arrives nested under
        ``heritage_item`` because RouteStopSerializer sources it there. Rejects a
        payload that lists the same heritage item twice (``unique_together`` would
        otherwise silently collapse them to one row).
        """
        normalized = []
        seen_items = set()
        for position, raw in enumerate(stops_data):
            raw = dict(raw)
            heritage_item = raw.pop('heritage_item', {}) or {}
            heritage_item_id = heritage_item.get('id')
            if heritage_item_id is not None:
                if heritage_item_id in seen_items:
                    raise serializers.ValidationError(
                        {'stops': 'A heritage item can only appear once in a route.'}
                    )
                seen_items.add(heritage_item_id)
            stop_id = raw.pop('id', None)
            fields = {
                k: raw[k]
                for k in ('arrival_instructions', 'suggested_time')
                if k in raw
            }
            # Honor a client-supplied order; otherwise fall back to list position
            # (what the drag-and-drop builder relies on).
            fields['order'] = raw.get('order', position + 1)
            normalized.append((stop_id, heritage_item_id, fields))
        return normalized

    def _diff_stops(self, route, stops_data):
        """
        Reconcile ``route``'s stops against ``stops_data`` WITHOUT deleting and
        recreating everything: match by explicit stop id, else by heritage_item
        (unique per route), update matched rows in place — preserving their PKs so
        UserRouteProgress.current_stop / visited_stops survive an edit — create
        genuinely new stops, and delete only the ones the user removed.

        ``order`` has no DB-unique constraint, so a single upsert pass is safe
        (no transient-collision parking needed).
        """
        from apps.heritage.models import HeritageItem

        existing = {s.id: s for s in route.stops.all()}
        by_item = {s.heritage_item_id: s for s in existing.values()}
        normalized = self._normalize_stops(stops_data)

        def match(stop_id, heritage_item_id):
            if stop_id and stop_id in existing:
                return existing[stop_id]
            if heritage_item_id and heritage_item_id in by_item:
                return by_item[heritage_item_id]
            return None

        with transaction.atomic():
            seen_ids = set()
            for stop_id, heritage_item_id, fields in normalized:
                found = match(stop_id, heritage_item_id)
                if found is not None:
                    for key, value in fields.items():
                        setattr(found, key, value)
                    found.save()
                    seen_ids.add(found.id)
                elif heritage_item_id:
                    heritage_item = HeritageItem.objects.filter(id=heritage_item_id).first()
                    if heritage_item:
                        created = RouteStop.objects.create(
                            route=route, heritage_item=heritage_item, **fields
                        )
                        seen_ids.add(created.id)

            # Delete only stops the user actually dropped.
            for stop_id, stop in existing.items():
                if stop_id not in seen_ids:
                    stop.delete()

    def _apply_generated_geometry(self, route, *, client_supplied):
        """
        Populate path/distance/estimated_duration from the ordered stops via the
        routing provider. Any field the client sent explicitly wins and is left
        untouched; the rest are (re)generated so editing the stop list keeps
        geometry in sync. If the stops can no longer produce a path (fewer than
        two locatable stops), the previously-generated values are CLEARED rather
        than left stale.

        Runs OUTSIDE the create/update transaction: the routing provider may make
        an HTTP call (OSRM), which must not hold row locks. ``client_supplied`` is
        the set of these field names present in the request.

        Returns the list of fields it changed (for the caller to persist).
        """
        result = build_path_for_stops(route.stops.all().order_by('order'))

        update_fields = []
        if 'path' not in client_supplied:
            route.path = (
                GEOSGeometry(json.dumps(result.geometry), srid=4326) if result else None
            )
            update_fields.append('path')
            # Turn-by-turn steps travel with the generated path (empty for the
            # straight-line fallback, which has none).
            route.turn_by_turn = (
                [
                    {
                        'instruction': s.instruction,
                        'distance_m': s.distance_m,
                        'duration_s': s.duration_s,
                        'name': s.name,
                    }
                    for s in result.steps
                ]
                if result
                else []
            )
            update_fields.append('turn_by_turn')
        if 'distance' not in client_supplied:
            route.distance = round(result.distance_m / 1000.0, 3) if result else None
            update_fields.append('distance')
        if 'estimated_duration' not in client_supplied:
            route.estimated_duration = (
                timedelta(seconds=round(result.duration_s)) if result else None
            )
            update_fields.append('estimated_duration')

        if update_fields:
            route.save(update_fields=update_fields)

    @staticmethod
    def _client_geometry_fields(validated_data):
        """Which of path/distance/estimated_duration the client sent (non-null)."""
        return {
            name
            for name in ('path', 'distance', 'estimated_duration')
            if validated_data.get(name) is not None
        }

    @staticmethod
    def _denormalize_theme(route, *, theme_explicit):
        """Keep the legacy `theme` string in sync with the curated category so
        thematic search and theme-based gamification (which key off the string) keep
        working. The category is authoritative WHEN the client did not also send an
        explicit free-text `theme`: if a category is set, derive `theme` from its
        name (covers create, change, and re-derive). If the client explicitly sent a
        `theme` string, respect it (custom override). Clearing the category leaves
        the last string untouched (it may be an intentional free-text value)."""
        if route.theme_category_id and not theme_explicit:
            new_theme = route.theme_category.name
            if route.theme != new_theme:
                route.theme = new_theme
                route.save(update_fields=['theme'])

    def create(self, validated_data):
        """Create a route with nested stops, then auto-generate geometry."""
        stops_data = validated_data.pop('stops', [])
        theme_explicit = 'theme' in validated_data
        client_supplied = self._client_geometry_fields(validated_data)
        with transaction.atomic():
            route = HeritageRoute.objects.create(**validated_data)
            self._denormalize_theme(route, theme_explicit=theme_explicit)
            if stops_data:
                self._diff_stops(route, stops_data)
        # Routing (possible HTTP call) runs after the transaction commits.
        self._apply_generated_geometry(route, client_supplied=client_supplied)
        return route

    def update(self, instance, validated_data):
        """Update route fields + non-destructive stop diff, then regenerate geometry."""
        stops_data = validated_data.pop('stops', None)
        theme_explicit = 'theme' in validated_data
        client_supplied = self._client_geometry_fields(validated_data)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            self._denormalize_theme(instance, theme_explicit=theme_explicit)

            if stops_data is not None:
                self._diff_stops(instance, stops_data)
        # Routing (possible HTTP call) runs after the transaction commits.
        self._apply_generated_geometry(instance, client_supplied=client_supplied)
        return instance
