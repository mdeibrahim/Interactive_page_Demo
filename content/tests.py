from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, ModulePurchase, Course


User = get_user_model()


class PurchaseAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', email='student@example.com', password='testpass123')
        self.category = Category.objects.create(name='Programming', slug='programming')
        self.course = Course.objects.create(
            category=self.category,
            name='Python Basics',
            slug='python-basics',
            price=999,
        )
        self.course_url = reverse(
            'content:category_details',
            args=[self.category.slug, self.course.slug],
        )

    def test_pending_purchase_still_shows_course_page(self):
        self.client.force_login(self.user)
        ModulePurchase.objects.create(user=self.user, course=self.course, is_purchased=False)

        response = self.client.get(self.course_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'content/course_detail.html')

    def test_completed_purchase_grants_course_access(self):
        self.client.force_login(self.user)
        ModulePurchase.objects.create(user=self.user, course=self.course, is_purchased=True)

        response = self.client.get(self.course_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'content/course_detail.html')


