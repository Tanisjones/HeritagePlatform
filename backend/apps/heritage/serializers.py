from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer, GeometryField
from .models import HeritageItem, HeritageCategory, HeritageType, Parish, MediaFile, HeritageRelation, Annotation
from apps.education.serializers import LOMGeneralSerializer


class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = '__all__'


class MediaFileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = '__all__'
        read_only_fields = ['uploaded_by']


class HeritageCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HeritageCategory
        fields = '__all__'


class HeritageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeritageType
        fields = '__all__'


class ParishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parish
        fields = '__all__'


class HeritageItemSerializer(serializers.ModelSerializer):
    """
    Standard serializer for heritage items (basic management).
    """
    class Meta:
        model = HeritageItem
        fields = '__all__'


class HeritageItemListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for list views.
    Includes related foreign keys as nested objects for frontend display.
    """
    heritage_type = HeritageTypeSerializer(read_only=True)
    heritage_category = HeritageCategorySerializer(read_only=True)
    parish = ParishSerializer(read_only=True)
    images = MediaFileSerializer(many=True, read_only=True)
    main_image = MediaFileSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    lom_metadata = serializers.SerializerMethodField()

    class Meta:
        model = HeritageItem
        fields = [
            'id', 'title', 'description', 'location', 'address', 
            'status', 'heritage_type', 'heritage_category', 
            'parish', 'images', 'main_image', 'primary_image', 'created_at',
            'lom_metadata'
        ]

    def get_primary_image(self, obj):
        if obj.main_image:
            return self.context['request'].build_absolute_uri(obj.main_image.file.url)
        first_image = obj.images.first()
        if first_image:
            return self.context['request'].build_absolute_uri(first_image.file.url)
        return None

    def get_lom_metadata(self, obj):
        if hasattr(obj, 'lom_general'):
            return LOMGeneralSerializer(obj.lom_general).data
        return None


class HeritageItemDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for detailed view of a heritage item.
    Includes all media files (images, audio, video, documents) and full LOM metadata.
    """
    heritage_type = HeritageTypeSerializer(read_only=True)
    heritage_category = HeritageCategorySerializer(read_only=True)
    parish = ParishSerializer(read_only=True)
    images = MediaFileSerializer(many=True, read_only=True)
    main_image = MediaFileSerializer(read_only=True)
    audio = MediaFileSerializer(many=True, read_only=True)
    video = MediaFileSerializer(many=True, read_only=True)
    documents = MediaFileSerializer(many=True, read_only=True)
    lom_metadata = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    # Add contributor info if needed, but keeping it simple for now

    class Meta:
        model = HeritageItem
        fields = '__all__'

    def get_lom_metadata(self, obj):
        if hasattr(obj, 'lom_general'):
            return LOMGeneralSerializer(obj.lom_general).data
        return None

    def get_primary_image(self, obj):
        if obj.main_image:
            return self.context['request'].build_absolute_uri(obj.main_image.file.url)
        first_image = obj.images.first()
        if first_image:
            return self.context['request'].build_absolute_uri(first_image.file.url)
        return None


class HeritageItemCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating heritage items.
    Handles GeoJSON geometry fields.
    """
    location = GeometryField()

    class Meta:
        model = HeritageItem
        fields = '__all__'


class HeritageItemContributionSerializer(serializers.ModelSerializer):
    """
    Serializer used by the contribution wizard.
    Simplifies the creation process for end-users.
    """
    location = GeometryField()

    class Meta:
        model = HeritageItem
        fields = '__all__'


class HeritageRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeritageRelation
        fields = '__all__'


class HeritageItemGeoJSONSerializer(GeoFeatureModelSerializer):
    location = GeometryField()
    primary_image = serializers.SerializerMethodField()
    heritage_type = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    heritage_category = serializers.SlugRelatedField(slug_field='slug', read_only=True)

    class Meta:
        model = HeritageItem
        geo_field = 'location'
        fields = '__all__'

    def get_primary_image(self, obj):
        if obj.main_image:
            return self.context['request'].build_absolute_uri(obj.main_image.file.url)
        first_image = obj.images.first()
        if first_image:
            return self.context['request'].build_absolute_uri(first_image.file.url)
        return None


class AnnotationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Annotation
        fields = [
            'id', 'heritage_item', 'user', 'user_email', 'content',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Auto-assign the current user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)