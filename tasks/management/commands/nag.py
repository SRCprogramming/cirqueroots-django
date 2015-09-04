__author__ = 'adrian'

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from tasks.models import Task, Claim, Nag
from members.models import Member
import datetime
from decimal import Decimal


class Command(BaseCommand):

    help = "Emails members asking them to work tasks."

    def handle(self, *args, **options):

        # Find out who's doing what over the next week.
        today = datetime.date.today()
        nextweek = today + datetime.timedelta(weeks=+1)
        already_scheduled = Claim.sum_in_period(today,nextweek)

        # Determine who has already signed up for "a lot" of work already. Threshold value is arbitrary.
        heavily_scheduled = set([member for member,hours in already_scheduled.items() if hours >= 6.0])

        # Cycle through the next week's NAGGING tasks to see which need workers and who should be nagged.
        nag_lists = {}
        for task in Task.objects.filter(scheduled_date__gte=today).filter(scheduled_date__lte=nextweek).filter(should_nag=True):
            if not task.is_fully_claimed():
                if not task.work_done:
                    potentials = task.all_eligible_claimants() - task.current_claimants()
                    # If a given member is already heavily scheduled this week, don't nag them except for tasks today or tomorrow that aren't fully staffed.
                    if (task.scheduled_date - today) > datetime.timedelta(days=1):
                        potentials -= heavily_scheduled
                    # People without email addresses can't be nagged:
                    potentials = [p for p in potentials if p.email > ""]
                    for member in potentials:
                        if member not in nag_lists:
                            nag_lists[member] = []
                        nag_lists[member] += [task]

        # Send email messages:
        text_content_template = get_template('tasks/email_nag_template.txt')
        html_content_template = get_template('tasks/email_nag_template.html')
        for member,tasks in nag_lists.items():

            b64,md5 = Member.generate_auth_token_str(
                lambda token: Nag.objects.filter(auth_token_md5=token).count() == 0 # uniqueness test
            )

            nag = Nag.objects.create(who=member, auth_token_md5=md5)
            nag.tasks.add(*tasks)

            d = Context({
                'token': b64,
                'member': member,
                'tasks': tasks,
                'host': 'http://xerocraft-django.herokuapp.com'
            })
            subject = 'Call for Volunteers'
            from_email = 'Volunteer Coordinator <volunteer@xerocraft.org>'
            to = member.email
            text_content = text_content_template.render(d)
            html_content = html_content_template.render(d)
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            msg.send()