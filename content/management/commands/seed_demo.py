from django.core.management.base import BaseCommand
from content.models import (
    Category,
    SubCategory,
    Subject,
    AccordionSection,
    InteractiveContent,
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

        # ── SubCategory ──
        subcat, _ = SubCategory.objects.get_or_create(
            category=cat,
            slug='crime-reporting',
            defaults={'name': 'Crime Reporting', 'description': 'Covering criminal investigations and court proceedings.'}
        )

        subject, _ = Subject.objects.get_or_create(
            subcategory=subcat,
            slug='rajdhani-fortune-shopping',
            defaults={
                'title': 'Rajdhani Fortune Shopping Mall Jewellery Theft',
                'body_content': self._body_content(),
            }
        )

        # ── Interactive Contents ──
        ic_text, _ = InteractiveContent.objects.get_or_create(
            subject=subject,
            content_type='text',
            defaults={
                'title': 'What is Suspicion (সন্দেহ)?',
                'text_content': (
                    '<p><strong>Suspicion (সন্দেহ)</strong> in legal and journalistic contexts refers to '
                    'a reasonable belief, based on observable facts, that a person is involved in or may '
                    'have knowledge of a crime.</p>'
                    '<p>Investigative bodies use suspicion as a basis to begin questioning a witness or '
                    'person of interest. It is distinct from full legal accusation.</p>'
                    '<p><em>Example:</em> Dhaka Metropolitan Detective Branch (DB) detained four individuals '
                    'on suspicion of involvement in the Fortune Shopping Mall jewellery heist.</p>'
                ),
            }
        )

        ic_img, _ = InteractiveContent.objects.get_or_create(
            subject=subject,
            content_type='image',
            title='Crime Scene Map',
            defaults={'image': ''}
        )

        # Audio IC
        ic_audio, _ = InteractiveContent.objects.get_or_create(
            subject=subject,
            content_type='audio',
            title='DB Press Briefing (Audio)',
            defaults={'audio': ''}
        )

        # Video IC
        ic_video, _ = InteractiveContent.objects.get_or_create(
            subject=subject,
            content_type='video',
            title='CCTV Footage Analysis',
            defaults={'video': ''}
        )

        # YouTube IC
        ic_yt, _ = InteractiveContent.objects.get_or_create(
            subject=subject,
            content_type='youtube',
            title='News Report on Fortune Mall Theft',
            defaults={'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'}
        )

        # ── Update body with real IDs ──
        subject.body_content = self._body_content_with_ids(
            ic_text.id, ic_img.id, ic_audio.id, ic_video.id, ic_yt.id
        )
        subject.save()

        # ── Modules, Videos, Quizzes ──
        mod1, _ = Module.objects.get_or_create(
            subcategory=subcat,
            slug='introduction',
            defaults={'title': 'Introduction & Context', 'description': 'Overview and background of the case.', 'order': 1}
        )

        mod2, _ = Module.objects.get_or_create(
            subcategory=subcat,
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

        # ── Accordion Sections ──
        AccordionSection.objects.get_or_create(
            subject=subject,
            title='Introduction',
            defaults={
                'content': (
                    '<p>This lesson covers the high-profile jewellery theft case at Rajdhani '
                    'Fortune Shopping Mall, Dhaka. Over <strong>৳ 5 crore</strong> worth of '
                    'gold and ornaments were stolen from Shompa Jewellers.</p>'
                    '<p>You will learn key investigative journalism concepts — including how '
                    'DB Police conducted the operation and arrested suspects.</p>'
                ),
                'order': 1,
                'is_open_by_default': True,
            }
        )
        AccordionSection.objects.get_or_create(
            subject=subject,
            title='Detailed Explanation',
            defaults={
                'content': (
                    '<p>Dhaka Metropolitan Detective Branch (DB) received a tip-off and '
                    'placed the suspects under surveillance before the arrest. '
                    'All four suspects confessed during initial interrogation.</p>'
                    '<p>Key evidence: CCTV footage, stolen ornament recovery, '
                    'and witness testimonies.</p>'
                ),
                'order': 2,
            }
        )
        AccordionSection.objects.get_or_create(
            subject=subject,
            title='Additional Resources',
            defaults={
                'content': (
                    '<p>📰 Read the full report in Prothom Alo &amp; Daily Star.</p>'
                    '<p>📹 Watch the DB press conference video above.</p>'
                    '<p>📚 Reference: CrPC Section 54 — arrest without warrant.</p>'
                ),
                'order': 3,
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f'\nSUCCESS: Demo data seeded successfully!\n'
            f'   Category: {cat.name}\n'
            f'   SubCategory: {subcat.name}\n'
            f'   Subject: {subject.title}\n'
            f'   Interactive items: {subject.interactive_contents.count()}\n'
            f'   Accordion sections: {subject.accordion_sections.count()}\n\n'
            f'   Visit: http://127.0.0.1:8000/\n'
            f'   Subject page: http://127.0.0.1:8000/category/journalism/crime-reporting/rajdhani-fortune-shopping/\n'
        ))

    def _body_content(self):
        return '<p>Loading content IDs...</p>'

    def _body_content_with_ids(self, text_id, img_id, audio_id, video_id, yt_id):
        return f"""<p>
রাজধানীর ফরচুন শপিং মেলের শম্পা জুয়েলার্স থেকে ৫০০ স্বর্ণালঙ্কার চুরির চাঞ্চল্যকর ঘটনার রহস্য
উদঘাটন করেছে ঢাকা মহানগর গোয়েন্দা পুলিশ (ডিবি)। দুর্ধর্ষ এই চুরির ঘটনায় জড়িত
<span class="highlight-link" data-content-id="{text_id}" data-type="text">সন্দেহ</span>
চার জনকে গ্রেফতার করা হয়েছে এবং তাদের কাছ থেকে বিপুল পরিমাণ চোরাই স্বর্ণালঙ্কার উদ্ধার করা
হয়েছে বলে জানিয়েছে ডিবি।
</p>

<p>
ডিবির যুগ্ম পুলিশ কমিশনার জানান, গত সোমবার দিবাগত রাতে
<span class="highlight-link" data-content-id="{img_id}" data-type="image">অভিযান পরিচালনা করে</span>
চারজন সন্দেহভাজন ব্যক্তিকে রাজধানীর বিভিন্ন স্থান থেকে গ্রেফতার করা হয়।
তাদের কাছ থেকে মোট ১২০টি সোনার গহনা এবং নগদ অর্থ জব্দ করা হয়।
</p>

<p>
প্রাথমিক জিজ্ঞাসাবাদে গ্রেফতারকৃতরা অপরাধের কথা স্বীকার করেছে। ডিবি জানায় যে দলটি দীর্ঘদিন ধরে
শপিং মলগুলোকে লক্ষ্য বানিয়ে চুরি করে আসছিল।
<span class="highlight-link" data-content-id="{audio_id}" data-type="audio">ডিবির প্রেস ব্রিফিং শুনুন</span>
— যেখানে পুরো অপারেশনের বিবরণ দেওয়া হয়েছে।
</p>

<p>
ঘটনাস্থলের
<span class="highlight-link" data-content-id="{video_id}" data-type="video">সিসিটিভি ফুটেজ বিশ্লেষণ</span>
করে পুলিশ চোরদের শনাক্ত করতে সক্ষম হয়। ফুটেজে দেখা যাচ্ছে, তারা দোকান বন্ধ হওয়ার পরে
ছাদ ভেঙে ভেতরে প্রবেশ করে।
</p>

<p>
এই ঘটনা সংক্রান্ত বিস্তারিত সংবাদ দেখুন:
<span class="highlight-link" data-content-id="{yt_id}" data-type="youtube">ইউটিউব নিউজ রিপোর্ট</span>
— যা টেলিভিশন চ্যানেলে প্রচারিত হয়েছিল।
</p>

<p>
মামলাটির তদন্ত অব্যাহত রয়েছে এবং আরও গ্রেফতারের সম্ভাবনা রয়েছে বলে জানিয়েছে ডিবি পুলিশ।
ফরচুন শপিং মলের নিরাপত্তা ব্যবস্থা জোরদার করার কথাও বলা হয়েছে।
</p>"""
