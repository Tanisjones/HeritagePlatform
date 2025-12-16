from rest_framework import serializers
from .models import HeritageRoute, RouteStop, UserRouteProgress, RouteRating
from apps.heritage.serializers import HeritageItemListSerializer


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

    class Meta:
        model = RouteStop
        fields = [
            'id', 'heritage_item', 'heritage_item_id', 'order',
            'arrival_instructions', 'suggested_time'
        ]
        read_only_fields = ['id']


class RouteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for route list views."""
    creator = UserPublicSerializer(read_only=True)
    stop_count = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = HeritageRoute
        fields = [
            'id', 'title', 'description', 'theme', 'difficulty',
            'estimated_duration', 'distance', 'is_official', 'status',
            'creator', 'stop_count', 'view_count', 'completion_count',
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
    user_progress = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()

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

    class Meta:
        model = HeritageRoute
        fields = [
            'title', 'description', 'theme', 'difficulty',
            'estimated_duration', 'distance', 'path',
            'wheelchair_accessible', 'public_transit_accessible',
            'accessibility_notes', 'best_season', 'estimated_cost',
            'cost_notes', 'available_languages', 'stops'
        ]

    def create(self, validated_data):
        """Create route with nested stops."""
        stops_data = validated_data.pop('stops', [])
        route = HeritageRoute.objects.create(**validated_data)

        # Create stops
        for stop_data in stops_data:
            heritage_item_data = stop_data.pop('heritage_item', {})
            heritage_item_id = heritage_item_data.get('id')
            if heritage_item_id:
                from apps.heritage.models import HeritageItem
                try:
                    heritage_item = HeritageItem.objects.get(id=heritage_item_id)
                    RouteStop.objects.create(
                        route=route,
                        heritage_item=heritage_item,
                        **stop_data
                    )
                except HeritageItem.DoesNotExist:
                    pass  # Skip invalid heritage items

        return route

    def update(self, instance, validated_data):
        """Update route and optionally replace stops."""
        stops_data = validated_data.pop('stops', None)

        # Update route fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If stops data provided, replace all stops
        if stops_data is not None:
            instance.stops.all().delete()
            for stop_data in stops_data:
                heritage_item_data = stop_data.pop('heritage_item', {})
                heritage_item_id = heritage_item_data.get('id')
                if heritage_item_id:
                    from apps.heritage.models import HeritageItem
                    try:
                        heritage_item = HeritageItem.objects.get(id=heritage_item_id)
                        RouteStop.objects.create(
                            route=instance,
                            heritage_item=heritage_item,
                            **stop_data
                        )
                    except HeritageItem.DoesNotExist:
                        pass  # Skip invalid heritage items

        return instance
