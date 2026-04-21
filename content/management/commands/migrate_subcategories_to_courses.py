from django.core.management.base import BaseCommand
from django.db import transaction

from content.models import (
    Course,
    Module,
    ModulePurchase,
    CourseCertificate,
    CourseChangeRequest,
)


class Command(BaseCommand):
    help = 'Legacy migration helper for older course-table upgrades.'

    def handle(self, *args, **options):
        # Legacy model has been removed from the codebase. This command is
        # intentionally a no-op. If old rows still exist in a backup database,
        # migrate them with a dedicated one-off data migration.
        self.stdout.write(self.style.WARNING('Legacy model removed — no action performed.'))
