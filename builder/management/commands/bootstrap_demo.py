from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from builder.models import ProjectTemplate, PrototypeProject
from builder.services.generator import generate_streamlit_artifacts
from builder.services.templates import seed_project_from_template

User = get_user_model()


class Command(BaseCommand):
    help = "Create a demo user and a seeded project for Prototype Studio."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="demo-pass-123")
        parser.add_argument("--project-name", default="Field Ops Quote Builder")
        parser.add_argument("--generate", action="store_true")

    def handle(self, *args, **options):
        user, user_created = User.objects.get_or_create(
            username=options["username"],
            defaults={"is_staff": True, "is_superuser": True},
        )
        if user_created:
            user.set_password(options["password"])
            user.save(update_fields=["password"])

        project, project_created = PrototypeProject.objects.get_or_create(
            name=options["project_name"],
            defaults={
                "created_by": user,
                "template_kind": ProjectTemplate.QUOTE_BUILDER,
                "description": "Seeded demo workspace for quote-builder style prototypes.",
            },
        )
        if project_created or not project.entities.exists():
            seed_project_from_template(project)

        if options["generate"]:
            generate_streamlit_artifacts(project)

        self.stdout.write(self.style.SUCCESS(f"User: {user.username}"))
        if user_created:
            self.stdout.write(self.style.WARNING(f"Password: {options['password']}"))
        self.stdout.write(self.style.SUCCESS(f"Project: {project.name}"))
