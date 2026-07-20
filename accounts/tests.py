from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from .models import User, UserRoles

User = get_user_model()


# =============================================================================
# Model Tests
# =============================================================================

class UserModelTest(TestCase):
    """Tests for the custom User model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )

    def test_create_user_defaults(self):
        self.assertEqual(self.user.role, UserRoles.CASHIER)
        self.assertFalse(self.user.is_deleted)
        self.assertIsNone(self.user.deleted_at)
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.check_password("testpass123"))

    def test_create_user_with_role(self):
        admin = User.objects.create_user(
            username="admin", email="a@b.com", password="pass", role=UserRoles.ADMIN
        )
        self.assertEqual(admin.role, UserRoles.ADMIN)

    def test_str(self):
        self.assertEqual(str(self.user), "John Doe (cashier)")

    def test_str_no_last_name(self):
        u = User.objects.create_user(
            username="nolast", email="n@b.com", password="pass", first_name="Alice"
        )
        self.assertEqual(str(u), "Alice (cashier)")

    def test_soft_delete(self):
        self.user.delete()
        self.assertTrue(self.user.is_deleted)
        self.assertIsNotNone(self.user.deleted_at)
        # Still in DB
        self.assertEqual(User.all_objects.count(), 1)
        # Excluded by default manager
        self.assertEqual(User.objects.count(), 0)

    def test_restore(self):
        self.user.delete()
        self.user.restore()
        self.assertFalse(self.user.is_deleted)
        self.assertIsNone(self.user.deleted_at)
        self.assertEqual(User.objects.count(), 1)

    def test_hard_delete(self):
        self.user.hard_delete()
        self.assertEqual(User.all_objects.count(), 0)

    def test_is_admin_property(self):
        self.user.role = UserRoles.ADMIN
        self.user.save()
        self.assertTrue(self.user.is_admin)
        self.user.role = UserRoles.CASHIER
        self.user.save()
        self.assertFalse(self.user.is_admin)

    def test_is_manager_property(self):
        for role in (UserRoles.ADMIN, UserRoles.MANAGER):
            self.user.role = role
            self.user.save()
            self.assertTrue(self.user.is_manager)
        self.user.role = UserRoles.CASHIER
        self.user.save()
        self.assertFalse(self.user.is_manager)


# =============================================================================
# Manager Tests
# =============================================================================

class SoftDeleteUserManagerTest(TestCase):
    def setUp(self):
        self.active = User.objects.create_user(
            username="active", email="a@b.com", password="pass"
        )
        self.deleted = User.objects.create_user(
            username="deleted", email="d@b.com", password="pass"
        )
        self.deleted.delete()

    def test_get_queryset_excludes_deleted(self):
        self.assertEqual(list(User.objects.all()), [self.active])

    def test_hard_deleted(self):
        self.assertEqual(list(User.objects.hard_deleted()), [self.deleted])

    def test_all_with_deleted(self):
        self.assertEqual(User.objects.all_with_deleted().count(), 2)


# =============================================================================
# Form Tests
# =============================================================================

class RegistrationFormTest(TestCase):
    def test_valid_data(self):
        from .forms import CustomUserCreationForm

        form = CustomUserCreationForm(data={
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_email(self):
        from .forms import CustomUserCreationForm

        form = CustomUserCreationForm(data={
            "username": "newuser",
            "first_name": "Jane",
            "last_name": "Smith",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_mismatch(self):
        from .forms import CustomUserCreationForm

        form = CustomUserCreationForm(data={
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "password1": "StrongPass123!",
            "password2": "DifferentPass456!",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)


class ProfileFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )

    def test_valid_update(self):
        from .forms import UserProfileForm

        form = UserProfileForm(
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
                "phone_number": "+9230112345678",
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.phone_number, "+9230112345678")

    def test_missing_first_name(self):
        from .forms import UserProfileForm

        form = UserProfileForm(
            data={
                "first_name": "",
                "last_name": "Name",
                "email": "test@example.com",
            },
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)


# =============================================================================
# View Tests
# =============================================================================

class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("accounts:register")

    def test_get_returns_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")

    def test_post_valid_creates_user_and_redirects(self):
        response = self.client.post(self.url, {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        # User is logged in after registration
        user = User.objects.get(username="newuser")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_post_invalid_returns_form_with_errors(self):
        response = self.client.post(self.url, {
            "username": "",
            "email": "bad",
            "password1": "pass",
            "password2": "pass",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="").exists())

    def test_authenticated_user_redirects_to_profile(self):
        user = User.objects.create_user(
            username="existing", email="e@b.com", password="pass"
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/profile/", response.url)


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("accounts:login")
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_get_returns_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign In")

    def test_post_valid_credentials_redirects(self):
        response = self.client.post(self.url, {
            "username": "testuser",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/profile/", response.url)

    def test_post_invalid_credentials(self):
        response = self.client.post(self.url, {
            "username": "testuser",
            "password": "wrongpass",
        })
        self.assertEqual(response.status_code, 200)  # re-renders form


class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="t@b.com", password="pass"
        )
        self.client.force_login(self.user)

    def test_logout_redirects(self):
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)


class ProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("accounts:profile")
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass",
            first_name="John", last_name="Doe",
        )

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John")

    def test_post_updates_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "phone_number": "+9230112345678",
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")


class PasswordChangeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("accounts:password_change")
        self.user = User.objects.create_user(
            username="testuser", email="t@b.com", password="oldpass123"
        )

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password")

    def test_post_changes_password(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "old_password": "oldpass123",
            "new_password1": "NewStrongPass123!",
            "new_password2": "NewStrongPass123!",
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass123!"))


class PasswordResetViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )

    def test_get_returns_form(self):
        response = self.client.get(reverse("accounts:password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset password")

    def test_post_valid_email_redirects(self):
        response = self.client.post(reverse("accounts:password_reset"), {
            "email": "test@example.com",
        })
        self.assertEqual(response.status_code, 302)


# =============================================================================
# URL Resolution Tests
# =============================================================================

class URLResolutionTest(TestCase):
    def test_register_url(self):
        self.assertEqual(reverse("accounts:register"), "/accounts/register/")

    def test_login_url(self):
        self.assertEqual(reverse("accounts:login"), "/accounts/login/")

    def test_logout_url(self):
        self.assertEqual(reverse("accounts:logout"), "/accounts/logout/")

    def test_profile_url(self):
        self.assertEqual(reverse("accounts:profile"), "/accounts/profile/")

    def test_password_change_url(self):
        self.assertEqual(reverse("accounts:password_change"), "/accounts/password-change/")

    def test_password_reset_url(self):
        self.assertEqual(reverse("accounts:password_reset"), "/accounts/password-reset/")
