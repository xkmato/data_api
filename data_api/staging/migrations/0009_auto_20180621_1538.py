# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-06-21 15:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staging', '0008_auto_20180621_1536'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='query',
            field=models.TextField(blank=True, null=True),
        ),
    ]