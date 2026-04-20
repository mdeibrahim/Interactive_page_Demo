from django.core.management.base import BaseCommand
from django.db import transaction

from content.models import (
    SubCategory,
    Course,
    Module,
    Subject,
    ModulePurchase,
    CourseCertificate,
    CourseChangeRequest,
)


class Command(BaseCommand):
    help = 'Migrate SubCategory -> Course and set transitional course FKs'

    def handle(self, *args, **options):
        created = 0
        total_updated = 0

        with transaction.atomic():
            for sub in SubCategory.objects.all():
                course = getattr(sub, 'migrated_course', None)
                if course:
                    self.stdout.write(self.style.NOTICE(f"Skipping existing migration for SubCategory {sub.id}: {sub.name}"))
                else:
                    course = Course.objects.create(
                        teacher=sub.teacher,
                        category=sub.category,
                        name=sub.name,
                        slug=sub.slug,
                        description=sub.description,
                        price=sub.price,
                        old_subcategory=sub,
                    )
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"Created Course {course.id}: {course.name}"))

                # Update related objects to point to new Course
                n = Module.objects.filter(subcategory=sub).update(course=course)
                total_updated += n
                if n:
                    self.stdout.write(f"  Updated {n} Module(s)")

                n = Subject.objects.filter(subcategory=sub).update(course=course)
                total_updated += n
                if n:
                    self.stdout.write(f"  Updated {n} Subject(s)")

                n = ModulePurchase.objects.filter(subcategory=sub).update(course=course)
                total_updated += n
                if n:
                    self.stdout.write(f"  Updated {n} ModulePurchase(s)")

                n = CourseCertificate.objects.filter(subcategory=sub).update(course=course)
                total_updated += n
                if n:
                    self.stdout.write(f"  Updated {n} CourseCertificate(s)")

                n = CourseChangeRequest.objects.filter(course=sub).update(course_new=course)
                total_updated += n
                if n:
                    self.stdout.write(f"  Updated {n} CourseChangeRequest(s)")

        self.stdout.write(self.style.SUCCESS(f"Migration complete — created {created} Course(s), updated {total_updated} related rows."))