from django.db import migrations


def create_paymentinstruction_table(apps, schema_editor):
    PaymentInstruction = apps.get_model('content', 'PaymentInstruction')
    db_table = PaymentInstruction._meta.db_table
    try:
        existing = schema_editor.connection.introspection.table_names()
    except Exception:
        existing = []
    if db_table in existing:
        return
    schema_editor.create_model(PaymentInstruction)


def drop_paymentinstruction_table(apps, schema_editor):
    PaymentInstruction = apps.get_model('content', 'PaymentInstruction')
    db_table = PaymentInstruction._meta.db_table
    try:
        existing = schema_editor.connection.introspection.table_names()
    except Exception:
        existing = []
    if db_table in existing:
        schema_editor.delete_model(PaymentInstruction)


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_paymentinstruction_table, reverse_code=drop_paymentinstruction_table),
    ]
