import getpass

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create an admin user'

    def handle(self, *args, **options):
        self.stdout.write("Creating an admin user...")

        # Get user details
        email = input("Email: ").strip()
        first_name = input("First name: ").strip()
        last_name = input("Last name: ").strip()
        phone_number = input("Phone number: ").strip()

        # Get password securely
        while True:
            password = getpass.getpass("Password: ")
            password_confirm = getpass.getpass("Confirm Password: ")
            if password == password_confirm:
                break
            else:
                self.stdout.write("Passwords do not match. Please try again.")

        try:
            # Create the admin user
            User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                user_type='admin',
                is_superuser=True,
                is_staff=True
            )

            self.stdout.write(self.style.SUCCESS(f"Admin user '{email}' created successfully."))

        except ValidationError as e:
            self.stdout.write(self.style.ERROR(f"Error creating user: {e.messages}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {str(e)}"))