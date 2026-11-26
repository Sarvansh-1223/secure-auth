import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q


class UserManager(BaseUserManager):
    def create_user(self, email=None, phone_e164=None, **extra):
        user = self.model(email=email, phone_e164=phone_e164, **extra)
        user.set_unusable_password()  # passwordless: OTP / WebAuthn only
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    """Identity and verification state only. Personal details live in UserProfile."""

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True)
    phone_e164 = models.CharField(max_length=16, unique=True, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "public_id"
    objects = UserManager()

    class Meta:
        db_table = "auth_user_account"
        constraints = [
            models.CheckConstraint(
                condition=Q(email__isnull=False) | Q(phone_e164__isnull=False),
                name="user_has_email_or_phone",
            )
        ]

    def __str__(self):
        return str(self.public_id)

    def is_identifier_verified(self, kind: str) -> bool:
        return self.email_verified if kind == "email" else self.phone_verified


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    surname = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile"
