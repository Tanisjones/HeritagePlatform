from rest_framework import serializers
from .models import (
    LOMGeneral, LOMLifeCycle, LOMEducational, LOMRights,
    LOMClassification, LOMContributor,
    LOMRelation, AssessmentQuestion,
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

class AssessmentQuestionSerializer(serializers.ModelSerializer):
    """Full assessment-question serializer.

    NOTE: this exposes ``choices[].correct`` and ``correct_response`` — fine for
    authoring/curator views, but a public "quiz-taking" endpoint should strip
    those answer keys (e.g. via a separate read serializer) so learners can't
    read the answers off the wire.
    """
    class Meta:
        model = AssessmentQuestion
        exclude = ['lom_general', 'created_at', 'updated_at']


class AssessmentQuestionNestedSerializer(serializers.ModelSerializer):
    """Question shape for nested writes under LOMGeneral (no ``lom_general`` —
    it is bound from the parent). Mirrors how classifications are written."""
    class Meta:
        model = AssessmentQuestion
        exclude = ['id', 'lom_general', 'created_at', 'updated_at']


class LOMGeneralSerializer(serializers.ModelSerializer):
    heritage_item_id = serializers.UUIDField(read_only=True)
    lifecycle = LOMLifeCycleSerializer(read_only=True)
    educational = LOMEducationalSerializer(read_only=True)
    rights = LOMRightsSerializer(read_only=True)
    classifications = LOMClassificationSerializer(many=True, read_only=True)
    relations = LOMRelationSerializer(many=True, read_only=True)
    questions = AssessmentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = LOMGeneral
        exclude = ['heritage_item', 'created_at', 'updated_at']


class LOMGeneralWriteSerializer(serializers.ModelSerializer):
    """
    Writable, nested serializer so the whole educational layer can be authored
    in a single PATCH /lom/{id}/ : the general fields plus nested `educational`,
    `rights`, `lifecycle` (one-to-one, update-or-create) and `classifications`
    (replace-all). Reads back through LOMGeneralSerializer's nested children.
    """
    educational = LOMEducationalSerializer(required=False)
    rights = LOMRightsSerializer(required=False)
    lifecycle = LOMLifeCycleSerializer(required=False)
    classifications = LOMClassificationSerializer(many=True, required=False)
    questions = AssessmentQuestionNestedSerializer(many=True, required=False)

    class Meta:
        model = LOMGeneral
        exclude = ['heritage_item', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        educational = validated_data.pop('educational', None)
        rights = validated_data.pop('rights', None)
        lifecycle = validated_data.pop('lifecycle', None)
        classifications = validated_data.pop('classifications', None)
        questions = validated_data.pop('questions', None)

        # General (own) fields.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # One-to-one children: update in place or create.
        if educational is not None:
            LOMEducational.objects.update_or_create(
                lom_general=instance, defaults=educational
            )
        if rights is not None:
            LOMRights.objects.update_or_create(
                lom_general=instance, defaults=rights
            )
        if lifecycle is not None:
            # contributors is read-only in the serializer, so it won't be here.
            LOMLifeCycle.objects.update_or_create(
                lom_general=instance, defaults=lifecycle
            )

        # Classifications (FK many): replace the set.
        if classifications is not None:
            instance.classifications.all().delete()
            for entry in classifications:
                LOMClassification.objects.create(lom_general=instance, **entry)

        # Questions (FK many): replace the set (same semantics as classifications).
        if questions is not None:
            instance.questions.all().delete()
            for entry in questions:
                AssessmentQuestion.objects.create(lom_general=instance, **entry)

        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        # Always return the rich read shape after a write.
        return LOMGeneralSerializer(instance, context=self.context).data


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
