from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0005_allow_subcategory_null"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "content_coursecontent" ALTER COLUMN "video_url" DROP NOT NULL;'
            ),
            reverse_sql=(
                'ALTER TABLE "content_coursecontent" ALTER COLUMN "video_url" SET NOT NULL;'
            ),
        ),
    ]
