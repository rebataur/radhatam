# Generated by Django 4.2 on 2023-05-10 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radhatamapp', '0041_alter_argumentmeta_type_alter_field_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='field',
            name='datatype',
            field=models.CharField(choices=[('TEXT', 'Text'), ('INTEGER', 'Integer'), ('NUMERIC', 'Numeric'), ('DATE', 'Date'), ('BINARY', 'Binary'), ('PNG_IMAGE', 'PNG Image')], default='TEXT', max_length=64),
        ),
        migrations.AlterField(
            model_name='argumentmeta',
            name='type',
            field=models.CharField(choices=[('TEXT', 'Text'), ('INTEGER', 'Integer'), ('NUMERIC', 'Numeric'), ('DATE', 'Date'), ('BINARY', 'Binary'), ('PNG_IMAGE', 'PNG Image')], default='TEXT', max_length=20),
        ),
        migrations.AlterField(
            model_name='field',
            name='type',
            field=models.CharField(choices=[('COLUMN', 'Column'), ('DERIVED', 'Derived'), ('CALCULATED', 'Calculated')], default='COLUMN', max_length=64),
        ),
        migrations.AlterField(
            model_name='functionmeta',
            name='return_type',
            field=models.CharField(choices=[('TEXT', 'Text'), ('INTEGER', 'Integer'), ('NUMERIC', 'Numeric'), ('DATE', 'Date'), ('BINARY', 'Binary'), ('PNG_IMAGE', 'PNG Image')], default='TEXT', max_length=20),
        ),
        migrations.AlterField(
            model_name='functionmeta',
            name='type',
            field=models.CharField(choices=[('CALCULATION', 'Calculation'), ('VISUALIZE', 'Visualize'), ('DATASCIENCE', 'DataScience')], default='CALCULATION', max_length=20),
        ),
    ]
