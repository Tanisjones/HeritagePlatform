from rest_framework import serializers
from .models import Badge, Level, UserBadge, PointTransaction

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ['id', 'name', 'description', 'icon', 'category', 'points_value', 'requirements']

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['id', 'number', 'name', 'min_points', 'max_points', 'benefits']

class UserBadgeSerializer(serializers.ModelSerializer):
    # Nest the badge so clients get its name/icon, not a bare PK.
    badge = BadgeSerializer(read_only=True)

    class Meta:
        model = UserBadge
        fields = ['id', 'user', 'badge', 'earned_at']

class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTransaction
        fields = ['id', 'user', 'points', 'reason', 'reference_type', 'reference_id', 'created_at']
