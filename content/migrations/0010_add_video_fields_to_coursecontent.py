from django.db import migrations, models


def add_missing_coursecontent_columns(apps, schema_editor):
    connection = schema_editor.connection
    table_name = 'content_coursecontent'

    with connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

        if 'video_url' not in existing_columns:
            cursor.execute(
                "ALTER TABLE content_coursecontent ADD COLUMN video_url varchar(200) NULL"
            )
        if 'duration_seconds' not in existing_columns:
            cursor.execute(
                "ALTER TABLE content_coursecontent ADD COLUMN duration_seconds integer NULL DEFAULT 0"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0009_add_content_type_to_coursecontent'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_missing_coursecontent_columns, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='coursecontent',
                    name='video_url',
                    field=models.URLField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='coursecontent',
                    name='duration_seconds',
                    field=models.PositiveIntegerField(blank=True, default=0, null=True),
                ),
            ],
        ),
    ]
