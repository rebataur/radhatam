# Generated by Django 4.1.7 on 2023-06-10 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radhatamapp', '0048_alter_derivedfieldargument_argument_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='derivedfieldargument',
            name='argument_value',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='fieldfilter',
            name='filter_op',
            field=models.CharField(choices=[('eq', 'Exact'), ('not', 'Not'), ('gt', 'Greater Than'), ('gte', 'Greater Than Equal To'), ('lt', 'Less Than'), ('lte', 'Less Than Equal')], default='EXACT', max_length=30),
        ),
    ]