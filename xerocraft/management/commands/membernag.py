
# Standard
from datetime import datetime, timedelta, time
import logging

# Third Party
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from django.utils import timezone
from freezegun import freeze_time

# Local
from members.models import Membership, VisitEvent, PaidMembershipNudge

__author__ = 'adrian'

VC_EMAIL = "Volunteer Coordinator <volunteer@xerocraft.org>"
XIS_EMAIL = "Xerocraft Internal Systems <xis@xerocraft.org>"

# Why aren't these defined in datetime?
MONDAY    = 0
TUESDAY   = 1
WEDNESDAY = 2
THURSDAY  = 3
FRIDAY    = 4
SATURDAY  = 5
SUNDAY    = 6

# TODO: This command is Xerocraft specific. Move to "xerocraft"?

OPENHACKS = [
    (TUESDAY, time(18, 0, 0), time(22, 0, 0)),
    (THURSDAY, time(19, 0, 0), time(22, 0, 0)),
    (SATURDAY, time(12, 0, 0), time(16, 0, 0)),
]


# TODO: Combine this command with the login scraper so it sends email shortly after person arrives?
# TODO: Should send an alert to staff members' Xerocraft apps.
class Command(BaseCommand):

    help = "Emails unpaid members who visit during paid member hours."
    logger = logging.getLogger("xerocraft-django")
    bad_visits = None
    bad_visitors = None
    tz = timezone.get_default_timezone()
    today = None
    yesterday = None

    def add_arguments(self, parser):
        # Intended for test cases which will run on a specific date.
        parser.add_argument('--date')

    def note_bad_visit(self, visit, pm: Membership):

        if visit.who in self.bad_visits:
            self.bad_visits[visit.who].append(visit)
        else:
            self.bad_visits[visit.who] = [visit]

        if visit.who not in self.bad_visitors:
            self.bad_visitors[visit.who] = pm

    def process_bad_visits(self):
        for member, pm in self.bad_visitors.items():

            if member.email in [None, ""]:
                self.logger.info("Bad visit by %s but they haven't provided an email address.", member.username)
                continue

            # Send email messages:
            text_content_template = get_template('members/email-unpaid-visit.txt')
            html_content_template = get_template('members/email-unpaid-visit.html')

            visits = self.bad_visits[member]
            visits = [timezone.localtime(v.when) for v in visits]

            d = Context({
                'friendly_name': member.friendly_name,
                'paid_membership': pm,
                'bad_visit': visits[0],
            })

            subject = 'Time to Renew your Xerocraft Membership'
            from_email = XIS_EMAIL
            bcc_email = XIS_EMAIL
            to = from_email  # TODO: Testing only. Not ready to send to actual members.
            text_content = text_content_template.render(d)
            html_content = html_content_template.render(d)
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [bcc_email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            self.logger.info("Email sent to %s re bad visit.", member.username)
            PaidMembershipNudge.objects.create(member=member)

    def during_open_hack(self, visit):
        assert timezone.localtime(visit.when).date() == self.yesterday.date()
        time_leeway = timedelta(hours=1)
        for (hack_dow, hack_start, hack_end) in OPENHACKS:
            visit_dow = timezone.localtime(visit.when).weekday()
            if visit_dow == hack_dow:
                hack_start = self.tz.localize(datetime.combine(self.yesterday, hack_start))
                hack_end = self.tz.localize(datetime.combine(self.yesterday, hack_end))
                if hack_start-time_leeway <= visit.when <= hack_end+time_leeway:
                    return True
        return False

    def nag_for_unpaid_visits(self):

        self.bad_visits = {}
        self.bad_visitors = {}

        date_leeway = timedelta(days=14)

        yesterdays_visits = VisitEvent.objects.filter(when__range=[self.yesterday, self.today])
        for visit in yesterdays_visits:

            # Ignore the visit if it was during open hacks because all open hack visits are OK.
            if self.during_open_hack(visit): continue

            # Ignore visits by directors (who have decided they don't need to pay)
            if visit.who.is_tagged_with("Director"): continue

            # Get most recent membership for visitor.
            try:
                pm = Membership.objects.filter(member=visit.who).latest('start_date')
            except Membership.DoesNotExist:
                # Don't nag people that have NEVER paid because either:
                #  1) It's too soon to bother the member.
                #  2) The member is hopeless and will never pay.
                continue

            if pm.start_date > self.yesterday.date():
                # Don't nag because there is a future paid membership.
                continue
            elif pm.start_date <= self.yesterday.date() <= pm.end_date:
                # Don't nag because the latest paid membership covers the visit.
                continue
            elif self.yesterday.date() <= pm.end_date+date_leeway:
                # Don't nag yet because we're giving the member some leeway to renew.
                continue
            else:
                # Nag this user.
                self.note_bad_visit(visit, pm)

        self.process_bad_visits()
        return

    def handle(self, *args, **options):

        # The "date" option supports test cases that run on specific dates.
        test_time = options['date']
        if test_time is not None:
            freezer = freeze_time(test_time)
            freezer.start()

        self.today = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
        self.today = timezone.make_aware(self.today, timezone.get_default_timezone())
        self.yesterday = self.today - timedelta(days=1)

        self.nag_for_unpaid_visits()
        # There may be other sorts of nags here, in the future.

        if test_time is not None:
            freezer.stop()