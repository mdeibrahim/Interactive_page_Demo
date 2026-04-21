from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0002_create_paymentinstruction_table"),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentinstruction',
            name='image',
            field=models.ImageField(upload_to='payment_instructions/', blank=True, null=True),
        ),
    ]
