from rest_framework import serializers
from .models import (
    LOMGeneral, LOMLifeCycle, LOMEducational, LOMRights,
    LOMClassification, LOMContributor,
    LOMRelation, AssessmentQuestion,
    EducationalResource, ResourceType, ResourceCategory
)


def _sync_ordered_children(manager, model, parent, entries):
    """Reconcile a FK-many relation with a desired list of child dicts.

    Updates existing rows in positional order (preserving their primary keys —
    so UUIDs and any references survive an edit), creates rows for extra
    payloads, and deletes any surplus existing rows. This replaces the naive
    delete-then-recreate, which churned every child's UUID on every save.
    """
    existing = list(manager.all())
    field_name = manager.field.name
    for idx, data in enumerate(entries):
        if idx < len(existing):
            obj = existing[idx]
            for attr, value in data.items():
                setattr(obj, attr, value)
            obj.save()
        else:
            model.objects.create(**{field_name: parent}, **data)
    # Remove rows beyond the new set's length.
    for obj in existing[len(entries):]:
        obj.delete()


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
    """Full assessment-question serializer including the answer key
    (``choices[].correct``, ``correct_response``). Use ONLY for authenticated
    authoring/curator/QTI-export paths — never for anonymous reads. Public reads
    go through AssessmentQuestionPublicSerializer, which strips the answers.
    """
    class Meta:
        model = AssessmentQuestion
        exclude = ['lom_general', 'created_at', 'updated_at']


class AssessmentQuestionPublicSerializer(serializers.ModelSerializer):
    """Answer-key-free view of a question for unauthenticated learners: choices
    keep only their id/text, and correct_response is dropped entirely."""
    choices = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentQuestion
        fields = ['id', 'order', 'question_type', 'prompt', 'choices', 'feedback']

    def get_choices(self, obj):
        result = []
        for c in (obj.choices or []):
            if isinstance(c, dict):
                result.append({k: c.get(k) for k in ('id', 'text') if k in c})
        return result


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

        # FK-many children: sync in place rather than delete-and-recreate, so
        # existing rows keep their UUIDs when a client edits (not reorders) the
        # set. Surplus rows are removed; new payloads create new rows.
        if classifications is not None:
            _sync_ordered_children(
                instance.classifications, LOMClassification, instance, classifications
            )
        if questions is not None:
            _sync_ordered_children(
                instance.questions, AssessmentQuestion, instance, questions
            )

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
