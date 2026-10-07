"""Back office des comptes (version minimale, droits par rôle : US 9.1)"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

from accounts.models import User


class UserCreationForm(AdminUserCreationForm):
    """Formulaire de création : l'e-mail remplace le nom d'utilisateur"""

    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email", "role")


class UserChangeForm(BaseUserChangeForm):
    """Formulaire de modification d'un compte existant"""

    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Liste et fiches des comptes du back office"""

    form = UserChangeForm
    add_form = UserCreationForm
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "locked_until",
    )
    list_filter = ("role", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identité", {"fields": ("first_name", "last_name")}),
        # Les droits découlent du rôle (voir User.save)
        ("Droits", {"fields": ("role", "is_active")}),
        # Un administrateur peut déverrouiller un compte en vidant la date
        ("Sécurité", {"fields": ("failed_attempts", "locked_until")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "role",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
