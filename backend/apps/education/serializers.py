from rest_framework import serializers
from .models import (
    LOMGeneral, LOMLifeCycle, LOMEducational, LOMRights, 
    LOMClassification, LOMContributor,
    LOMRelation,
    EducationalResource, ResourceType, ResourceCategory
)

class LOMContributorSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOMContributor
        fields = ['role', 'entity', 'date']

class LOMLifeCycleSerializer(serializers.ModelSerializer):
    contributors = LOMContributorSerializer(many=True, read_only=True)
    
    class Meta:
        model = LOMLifeCycle
        fields = ['version', 'status', 'contributors']

class LOMEducationalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOMEducational
        exclude = ['id', 'lom_general', 'created_at', 'updated_at']

class LOMRightsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOMRights
        exclude = ['id', 'lom_general', 'created_at', 'updated_at']

class LOMClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOMClassification
        exclude = ['id', 'lom_general', 'created_at', 'updated_at']


class LOMRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOMRelation
        exclude = ['lom_general', 'created_at', 'updated_at']


class LOMRelationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOMRelation
        exclude = ['created_at', 'updated_at']

class LOMGeneralSerializer(serializers.ModelSerializer):
    heritage_item_id = serializers.UUIDField(read_only=True)
    lifecycle = LOMLifeCycleSerializer(read_only=True)
    educational = LOMEducationalSerializer(read_only=True)
    rights = LOMRightsSerializer(read_only=True)
    classifications = LOMClassificationSerializer(many=True, read_only=True)
    relations = LOMRelationSerializer(many=True, read_only=True)
    
    class Meta:
        model = LOMGeneral
        exclude = ['heritage_item', 'created_at', 'updated_at']

class LOMGeneralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOMGeneral
        fields = '__all__'

class ResourceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceType
        fields = '__all__'

class ResourceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceCategory
        fields = '__all__'

class EducationalResourceSerializer(serializers.ModelSerializer):
    resource_type = ResourceTypeSerializer(read_only=True)
    category = ResourceCategorySerializer(read_only=True)
    
    class Meta:
        model = EducationalResource
        fields = '__all__'
