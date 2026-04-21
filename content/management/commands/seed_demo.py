from django.core.management.base import BaseCommand
from content.models import (
    Category,
    Course,
    Module,
    CourseVideo,
    CourseQuiz,
    CourseQuizQuestion,
)


class Command(BaseCommand):
    help = 'Seed the database with demo content for the Interactive Teaching Platform'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding demo data...'))

        # ── Category ──
        cat, _ = Category.objects.get_or_create(
            slug='journalism',
            defaults={
                'name': 'Journalism',
                'description': 'News reporting, investigative journalism, and media studies.',
            }
        )

        # ── course ──
        course, _ = Course.objects.get_or_create(
            category=cat,
            slug='crime-reporting',
            defaults={'name': 'Crime Reporting', 'description': 'Covering criminal investigations and court proceedings.'}
        )



        # ── Modules, Videos, Quizzes ──
        mod1, _ = Module.objects.get_or_create(
            course=course,
            slug='introduction',
            defaults={'title': 'Introduction & Context', 'description': 'Overview and background of the case.', 'order': 1}
        )

        mod2, _ = Module.objects.get_or_create(
            course=course,
            slug='case-analysis',
            defaults={'title': 'Case Analysis', 'description': 'Detailed walkthrough and evidence analysis.', 'order': 2}
        )

        # Videos for module 1
        CourseVideo.objects.get_or_create(module=mod1, title='Overview of the Case', defaults={'video_url': ''})
        CourseVideo.objects.get_or_create(module=mod1, title='Timeline & Key Events', defaults={'video_url': ''})

        # Videos for module 2
        CourseVideo.objects.get_or_create(module=mod2, title='CCTV Footage Breakdown', defaults={'video_url': ''})

        # Quizzes
        q1, _ = CourseQuiz.objects.get_or_create(module=mod1, title='Introduction Quiz', defaults={'pass_score': 50, 'is_active': True})
        CourseQuizQuestion.objects.get_or_create(quiz=q1, question='Which piece of evidence was central to the arrest?', defaults={
            'option_a': 'CCTV footage', 'option_b': 'Witness testimony', 'option_c': 'Recovered jewellery', 'option_d': 'None of the above', 'correct_option': 'A', 'order': 1
        })

        q2, _ = CourseQuiz.objects.get_or_create(module=mod2, title='Analysis Quiz', defaults={'pass_score': 60, 'is_active': True})
        CourseQuizQuestion.objects.get_or_create(quiz=q2, question='What analysis helped identify suspects?', defaults={
            'option_a': 'Timeline cross-check', 'option_b': 'CCTV enhancement', 'option_c': 'Forensic lab test', 'option_d': 'Social media tracing', 'correct_option': 'B', 'order': 1
        })

        # Accordion sections were previously attached to Subject; with Subject
        # removed we seed only Modules/Videos/Quizzes for demo purposes.

        self.stdout.write(self.style.SUCCESS(
            f'\nSUCCESS: Demo data seeded successfully!\n'
            f'   Category: {cat.name}\n'
            f'   course: {course.name}\n'
            f'   Module 1: {mod1.title}\n'
            f'   Module 2: {mod2.title}\n\n'
            f'   Visit: http://127.0.0.1:8000/\n'
        ))

    def _body_content(self):
        return """<p>
রাজধানীর ফরচুন শপিং মেলের শম্পা জুয়েলার্স থেকে ৫০০ স্বর্ণালঙ্কার চুরির চাঞ্চল্যকর ঘটনার রহস্য
উদঘাটন করেছে ঢাকা মহানগর গোয়েন্দা পুলিশ (ডিবি)। দুর্ধর্ষ এই চুরির ঘটনায় জড়িত
সন্দেহভাজন
চার জনকে গ্রেফতার করা হয়েছে এবং তাদের কাছ থেকে বিপুল পরিমাণ চোরাই স্বর্ণালঙ্কার উদ্ধার করা
হয়েছে বলে জানিয়েছে ডিবি।
</p>

<p>
ডিবির যুগ্ম পুলিশ কমিশনার জানান, গত সোমবার দিবাগত রাতে
অভিযান পরিচালনা করে
চারজন সন্দেহভাজন ব্যক্তিকে রাজধানীর বিভিন্ন স্থান থেকে গ্রেফতার করা হয়।
তাদের কাছ থেকে মোট ১২০টি সোনার গহনা এবং নগদ অর্থ জব্দ করা হয়।
</p>

<p>
প্রাথমিক জিজ্ঞাসাবাদে গ্রেফতারকৃতরা অপরাধের কথা স্বীকার করেছে। ডিবি জানায় যে দলটি দীর্ঘদিন ধরে
শপিং মলগুলোকে লক্ষ্য বানিয়ে চুরি করে আসছিল।
ডিবির প্রেস ব্রিফিংয়ে পুরো অপারেশনের বিবরণ দেওয়া হয়েছে।
</p>

<p>
ঘটনাস্থলের
সিসিটিভি ফুটেজ বিশ্লেষণ
করে পুলিশ চোরদের শনাক্ত করতে সক্ষম হয়। ফুটেজে দেখা যাচ্ছে, তারা দোকান বন্ধ হওয়ার পরে
ছাদ ভেঙে ভেতরে প্রবেশ করে।
</p>

<p>
এই ঘটনা সংক্রান্ত বিস্তারিত সংবাদ বিভিন্ন টেলিভিশন চ্যানেল ও পত্রিকায় প্রচারিত হয়েছিল।
</p>

<p>
মামলাটির তদন্ত অব্যাহত রয়েছে এবং আরও গ্রেফতারের সম্ভাবনা রয়েছে বলে জানিয়েছে ডিবি পুলিশ।
ফরচুন শপিং মলের নিরাপত্তা ব্যবস্থা জোরদার করার কথাও বলা হয়েছে।
</p>"""


