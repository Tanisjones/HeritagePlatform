from rest_framework import serializers
from .models import (
    LOMGeneral, LOMLifeCycle, LOMEducational, LOMRights,
    LOMClassification, LOMContributor,
    LOMRelation, AssessmentQuestion,
    EducationalResource, ResourceType, ResourceCategory
)


def _sync_ordered_children(manager, entries):
    """Reconcile a FK-many relation with a desired list of child dicts.

    Matches existing rows to incoming entries by IDENTITY (``id``), not by list
    position: an entry carrying an ``id`` that matches an existing row updates
    that row in place (preserving its UUID and any external references); an entry
    without a matching ``id`` creates a new row; existing rows whose ``id`` is not
    present in the payload are deleted. This is order-independent, so a client
    reordering the children no longer mis-assigns content to the wrong UUID (the
    bug positional matching had, made worse by unordered querysets).

    ``manager`` is a reverse-FK related manager; the model and parent instance and
    the FK field name are all derived from it.
    """
    model = manager.model
    parent = manager.instance
    field_name = manager.field.name

    existing = {obj.pk: obj for obj in manager.all()}
    seen_ids = set()

    for data in entries:
        data = dict(data)
        entry_id = data.pop('id', None)
        obj = existing.get(entry_id) if entry_id is not None else None
        if obj is not None:
            seen_ids.add(obj.pk)
            for attr, value in data.items():
                setattr(obj, attr, value)
            obj.save()
        else:
            model.objects.create(**{field_name: parent}, **data)

    # Delete rows the client dropped (present before, absent from the payload).
    for pk, obj in existing.items():
        if pk not in seen_ids:
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
    # id is optional-writable so nested replace-all can match existing rows by
    # identity (update in place) instead of by list position. Omit it to create.
    id = serializers.UUIDField(required=False)

    class Meta:
        model = LOMClassification
        exclude = ['lom_general', 'created_at', 'updated_at']


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
    it is bound from the parent). ``id`` is optional-writable so the replace-all
    sync can match existing rows by identity (preserving their UUID) rather than
    by list position. Omit ``id`` to create a new question."""
    id = serializers.UUIDField(required=False)

    class Meta:
        model = AssessmentQuestion
        exclude = ['lom_general', 'created_at', 'updated_at']


class LOMGeneralSerializer(serializers.ModelSerializer):
    heritage_item_id = serializers.UUIDField(read_only=True)
    lifecycle = LOMLifeCycleSerializer(read_only=True)
    educational = LOMEducationalSerializer(read_only=True)
    rights = LOMRightsSerializer(read_only=True)
    classifications = LOMClassificationSerializer(many=True, read_only=True)
    relations = LOMRelationSerializer(many=True, read_only=True)
    # Answer-key protection lives HERE (not just on the /lom-questions/ endpoint)
    # because this serializer is the read shape for /lom/, /lom/by_heritage_item/,
    # /education/lom-packages/ AND the nested lom_metadata on /heritage-items/ —
    # all anonymously readable. Anonymous callers get the answer-key-free shape.
    questions = serializers.SerializerMethodField()

    class Meta:
        model = LOMGeneral
        exclude = ['heritage_item', 'created_at', 'updated_at']

    def get_questions(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        question_qs = obj.questions.all()
        if user and user.is_authenticated:
            return AssessmentQuestionSerializer(question_qs, many=True, context=self.context).data
        return AssessmentQuestionPublicSerializer(question_qs, many=True, context=self.context).data


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

        # FK-many children: sync by identity (id) rather than delete-and-recreate,
        # so existing rows keep their UUIDs across edits AND reorders. Rows the
        # client dropped are removed; entries without an id create new rows.
        if classifications is not None:
            _sync_ordered_children(instance.classifications, classifications)
        if questions is not None:
            _sync_ordered_children(instance.questions, questions)

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
