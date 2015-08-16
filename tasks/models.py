from django.db import models
from datetime import date, timedelta
from members import models as mm

# TODO: Rework various validate() methods into Model.clean()? See Django's "model validation" docs.

# TODO: class MetaTag?  E.g. Tag instructor tags with "instructor" meta-tag?

# TODO: Import various *Field classes and remove "models."?


# class MetaTag(models.Model):
#
#     name = models.CharField(max_length=40,
#         help_text="A short name for the metatag.")
#     meaning = models.TextField(max_length=500,
#         help_text="A discussion of the metatag's semantics. What does it mean? What does it NOT mean?")
#
#     def __str__(self):
#         return self.name

def make_TaskMixin(dest_class_alias):
    """This function tunes the mix-in to avoid reverse accessor clashes.
-   The rest of the mix-in is identical for both Task and RecurringTaskTemplate.
-   """

    class TaskMixin(models.Model):
        """Defines fields that are common between RecurringTaskTemplate and Task.
        When a task is created from the template, these fields are copied from the template to the task.
        Help text describes the fields in terms of their role in Task.
        """

        owner = models.ForeignKey(mm.Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_"+dest_class_alias,
            help_text="The member that asked for this task to be created or has taken responsibility for its content.<br/>This is almost certainly not the person who will claim the task and do the work.")
        instructions = models.TextField(max_length=2048, blank=True,
            help_text="Instructions for completing the task.")
        short_desc = models.CharField(max_length=40,
            help_text="A short description/name for the task.")
        max_claimants = models.IntegerField(default=1,
            help_text="The maximum number of members that can simultaneously claim/work the task, often 1.")
        eligible_claimants = models.ManyToManyField(mm.Member, blank=True, symmetrical=False, related_name="claimable_"+dest_class_alias,
            help_text="Anybody chosen is eligible to claim the task.<br/>")
        eligible_tags = models.ManyToManyField(mm.Tag, blank=True, symmetrical=False, related_name="claimable_"+dest_class_alias,
            help_text="Anybody that has one of the chosen tags is eligible to claim the task.<br/>")
        reviewer = models.ForeignKey(mm.Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewable"+dest_class_alias,
            help_text="If required, a member who will review the work once its completed.")
        work_estimate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
            help_text="An estimate of how much work this tasks requires, in hours (e.g. 1.25).<br/>This is work time, not elapsed time.")
        uninterested = models.ManyToManyField(mm.Member, blank=True, symmetrical=False, related_name="uninteresting_"+dest_class_alias,
            help_text="Members that are not interested in this item.")
        start_time = models.TimeField(null=True, blank=True,
            help_text="The time at which the task should being, if any.")
        end_time = models.TimeField(null=True, blank=True,
            help_text="The time at which the task should end, if any.")

        class Meta:
            abstract = True

    return TaskMixin

