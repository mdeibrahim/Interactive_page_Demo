from django.db import migrations, models
import django.db.models.deletion


def create_interactivecontent_table_if_missing(apps, schema_editor):
    from content.models import InteractiveContent

    table_name = InteractiveContent._meta.db_table
    try:
        existing = schema_editor.connection.introspection.table_names()
    except Exception:
        existing = []

    if table_name in existing:
        return

    schema_editor.create_model(InteractiveContent)


def drop_interactivecontent_table_if_exists(apps, schema_editor):
    from content.models import InteractiveContent

    table_name = InteractiveContent._meta.db_table
    try:
        existing = schema_editor.connection.introspection.table_names()
    except Exception:
        existing = []

    if table_name not in existing:
        return

    schema_editor.delete_model(InteractiveContent)


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0006_allow_coursecontent_videourl_null'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    create_interactivecontent_table_if_missing,
                    reverse_code=drop_interactivecontent_table_if_exists,
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='InteractiveContent',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=255)),
                        ('content_type', models.CharField(choices=[('text', 'Text / Rich HTML'), ('image', 'Image'), ('audio', 'Audio'), ('video', 'Video (Upload)'), ('youtube', 'YouTube Video')], max_length=20)),
                        ('text_content', models.TextField(blank=True, help_text="For 'text' type — can include HTML with bold/italic/underline")),
                        ('image', models.ImageField(blank=True, null=True, upload_to='interactive/images/')),
                        ('audio', models.FileField(blank=True, null=True, upload_to='interactive/audio/')),
                        ('video', models.FileField(blank=True, null=True, upload_to='interactive/videos/')),
                        ('youtube_url', models.URLField(blank=True, help_text='Full YouTube URL e.g. https://www.youtube.com/watch?v=...')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('module', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='interactive_contents', to='content.module')),
                    ],
                ),
            ],
        ),
    ]
