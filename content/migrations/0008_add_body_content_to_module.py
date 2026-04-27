from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE content_module ADD COLUMN body_content text NOT NULL DEFAULT '';",
            reverse_sql="ALTER TABLE content_module DROP COLUMN body_content;",
        ),
    ]
