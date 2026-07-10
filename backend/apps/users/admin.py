from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.cities.models import CityRole

from .models import User, UserProfile, UserRole


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ['display_name', 'avatar', 'bio', 'location', 'preferred_language', 'role', 'points', 'level']


class CityRoleInline(admin.TabularInline):
    """E1 — per-city governance grants right on the User change page, so
    making someone a curator no longer means a detour through the CityRole
    admin. `granted_by` is stamped automatically (see UserAdmin.save_formset)."""
    model = CityRole
    fk_name = 'user'
    extra = 0
    autocomplete_fields = ['city']
    fields = ['city', 'role', 'granted_by', 'created_at']
    readonly_fields = ['granted_by', 'created_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline, CityRoleInline]

    def save_formset(self, request, form, formset, change):
        # Record who granted each new CityRole without asking the admin to
        # fill it in (the field is read-only on the inline).
        if formset.model is CityRole:
            instances = formset.save(commit=False)
            for obj in instances:
                if not obj.granted_by_id:
                    obj.granted_by = request.user
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            formset.save_m2m()
            return
        super().save_formset(request, form, formset, change)

    list_display = ['email', 'username', 'first_name', 'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'display_name', 'role', 'points', 'level', 'created_at']
    list_filter = ['role', 'level', 'preferred_language', 'created_at']
    search_fields = ['user__email', 'display_name', 'bio']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
