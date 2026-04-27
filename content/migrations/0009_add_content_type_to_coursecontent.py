from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0008_add_body_content_to_module'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE content_coursecontent ADD COLUMN content_type varchar(20) NOT NULL DEFAULT 'text';",
            reverse_sql="ALTER TABLE content_coursecontent DROP COLUMN content_type;",
        ),
    ]
