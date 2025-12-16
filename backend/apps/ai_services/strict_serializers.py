from __future__ import annotations

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    """
    DRF `Serializer` that rejects unknown keys (instead of silently ignoring them).
    """

    def to_internal_value(self, data):  # noqa: ANN001
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected an object.")

        unknown = set(data.keys()) - set(self.fields.keys())
        if unknown:
            raise serializers.ValidationError({k: "Unexpected field." for k in sorted(unknown)})

        return super().to_internal_value(data)

