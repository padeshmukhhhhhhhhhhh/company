# Generated by Django 4.2.18 on 2025-01-28 12:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_collegegroup'),
    ]

    operations = [
        migrations.AddField(
            model_name='settlement',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.student'),
        ),
    ]
