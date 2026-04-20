from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0007_emailotp'),
    ]

    operations = [
        migrations.AddField(
            model_name='modulepurchase',
            name='is_purchased',
            field=models.BooleanField(default=False),
        ),
    ]
