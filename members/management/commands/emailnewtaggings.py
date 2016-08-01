from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from django.utils import timezone
from members.models import Tagging
import datetime
import logging

__author__ = 'adrian'

XIS_EMAIL = "Xerocraft Internal Systems <xis@xerocraft.org>"

class Command(BaseCommand):

    help = "Email reports of new taggings are sent to members that authorized those taggings."

    @staticmethod
    def send_report(member, tagging_list):

        text_content_template = get_template('members/email-taggings-report.txt')
        html_content_template = get_template('members/email-taggings-report.html')
        d = Context({
            'member': member,
            'tagging_list': tagging_list,
        })
        subject = "New Taggings Report, " + datetime.date.today().strftime('%a %b %d')
        from_email = XIS_EMAIL
        bcc_email = XIS_EMAIL
        to = member.email
        text_content = text_content_template.render(d)
        html_content = html_content_template.render(d)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [bcc_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    def handle(self, *args, **options):
        tagging_lists = {}

        logger = logging.getLogger("members")

        # Process yesterday's taggings , gathering them by member:
        oneday = datetime.timedelta(days=1)
        yesterday = datetime.date.today() - oneday
        yesterday_start = datetime.datetime.combine(yesterday,datetime.time(0,0,0,0,timezone.get_default_timezone()))
        yesterday_end = yesterday_start + oneday
        for tagging in Tagging.objects.filter(date_tagged__gte=yesterday_start, date_tagged__lt=yesterday_end):
            member = tagging.authorizing_member
            if member is None: continue
            if member not in tagging_lists: tagging_lists[member] = []
            tagging_lists[member] += [tagging]

        # Look for work lists with totals that have changed since last report:
        for member, tagging_list in tagging_lists.items():
            if member.email == "": continue
            logger.info("Sent email to %s regarding authorized taggings", member)
            Command.send_report(member, tagging_list)
