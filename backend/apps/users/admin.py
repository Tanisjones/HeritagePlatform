from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

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


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]

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
