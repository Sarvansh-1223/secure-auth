from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .identifiers import normalize_email, normalize_phone
from .validators import validate_date_of_birth, validate_surname


def _wrap(fn, value):
    try:
        return fn(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))


class RegisterSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=254)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=32)
    surname = serializers.CharField(max_length=100, trim_whitespace=True)
    date_of_birth = serializers.DateField(input_formats=["%Y-%m-%d"])

    def validate_email(self, value):
        value = (value or "").strip()
        return _wrap(normalize_email, value) if value else None

    def validate_phone(self, value):
        value = (value or "").strip()
        return _wrap(normalize_phone, value) if value else None

    def validate_surname(self, value):
        return _wrap(validate_surname, value)

    def validate_date_of_birth(self, value):
        return _wrap(validate_date_of_birth, value)

    def validate(self, attrs):
        email, phone = attrs.get("email"), attrs.get("phone")
        if bool(email) == bool(phone):
            raise serializers.ValidationError(
                {"identifier": ["Provide either an email address or a mobile number."]}
            )
        return attrs


class CodeSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    code = serializers.CharField(max_length=16, trim_whitespace=True)


class IdentifierSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
