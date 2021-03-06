# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Claim',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('date', models.DateField()),
                ('status', models.CharField(max_length=1, choices=[('C', 'Current Claim'), ('X', 'Expired Claim'), ('Q', 'Queued Claim')])),
                ('member', models.ForeignKey(to='members.Member')),
            ],
        ),
        migrations.CreateModel(
            name='RecurringTaskTemplate',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('instructions', models.TextField(max_length=2048, help_text='Instructions for completing the task.', blank=True)),
                ('short_desc', models.CharField(max_length=40, help_text='A short description/name for the task.')),
                ('max_claimants', models.IntegerField(default=1, help_text='The maximum number of members that can simultaneously claim/work the task, often 1.')),
                ('work_estimate', models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=5, help_text='An estimate of how much work this tasks requires, in hours (e.g. 1.25).<br/>This is work time, not elapsed time.')),
                ('start_date', models.DateField(help_text='Choose a date for the first instance of the recurring task.')),
                ('active', models.BooleanField(help_text='Additional tasks will be created only when the template is active.', default=True)),
                ('first', models.BooleanField(default=False)),
                ('second', models.BooleanField(default=False)),
                ('third', models.BooleanField(default=False)),
                ('fourth', models.BooleanField(default=False)),
                ('last', models.BooleanField(default=False)),
                ('every', models.BooleanField(default=False)),
                ('monday', models.BooleanField(default=False)),
                ('tuesday', models.BooleanField(default=False)),
                ('wednesday', models.BooleanField(default=False)),
                ('thursday', models.BooleanField(default=False)),
                ('friday', models.BooleanField(default=False)),
                ('saturday', models.BooleanField(default=False)),
                ('sunday', models.BooleanField(default=False)),
                ('repeat_interval', models.SmallIntegerField(blank=True, null=True, help_text='Minimum number of days between recurrences, e.g. 14 for every two weeks.')),
                ('flexible_dates', models.NullBooleanField(choices=[(True, 'Yes'), (False, 'No'), (None, 'N/A')], help_text="Select 'No' if this task must occur on specific regularly-spaced dates.<br/>Select 'Yes' if the task is like an oil change that should happen every 90 days, but not on any specific date.", default=None)),
                ('eligible_claimants', models.ManyToManyField(related_name='claimable_TaskTemplates', blank=True, to='members.Member', help_text='Anybody chosen is eligible to claim the task.<br/>')),
                ('eligible_tags', models.ManyToManyField(related_name='claimable_TaskTemplates', blank=True, to='members.Tag', help_text='Anybody that has one of the chosen tags is eligible to claim the task.<br/>')),
                ('owner', models.ForeignKey(related_name='owned_TaskTemplates', null=True, to='members.Member', on_delete=django.db.models.deletion.SET_NULL, help_text='The member that asked for this task to be created or has taken responsibility for its content.<br/>This is almost certainly not the person who will claim the task and do the work.', blank=True)),
                ('reviewer', models.ForeignKey(related_name='reviewableTaskTemplates', null=True, to='members.Member', on_delete=django.db.models.deletion.SET_NULL, help_text='If required, a member who will review the work once its completed.', blank=True)),
                ('uninterested', models.ManyToManyField(related_name='uninteresting_TaskTemplates', blank=True, to='members.Member', help_text='Members that are not interested in this item.')),
            ],
            options={
                'ordering': ['short_desc'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('instructions', models.TextField(max_length=2048, help_text='Instructions for completing the task.', blank=True)),
                ('short_desc', models.CharField(max_length=40, help_text='A short description/name for the task.')),
                ('max_claimants', models.IntegerField(default=1, help_text='The maximum number of members that can simultaneously claim/work the task, often 1.')),
                ('work_estimate', models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=5, help_text='An estimate of how much work this tasks requires, in hours (e.g. 1.25).<br/>This is work time, not elapsed time.')),
                ('creation_date', models.DateField(default=datetime.date.today, help_text='The date on which this task was originally created, for tracking slippage.')),
                ('scheduled_date', models.DateField(blank=True, null=True, help_text='If appropriate, set a date on which the task must be performed.')),
                ('deadline', models.DateField(blank=True, null=True, help_text='If appropriate, specify a deadline by which the task must be completed.')),
                ('work_done', models.BooleanField(help_text='The person who does the work sets this to true when the work is completely done.', default=False)),
                ('work_accepted', models.NullBooleanField(choices=[(True, 'Yes'), (False, 'No'), (None, 'N/A')], help_text='If there is a reviewer for this task, the reviewer sets this to true or false once the worker has said that the work is done.')),
                ('claimants', models.ManyToManyField(related_name='tasks_claimed', to='members.Member', through='tasks.Claim')),
                ('depends_on', models.ManyToManyField(related_name='prerequisite_for', to='tasks.Task', help_text='If appropriate, specify what tasks must be completed before this one can start.')),
                ('eligible_claimants', models.ManyToManyField(related_name='claimable_Tasks', blank=True, to='members.Member', help_text='Anybody chosen is eligible to claim the task.<br/>')),
                ('eligible_tags', models.ManyToManyField(related_name='claimable_Tasks', blank=True, to='members.Tag', help_text='Anybody that has one of the chosen tags is eligible to claim the task.<br/>')),
                ('owner', models.ForeignKey(related_name='owned_Tasks', null=True, to='members.Member', on_delete=django.db.models.deletion.SET_NULL, help_text='The member that asked for this task to be created or has taken responsibility for its content.<br/>This is almost certainly not the person who will claim the task and do the work.', blank=True)),
                ('recurring_task_template', models.ForeignKey(null=True, to='tasks.RecurringTaskTemplate', on_delete=django.db.models.deletion.SET_NULL, blank=True)),
                ('reviewer', models.ForeignKey(related_name='reviewableTasks', null=True, to='members.Member', on_delete=django.db.models.deletion.SET_NULL, help_text='If required, a member who will review the work once its completed.', blank=True)),
                ('uninterested', models.ManyToManyField(related_name='uninteresting_Tasks', blank=True, to='members.Member', help_text='Members that are not interested in this item.')),
            ],
            options={
                'ordering': ['short_desc'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TaskNote',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('content', models.TextField(max_length=2048, help_text='Anything you want to say about the task. Questions, hints, problems, review feedback, etc.')),
                ('author', models.ForeignKey(related_name='task_notes_authored', null=True, to='members.Member', on_delete=django.db.models.deletion.SET_NULL, help_text='The member who wrote this note.', blank=True)),
                ('task', models.ForeignKey(to='tasks.Task')),
            ],
        ),
        migrations.CreateModel(
            name='Work',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('hours', models.DecimalField(max_digits=5, decimal_places=2, help_text='The actual time worked, in hours (e.g. 1.25). This is work time, not elapsed time.')),
                ('task', models.ForeignKey(to='tasks.Task', help_text='The task that was worked.')),
                ('worker', models.ForeignKey(to='members.Member', help_text='Member that did work toward completing task.')),
            ],
        ),
        migrations.AddField(
            model_name='task',
            name='workers',
            field=models.ManyToManyField(related_name='tasks_worked', to='members.Member', through='tasks.Work'),
        ),
        migrations.AddField(
            model_name='claim',
            name='task',
            field=models.ForeignKey(to='tasks.Task'),
        ),
    ]
