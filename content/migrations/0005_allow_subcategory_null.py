from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0004_alter_emailotp_code"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "content_modulepurchase" ALTER COLUMN "subcategory_id" DROP NOT NULL;'
            ),
            reverse_sql=(
                'ALTER TABLE "content_modulepurchase" ALTER COLUMN "subcategory_id" SET NOT NULL;'
            ),
        ),
    ]
