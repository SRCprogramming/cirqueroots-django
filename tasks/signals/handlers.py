from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from members.models import Member, Tag, Tagging
from tasks.models import Worker

__author__ = 'Adrian'


@receiver(post_save, sender=Tagging)
def act_on_new_tag(sender, **kwargs):
    if kwargs.get('created', True):
        pass
        """ TODO: Check to see if this new tagging makes the tagged_member eligible for a task
            they weren't previously eligible for. If so, email them with info.
        """


@receiver(post_save, sender=Member)
def create_default_worker(sender, **kwargs):
    if kwargs.get('created', True):
        w,_ = Worker.objects.get_or_create(member=kwargs.get('instance'))