class RecurringTaskTemplate(make_TaskMixin("TaskTemplates")):
    """Uses two mutually exclusive methods to define a schedule for recurring tasks.
    (1) A 'day-of-week vs nth-of-month' matrix for schedules like "every first and third Thursday"
    (2) A 'repeat delay' value for schedules like "every 30 days"
    """

    start_date = models.DateField(help_text="Choose a date for the first instance of the recurring task.")
    active = models.BooleanField(default=True, help_text="Additional tasks will be created only when the template is active.")

    # Weekday of month:
    first = models.BooleanField(default=False)  #, help_text="Task will recur on first weekday in the month.")
    second = models.BooleanField(default=False)  #, help_text="Task will recur on second weekday in the month.")
    third = models.BooleanField(default=False)  #, help_text="Task will recur on third weekday in the month.")
    fourth = models.BooleanField(default=False)  #, help_text="Task will recur on fourth weekday in the month.")
    last = models.BooleanField(default=False)  #, help_text="Task will recur on last weekday in the month. This will be 4th or 5th weekday, depending on calendar.")
    every = models.BooleanField(default=False)  #, help_text="Task recur every week")

    # Day of week:
    monday = models.BooleanField(default=False)  #, help_text="Task will recur on Monday.")
    tuesday = models.BooleanField(default=False)  #, help_text="Task will recur on Tuesday.")
    wednesday = models.BooleanField(default=False)  #, help_text="Task will recur on Wednesday.")
    thursday = models.BooleanField(default=False)  #, help_text="Task will recur on Thursday.")
    friday = models.BooleanField(default=False)  #, help_text="Task will recur on Friday.")
    saturday = models.BooleanField(default=False)  #, help_text="Task will recur a Saturday.")
    sunday = models.BooleanField(default=False)  #, help_text="Task will recur a Sunday.")

    # Every X days:
    repeat_interval = models.SmallIntegerField(null=True, blank=True, help_text="Minimum number of days between recurrences, e.g. 14 for every two weeks.")
    #TODO: flexible_dates should be set to "No" if repeat_interval is set to a value.  Should be set to "N/A" if repeat_interval becomes None.
    flexible_dates = models.NullBooleanField(default=None, choices=[(True, "Yes"), (False, "No"), (None, "N/A")], help_text="Select 'No' if this task must occur on specific regularly-spaced dates.<br/>Select 'Yes' if the task is like an oil change that should happen every 90 days, but not on any specific date.")

    def greatest_scheduled_date(self):
        "Of the Tasks that correspond to this template, returns the greatest scheduled_date."

        if len(self.task_set.all()) == 0:
            # Nothing is scheduled yet but nothing can be scheduled before start_date.
            # So, pretend that day before start_date is the greatest scheduled date.
            result = self.start_date + timedelta(days = -1)
            return result

        scheduled_dates = map(lambda x: x.scheduled_date, self.task_set.all())
        return max(scheduled_dates)

    def date_matches_template(self, d: date):
        """
        :param d: Date to be tested.
        :return: Boolean indicating if d matches the day-of-week and ordinal-in-month specified by the template.
        """

        if self.repeats_at_intervals():
            return self.date_matches_template_intervals(d)

        if self.repeats_on_certain_days():
            return self.date_matches_template_certain_days(d)

    def date_matches_template_intervals(self, date_considered: date):
        last_date = self.greatest_scheduled_date()
        days_since = date_considered - last_date
        return days_since.days == self.repeat_interval

    def date_matches_template_certain_days(self, d: date):

        def nth_xday(d):
            """ Return a value which indicates that date d is the nth <x>day of the month. """
            dom_num = d.day
            ord_num = 1
            while dom_num > 7:
                dom_num -= 7
                ord_num += 1
            return ord_num

        def is_last_xday(d):
            """ Return a value which indicates whether date d is the LAST <x>day of the month. """
            month = d.month
            d += timedelta(days = +1)
            return True if d.month > month else False

        dow_num = d.weekday() # day-of-week number
        day_matches = (dow_num==0 and self.monday) \
            or (dow_num==1 and self.tuesday) \
            or (dow_num==2 and self.wednesday) \
            or (dow_num==3 and self.thursday) \
            or (dow_num==4 and self.friday) \
            or (dow_num==5 and self.saturday) \
            or (dow_num==6 and self.sunday)

        if not day_matches: return False  # Doesn't match template if day-of-week doesn't match.
        if self.every: return True  # Does match if it happens every week and the day-of-week matches.
        if is_last_xday(d) and self.last: return True # Check for last <x>day match.

        # Otherwise, figure out the ordinal and see if we match it.
        ord_num = nth_xday(d)
        ordinal_matches = (ord_num==1 and self.first) \
            or (ord_num==2 and self.second) \
            or (ord_num==3 and self.third) \
            or (ord_num==4 and self.fourth) \
            or (ord_num==4 and self.last)

        return ordinal_matches

    def is_dow_chosen(self):
        return self.monday    \
            or self.tuesday   \
            or self.wednesday \
            or self.thursday  \
            or self.friday    \
            or self.saturday  \
            or self.sunday

    def is_ordinal_chosen(self):
        return self.first  \
            or self.second \
            or self.third  \
            or self.fourth \
            or self.last   \
            or self.every

    def repeats_on_certain_days(self):
        return self.is_dow_chosen() and self.is_ordinal_chosen()

    def repeats_at_intervals(self):
        return self.repeat_interval is not None and self.flexible_dates is not None

    def create_tasks(self, max_days_in_advance):
        """Creates/schedules new tasks from current date (inclusive).
        Stops when scheduling a new task would be more than max_days_in_advance from current date.
        Does not create/schedule a task on date D if one already exists for date D.
        Does nothing if the template is not active.
        """

        if not self.active: return

        curr = date.today() + timedelta(days = -1)
        stop = date.today() + timedelta(days = max_days_in_advance)
        while curr < stop:
            curr += timedelta(days = +1)
            if self.date_matches_template(curr):

                # Check if task is already instantiated for curr date and skip creation if it does.
                if Task.objects.filter(recurring_task_template=self, scheduled_date=curr).count() > 0:
                    continue

                t = Task.objects.create(recurring_task_template=self, creation_date = date.today())
                t.scheduled_date = curr

                # Copy mixin fields from template to instance:
                t.owner = self.owner
                t.instructions = self.instructions
                t.short_desc = self.short_desc
                t.reviewer = self.reviewer
                t.work_estimate = self.work_estimate
                t.max_claimants = self.max_claimants
                t.eligible_claimants = self.eligible_claimants.all()
                t.eligible_tags = self.eligible_tags.all()
                t.uninterested = self.uninterested.all()
                t.start_time = self.start_time
                t.end_time = self.end_time
                t.save()

    def validate(self):
        if self.last and self.fourth:
            return False, "Choose either fourth week or last week, not both."
        if self.every and (self.first or self.second or self.third or self.fourth or self.last):
            return False, "If you choose 'every week' don't choose any other weeks."
        if self.work_estimate < 0:
            # zero will mean "not yet estimated" but anything that has been estimated must have work > 0.
            return False, "Invalid work estimate."
        if self.eligible_claimants is None and self.eligible_tags is None:
            return False, "One or more people and/or one or more tags must be selected."
        return True, "Looks good."

    def recurrence_str(self):
        days_of_week = self.repeats_on_certain_days()
        intervals = self.repeats_at_intervals()
        if days_of_week and intervals:
            return "?"
        if (not days_of_week) and (not intervals):
            return "?"
        if days_of_week:
            blank = '\u25CC'
            return "%s%s%s%s%s%s%s" % (
                "M" if self.monday else blank,
                "T" if self.tuesday else blank,
                "W" if self.wednesday else blank,
                "T" if self.thursday else blank,
                "F" if self.friday else blank,
                "S" if self.saturday else blank,
                "S" if self.sunday else blank,
            )
        if intervals:
            if self.repeat_interval == 1:
                return "every day"
            else:
                return "every %d days" % self.repeat_interval
        return "X"
    recurrence_str.short_description = "Recurrence"

    def __str__(self):
        return "%s [%s]" % (self.short_desc, self.recurrence_str())

    class Meta:
        ordering = ['short_desc','-monday','-tuesday','-wednesday','-thursday','-friday','-saturday','-sunday']


