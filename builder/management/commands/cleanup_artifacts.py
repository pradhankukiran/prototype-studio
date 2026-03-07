from __future__ import annotations

import shutil
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from builder.models import GeneratedArtifact, PrototypeProject


class Command(BaseCommand):
    help = 'Purge old generated artifacts and orphaned directories.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Delete artifacts older than this many days.')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting.')

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(days=days)

        old_artifacts = GeneratedArtifact.objects.filter(created_at__lt=cutoff)
        count = old_artifacts.count()

        if dry_run:
            self.stdout.write(f'[dry-run] Would delete {count} artifact record(s) older than {days} day(s).')
        else:
            old_artifacts.delete()
            self.stdout.write(f'Deleted {count} artifact record(s) older than {days} day(s).')

        generated_root = settings.GENERATED_ROOT
        if not generated_root.is_dir():
            return

        active_slugs = set(PrototypeProject.objects.values_list('slug', flat=True))

        removed_dirs = 0
        for child in generated_root.iterdir():
            if not child.is_dir():
                continue
            if child.name.startswith('.'):
                continue
            if child.name in active_slugs:
                continue
            if dry_run:
                self.stdout.write(f'[dry-run] Would remove orphaned directory: {child}')
            else:
                shutil.rmtree(child)
                self.stdout.write(f'Removed orphaned directory: {child}')
            removed_dirs += 1

        # Clean orphaned zip files
        for child in generated_root.iterdir():
            if not child.is_file() or child.suffix != '.zip':
                continue
            slug = child.stem
            if slug in active_slugs:
                continue
            if dry_run:
                self.stdout.write(f'[dry-run] Would remove orphaned zip: {child}')
            else:
                child.unlink()
                self.stdout.write(f'Removed orphaned zip: {child}')

        if removed_dirs == 0 and not dry_run:
            self.stdout.write('No orphaned directories found.')
