# Generated by Django 4.1.7 on 2023-05-20 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radhatamapp', '0044_alter_functionmeta_return_sql'),
    ]

    operations = [
        migrations.AlterField(
            model_name='functionmeta',
            name='return_sql',
            field=models.TextField(max_length=1024),
        ),
    ]