class Claim(models.Model):

    CURRENT = "C"
    EXPIRED = "X"
    QUEUED = "Q"
    CLAIM_STATUS_CHOICES = [
        (CURRENT, "Current"),
        (EXPIRED, "Expired"),
        (QUEUED, "Queued")
    ]
    task = models.ForeignKey('Task')
    member = models.ForeignKey(mm.Member)
    date = models.DateField()
    hours_claimed = models.DecimalField(max_digits=5, decimal_places=2,
        help_text="The actual time claimed, in hours (e.g. 1.25). This is work time, not elapsed time.")
    status = models.CharField(max_length=1, choices=CLAIM_STATUS_CHOICES)


class Work(models.Model):

    worker = models.ForeignKey(mm.Member,
        help_text="Member that did work toward completing task.")
    task = models.ForeignKey('Task',
        help_text="The task that was worked.")
    hours = models.DecimalField(max_digits=5, decimal_places=2,
        help_text="The actual time worked, in hours (e.g. 1.25). This is work time, not elapsed time.")
    when = models.DateField(null=False, default=date.today,
        help_text="The date on which the work was done.")


class Task(make_TaskMixin("Tasks")):

    creation_date = models.DateField(null=False, default=date.today,
        help_text="The date on which this task was originally created, for tracking slippage.")
    scheduled_date = models.DateField(null=True, blank=True,
        help_text="If appropriate, set a date on which the task must be performed.")
    deadline = models.DateField(null=True, blank=True,
        help_text="If appropriate, specify a deadline by which the task must be completed.")
    depends_on = models.ManyToManyField('self', symmetrical=False, related_name="prerequisite_for",
        help_text="If appropriate, specify what tasks must be completed before this one can start.")
    claimants = models.ManyToManyField(mm.Member, through=Claim, related_name="tasks_claimed",
        help_text="The people who say they are going to work on this task.")
    workers = models.ManyToManyField(mm.Member, through=Work, related_name="tasks_worked",
        help_text="The people who have actually posted hours against this task.")
    work_done = models.BooleanField(default=False,
        help_text="The person who does the work sets this to true when the work is completely done.")
    # TODO: work_accepted should be N/A if reviewer is None.  If reviewer is set, work_accepted should be set to "No".
    work_accepted = models.NullBooleanField(choices=[(True, "Yes"), (False, "No"), (None, "N/A")],
        help_text="If there is a reviewer for this task, the reviewer sets this to true or false once the worker has said that the work is done.")
    recurring_task_template = models.ForeignKey(RecurringTaskTemplate, null=True, blank=True, on_delete=models.SET_NULL)

    def is_closed(self):
        "Returns True if claimant should receive credit for the task."
        if self.reviewer is None:
            return self.work_done
        else:
            return self.work_done and self.work_accepted

    def is_open(self):
        "Returns True if the task isn't yet completed or if there's a reviewer who hasn't yet accepted it."
        return not self.is_closed()

    def validate(self):
        #TODO: Sum of claim hours should be <= work_estimate.
        #
        if self.work_accepted and not self.work_done:
            return False, "Work cannot be reviewed before it is marked as completed."
        if self.prev_claimed_by == self.claimed_by:
            return False, "Member cannot claim a task they've previously claimed. Somebody else has to get a chance at it."
        if self.work_estimate < 0:
            # REVIEW: zero will mean "not yet estimated" but anything that has been estimated must have work > 0.
            return False, "Invalid work estimate."
        if self.recurring_task_template is not None and self.scheduled_date is None:
            return False, "A task corresponding to a ScheduledTaskTemplate must have a scheduled date."
        return True, "Looks good."

    def scheduled_weekday(self):
        return self.scheduled_date.strftime('%A') if self.scheduled_date is not None else '-'
        # return week[self.scheduled_date.weekday()] if self.scheduled_date is not None else '-'
    scheduled_weekday.short_description = "Weekday"

    def __str__(self):
        if self.deadline is None:
            return "%s" % (self.short_desc)
        else:
            return "%s [%s deadline]" % (self.short_desc, self.deadline)

    class Meta:
        ordering = ['scheduled_date','start_time']

class TaskNote(models.Model):

    # Note will become anonymous if author is deleted or author is blank.
    author = models.ForeignKey(mm.Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="task_notes_authored",
        help_text="The member who wrote this note.")

    content = models.TextField(max_length=2048,
        help_text="Anything you want to say about the task. Questions, hints, problems, review feedback, etc.")

    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    CRITICAL = "C" # The note describes a critical issue that must be resolved. E.g. work estimate is too low.
    RESOLVED = "R" # The note was previously listed as CRITICAL but the issue has been resolved.
    INFO = "I" # The note is purely informational.
    NOTE_TYPE_CHOICES = [
        (CRITICAL, "Critical"),
        (RESOLVED, "Resolved"),
        (INFO, "Informational")
    ]
    status = models.CharField(max_length=1, choices=NOTE_TYPE_CHOICES)
