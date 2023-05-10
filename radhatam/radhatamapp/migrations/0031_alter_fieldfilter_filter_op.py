# Generated by Django 4.1.6 on 2023-02-18 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radhatamapp', '0030_alter_fieldfilter_filter_op'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fieldfilter',
            name='filter_op',
            field=models.CharField(choices=[('exact', '='), ('not', '!=')], default='equal', max_length=30),
        ),
    ]
