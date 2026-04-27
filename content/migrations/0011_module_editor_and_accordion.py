from django.db import migrations, models


def add_missing_module_updated_at(apps, schema_editor):
    connection = schema_editor.connection
    table_name = 'content_module'

    with connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }
        if 'updated_at' not in existing_columns:
            cursor.execute(
                "ALTER TABLE content_module ADD COLUMN updated_at datetime NULL"
            )
            cursor.execute(
                "UPDATE content_module SET updated_at = created_at WHERE updated_at IS NULL"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0010_add_video_fields_to_coursecontent'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_missing_module_updated_at, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='module',
                    name='updated_at',
                    field=models.DateTimeField(auto_now=True, null=True),
                ),
            ],
        ),
        migrations.CreateModel(
            name='ModuleAccordionSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_open_by_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('module', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='accordion_sections', to='content.module')),
            ],
            options={
                'ordering': ['order', 'created_at'],
            },
        ),
    ]
