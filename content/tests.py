from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, ModulePurchase, SubCategory, Subject


User = get_user_model()


class PurchaseAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', email='student@example.com', password='testpass123')
        self.category = Category.objects.create(name='Programming', slug='programming')
        self.subcategory = SubCategory.objects.create(
            category=self.category,
            name='Python Basics',
            slug='python-basics',
            price=999,
        )
        self.subject = Subject.objects.create(
            subcategory=self.subcategory,
            title='Introduction',
            slug='introduction',
            body_content='<p>Hello</p>',
        )
        self.subject_url = reverse(
            'content:subject_detail',
            args=[self.category.slug, self.subcategory.slug, self.subject.slug],
        )

    def test_pending_purchase_does_not_grant_subject_access(self):
        self.client.force_login(self.user)
        ModulePurchase.objects.create(user=self.user, subcategory=self.subcategory, is_purchased=False)

        response = self.client.get(self.subject_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'content/module_locked.html')

    def test_completed_purchase_grants_subject_access(self):
        self.client.force_login(self.user)
        ModulePurchase.objects.create(user=self.user, subcategory=self.subcategory, is_purchased=True)

        response = self.client.get(self.subject_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'content/subject_detail.html')
