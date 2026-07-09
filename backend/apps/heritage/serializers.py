from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer, GeometryField
from .models import HeritageItem, HeritageCategory, HeritageType, Parish, MediaFile, HeritageRelation, Annotation, Tag
from apps.cities.request import get_request_city_or_default
from apps.cities.serializers import CityRefSerializer
from apps.education.serializers import LOMGeneralSerializer, LOMEducationalSerializer


class TagListField(serializers.Field):
    """
    Tags on the wire are a plain list of strings (["independencia", "barroco"]);
    internally they resolve to Tag rows. Returning Tag instances from
    to_internal_value lets ModelSerializer's default create/update handle the
    M2M .set() — no per-serializer plumbing. Unknown tags are created on the
    spot (free-form by design); a validation failure elsewhere can therefore
    leave an unused Tag row behind, which is harmless vocabulary.
    """
    MAX_TAGS = 10

    def to_representation(self, value):
        return [tag.name for tag in value.all()]

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError('Se esperaba una lista de etiquetas.')
        if len(data) > self.MAX_TAGS:
            raise serializers.ValidationError(f'Máximo {self.MAX_TAGS} etiquetas.')
        tags = []
        for raw in data:
            if not isinstance(raw, str):
                raise serializers.ValidationError('Cada etiqueta debe ser texto.')
            tag = Tag.get_or_create_normalized(raw)
            if tag is not None and tag not in tags:
                tags.append(tag)
        return tags


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'slug']


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
    city = CityRefSerializer(read_only=True)

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
    city = CityRefSerializer(read_only=True)
    images = MediaFileSerializer(many=True, read_only=True)
    main_image = MediaFileSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    lom_metadata = serializers.SerializerMethodField()
    tags = TagListField(read_only=True)

    class Meta:
        model = HeritageItem
        fields = [
            'id', 'title', 'description', 'location', 'address',
            'status', 'heritage_type', 'heritage_category',
            'parish', 'city', 'images', 'main_image', 'primary_image', 'created_at',
            'lom_metadata', 'tags'
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
            # Pass context so the request threads through: LOMGeneralSerializer
            # strips question answer keys for anonymous callers.
            return LOMGeneralSerializer(obj.lom_general, context=self.context).data
        return None


class HeritageItemDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for detailed view of a heritage item.
    Includes all media files (images, audio, video, documents) and full LOM metadata.
    """
    heritage_type = HeritageTypeSerializer(read_only=True)
    heritage_category = HeritageCategorySerializer(read_only=True)
    parish = ParishSerializer(read_only=True)
    city = CityRefSerializer(read_only=True)
    images = MediaFileSerializer(many=True, read_only=True)
    main_image = MediaFileSerializer(read_only=True)
    audio = MediaFileSerializer(many=True, read_only=True)
    video = MediaFileSerializer(many=True, read_only=True)
    documents = MediaFileSerializer(many=True, read_only=True)
    lom_metadata = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    tags = TagListField(read_only=True)
    # Add contributor info if needed, but keeping it simple for now

    class Meta:
        model = HeritageItem
        fields = '__all__'

    def get_lom_metadata(self, obj):
        if hasattr(obj, 'lom_general'):
            # Pass context so the request threads through: LOMGeneralSerializer
            # strips question answer keys for anonymous callers.
            return LOMGeneralSerializer(obj.lom_general, context=self.context).data
        return None

    def get_primary_image(self, obj):
        if obj.main_image:
            return self.context['request'].build_absolute_uri(obj.main_image.file.url)
        first_image = obj.images.first()
        if first_image:
            return self.context['request'].build_absolute_uri(first_image.file.url)
        return None


class ParishCityCoherenceMixin:
    """
    Reject a parish that belongs to a different city than the item.

    The item's city is server-assigned (request context on create, the
    immutable instance city on update), so the check anchors on that — a
    client cannot dodge it by posting a different city. On create WITHOUT an
    explicit request city (legacy clients), the parish's own city is adopted
    (see resolve_city_for_new_item), so there is nothing to check.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        parish = attrs.get('parish', getattr(self.instance, 'parish', None))
        if parish is None:
            return attrs
        if self.instance is not None:
            city_id = self.instance.city_id
        else:
            from apps.cities.request import get_request_city
            city = get_request_city(self.context.get('request'))
            city_id = city.id if city else None
        if city_id is not None and parish.city_id != city_id:
            raise serializers.ValidationError(
                {'parish': 'La parroquia seleccionada no pertenece a la ciudad activa.'}
            )
        return attrs


class HeritageItemCreateUpdateSerializer(ParishCityCoherenceMixin, serializers.ModelSerializer):
    """
    Serializer for creating and updating heritage items.
    Handles GeoJSON geometry fields.
    """
    location = GeometryField()
    tags = TagListField(required=False)
    # Server-assigned from the request city context (see perform_create) —
    # clients cannot place content in another city.
    city = CityRefSerializer(read_only=True)

    class Meta:
        model = HeritageItem
        fields = '__all__'
        # These are driven by the moderation workflow / server, never the client.
        # Without this, a plain authenticated user could POST status='published'
        # (bypassing draft→pending→published) or set contributor to another user.
        read_only_fields = [
            'status', 'contributor', 'curator', 'curator_feedback',
            'moderator', 'moderator_feedback', 'submission_date',
            'last_review_date', 'view_count', 'favorite_count',
        ]


class HeritageItemContributionSerializer(ParishCityCoherenceMixin, serializers.ModelSerializer):
    """
    Serializer used by the contribution wizard.
    Simplifies the creation process for end-users.

    ``educational`` is an optional, write-only nested payload for the wizard's
    "Capa educativa" step. Declaring it here (rather than reading request.data in
    the view) means DRF validates it in the normal flow, so errors surface with a
    proper ``educational.<field>`` path. The view pops it from validated_data and
    applies it to the item's LOM after creation.

    ``save_as_draft`` (B2) keeps the item out of the moderation queue
    (status='draft' instead of 'pending') so contributors can park work in
    progress; ``suggested_category`` (B7) is a free-text request relayed to the
    city's curators when none of the curated categories fits. Both are
    write-only wizard inputs consumed by the view, never model fields.
    """
    location = GeometryField()
    educational = LOMEducationalSerializer(required=False, write_only=True)
    tags = TagListField(required=False)
    save_as_draft = serializers.BooleanField(write_only=True, required=False, default=False)
    suggested_category = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=200
    )
    # Server-assigned from the request city context (see perform_create).
    city = CityRefSerializer(read_only=True)

    class Meta:
        model = HeritageItem
        fields = '__all__'
        # The wizard view (ContributionViewSet.perform_create) sets contributor and
        # status server-side; the client must not be able to spoof them here either.
        read_only_fields = [
            'status', 'contributor', 'curator', 'curator_feedback',
            'moderator', 'moderator_feedback', 'submission_date',
            'last_review_date', 'view_count', 'favorite_count',
        ]


class HeritageRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeritageRelation
        fields = '__all__'


class HeritageItemGeoJSONSerializer(GeoFeatureModelSerializer):
    location = GeometryField()
    primary_image = serializers.SerializerMethodField()
    heritage_type = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    heritage_category = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    city = serializers.SlugRelatedField(slug_field='slug', read_only=True)

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