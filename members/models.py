# pylint: disable=C0330

# Standard
import base64
import uuid
import hashlib
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Union, Tuple

# Third Party
from django.db import models
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from nameparser import HumanName

# Local
from books.models import Sale
from abutils.utils import generate_ctrlid


TZ = timezone.get_default_timezone()


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# CTRLID Functions
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

def next_payment_ctrlid():
    raise NotImplementedError("This method is referenced by 0025_auto_20160215_1529.py but shouldn't be called.")


def next_membership_ctrlid() -> str:
    """Provides an arbitrary default value for the ctrlid field, necessary when data is being entered manually."""
    return generate_ctrlid(Membership)


def next_giftcardref_ctrlid() -> str:
    """Provides an arbitrary default value for the ctrlid field, necessary when data is being entered manually."""
    return generate_ctrlid(MembershipGiftCardReference)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# Models
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

# class MetaTag(models.Model):
#
#     name = models.CharField(max_length=40,
#         help_text="A short name for the metatag.")
#     meaning = models.TextField(max_length=500,
#         help_text="A discussion of the metatag's semantics. What does it mean? What does it NOT mean?")
#
#     def __str__(self):
#         return self.name

class Tag(models.Model):
    """ A tag represents some attribute of a Member. Examples are various skills, shop roles, or shop permissions.
    """
    name = models.CharField(max_length=40, unique=True,
        help_text="A short name for the tag.")
    meaning = models.TextField(max_length=500,
        help_text="A discussion of the tag's semantics. What does it mean? What does it NOT mean?")
    # meta_tags = models.ManyToManyField(MetaTag, blank=True,
    #     help_text="A tag can have zero or more metatags.")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Member(models.Model):
    """Represents a Xerocraft member.
    Member is an extension of auth.User that adds Xerocraft-specific state like "tags".
    """
    MEMB_CARD_STR_LEN = 32

    auth_user = models.OneToOneField('auth.User', null=False, unique=True, related_name="member",
        help_text="This must point to the corresponding auth.User object.")

    # Saving as MD5 provides some protection against read-only attacks.
    membership_card_md5 = models.CharField(max_length=MEMB_CARD_STR_LEN, null=True, blank=True,
        help_text="MD5 of the random urlsafe base64 string on the membership card.")

    membership_card_when = models.DateTimeField(null=True, blank=True,
        help_text="Date/time on which the membership card was created.")

    # phone_mac_hash = models.CharField(max_length=32,
    #     null=True, blank=True,  # MAC address tracking is opt-in
    #     help_text="MAC address of member's phone.")
    #
    # rfid_has = models.CharField(max_length=32,
    #     null=True, blank=True,  # RFIDs are issued to some members but not all
    #     help_text="MD5 of member's RFID card number.")

    tags = models.ManyToManyField(Tag, blank=True, related_name="members",
        through='Tagging', through_fields=('tagged_member', 'tag'))

    @staticmethod
    def generate_auth_token_str(is_unique):
        """Generate a token (and its md5) which will be used in nag email urls, icalendar urls, etc."""

        # Note: This is very similar to the generator in membership. Should there be one util that serves both apps?

        # Generate a token which is 32 characters of url-safe base64.
        u1 = uuid.uuid4().bytes
        u2 = uuid.uuid4().bytes
        b64 = base64.urlsafe_b64encode(u1+u2).decode()[:32]

        # Calculate md5 of the b64 and start over if there's a md5 collision
        md5 = hashlib.md5(b64.encode()).hexdigest()
        if is_unique(md5):
            return b64, md5
        else:
            # Collision detected, so try again.
            return Member.generate_auth_token_str(is_unique)

    def generate_member_card_str(self):

        def unique(token: str) -> bool:
            md5_count = Member.objects.filter(membership_card_md5=token).count()
            assert md5_count <= 1 # Greater than 1 means collision checking has somehow failed in the past.
            return md5_count == 0

        b64, md5 = Member.generate_auth_token_str(unique)
        # Save the the md5 of the base64 string in the member table.
        self.membership_card_md5 = md5
        self.membership_card_when = timezone.now()
        self.save()
        return b64

    def is_tagged_with(self, tag_name):
        return True if tag_name in [x.name for x in self.tags.all()] else False

    def can_tag_with(self, tag):
        for tagging in self.taggings.all():
            if tagging.tag.name == tag.name:
                return tagging.can_tag
        return False

    def is_domain_staff(self):  # Different than website staff.
        return self.is_tagged_with("Staff")

    def is_currently_paid(self, grace_period=timedelta(0)):
        ''' Determine whether member is currently covered by a membership with a given grace period.'''
        now = datetime.now().date()

        m = Membership.objects.filter(
            member=self,
            start_date__lte=now, end_date__gte=now-grace_period)
        if len(m) > 0:
            return True

        return False

    @property
    def first_name(self)->str:
        return self.auth_user.first_name

    @property
    def last_name(self)->str:
        return self.auth_user.last_name

    @property
    def username(self)->str:
        return self.auth_user.username

    @property
    def friendly_name(self)->str:
        """ Friendly name is the members first name. If first name not available then it's the member's username. """
        if self.first_name is not None and len(self.first_name) > 0:
            return self.first_name
        else:
            return self.username

    @property
    def email(self): return self.auth_user.email

    @property
    def is_active(self): return self.auth_user.is_active

    @staticmethod
    def get_by_card_str(member_card_str):
        member_card_md5 = hashlib.md5(member_card_str.encode()).hexdigest()
        try:
            return Member.objects.get(membership_card_md5=member_card_md5)
        except Member.DoesNotExist:
            return None

    @staticmethod
    def get_for_staff(member_card_str: str, staff_card_str: str) -> Tuple[bool, Union[Tuple['Member', 'Member'], str]]:
        """
        Given a member card string and a staff card string, return details for the member.
        :param member_card_str: The token on a member's card
        :param staff_card_str: The token on a staff member's card
        :return: (True, (member, staff)) on success, (False, error_message) on failure
        """
        # Look up the subject member and the staff member and report various possible errors:
        member = Member.get_by_card_str(member_card_str)
        if member is None: return False, "Invalid member card"
        staff = Member.get_by_card_str(staff_card_str)
        if staff is None: return False, "Invalid staff card"
        if not staff.is_domain_staff(): return False, "Not a staff member"
        return True, (member, staff)

    # TODO: Add case-insensitive index to User.username for performance.
    # TODO: Add code somewhere to ensure that email addresses for users are unique.
    @staticmethod
    def get_local_user(identifier):
        # NOTE! In code below, "identifier" means "username or email address".
        if identifier is None:
            return None
        if identifier.isspace() or len(identifier) == 0:
            return None
        try:
            user = User.objects.get(username__iexact=identifier)
            return user
        except User.DoesNotExist:
            pass
        try:
            user = User.objects.get(email__iexact=identifier)
            return user
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_local_member(identifier):
        user = Member.get_local_user(identifier)
        if user is not None: return user.member
        return None

    def validate(self):
        if self.membership_card_md5 is not None:
            if len(self.membership_card_md5) != self.MEMB_CARD_STR_LEN:
                return False, "Bad membership card string."
            if self.auth_user is None:
                return False, "Every Member must be linked to a User."
        return True, "Looks good"

    def __str__(self):
        if self.first_name != "" and self.last_name != "":
            return "%s %s" % (self.first_name, self.last_name)
        else:
            return self.username

    class Meta:
        ordering = ['auth_user__first_name', 'auth_user__last_name']


class Pushover(models.Model):

    who = models.ForeignKey(Member,
        on_delete=models.CASCADE,  # If a member is deleted, it doesn't make sense to keep their pushover info.
        help_text="The member to whom this tagging info applies.")

    key = models.CharField(max_length=30, null=False, blank=False,
        help_text="The member's User Key on Pushover.com")


class Tagging(models.Model):
    """ Intermediate table representing the many-tomany relation between Member and Tag
    """
    tagged_member = models.ForeignKey(Member, related_name='taggings',
        on_delete=models.CASCADE,  # If a member is deleted, it doesn't make sense to keep their taggings.
        help_text="The member tagged.")

    date_tagged = models.DateTimeField(null=False, blank=False, auto_now_add=True,
        help_text="Date/time on which the member was tagged.")

    tag = models.ForeignKey(Tag,
        on_delete=models.CASCADE,  # If a tag is deleted, it doesn't make sense to keep the associated taggings.
        help_text="The tag assigned to the member.")

    authorizing_member = models.ForeignKey(Member, null=True, blank=True, related_name='authorized_taggings',
        on_delete=models.SET_NULL,  # If the member who created the tagging is deleted, the tagging should remain.
        help_text="The member that authorized that the member be tagged.")
        # Note: If authorizing member is deleted, his/her Taggings shouldn't be. Hence on_delete=SET_NULL.
        # However, blank=False because somebody using admin really should provide the authorizing member info.

    can_tag = models.BooleanField(default=False,
        help_text="If True, the tagged member can be a authorizing member for this tag.")
        # Note: Above assumes that only people with a certain tag can grant that tag.
        # However, Django admins with appropriate permissions can tag any member with any tag, when required.

    @staticmethod
    def add_if_permitted(tagger, taggee, tag):
        if taggee.is_tagged_with(tag.name): return
        if tagger.can_tag_with(tag):
            Tagging.objects.create(tagged_member=taggee, tag=tag, authorizing_member=tagger)

    @staticmethod
    def remove_if_permitted(tagger, taggee, tag):
        if not taggee.is_tagged_with(tag.name): return
        if tagger.can_tag_with(tag):
            try:
                tag = Tagging.objects.get(tagged_member=taggee, tag=tag)
                tag.delete()
            except Tagging.DoesNotExist:
                pass

    def __str__(self):
        return "%s/%s/%s" % (self.tagged_member.auth_user.username, self.tag.name, self.can_tag)

    class Meta:
        unique_together = ('tagged_member', 'tag')


class MemberNote(models.Model):

    # Note will be anonymous if author is deleted or author is blank.
    author = models.ForeignKey(Member, null=True, blank=True, related_name="member_notes_authored",
        on_delete=models.SET_NULL,  # If the person who wrote the note is deleted, the note should be kept.
        help_text="The member who wrote this note.")

    content = models.TextField(max_length=2048,
        help_text="For staff. Anything you want to say about the member.")

    member = models.ForeignKey(Member,
        on_delete=models.CASCADE,  # If a member is deleted, any notes concerning them should be deleted.
        help_text="The member to which this note pertains.")


class VisitEvent(models.Model):

    who = models.ForeignKey(Member,
        on_delete=models.PROTECT,  # Visit info is too valuable to be deleted or detached from member info.
        help_text="The member who's visiting or visited.")

    when = models.DateTimeField(null=False, blank=False, default=timezone.now,
        help_text="Date/time of visit event.")

    METHOD_RFID = "R"
    METHOD_FRONT_DESK = "F"
    METHOD_MOBILE_APP = "M"
    METHOD_UNKNOWN = "U"
    VISIT_METHOD_CHOICES = [
        (METHOD_RFID, "RFID"),
        (METHOD_FRONT_DESK, "Front Desk"),
        (METHOD_MOBILE_APP, "Mobile App"),
        (METHOD_UNKNOWN, "Unknown"),
    ]
    method = models.CharField(max_length=1, choices=VISIT_METHOD_CHOICES,
        default=METHOD_UNKNOWN, null=False, blank=False,
        help_text="The method used to record the visit, such as 'Front Desk' or 'RFID'.")

    EVT_ARRIVAL = "A"
    EVT_PRESENT = "P"
    EVT_DEPARTURE = "D"
    VISIT_EVENT_CHOICES = [
        (EVT_ARRIVAL, "Arrival"),
        (EVT_PRESENT, "Presence"),
        (EVT_DEPARTURE, "Departure")
    ]
    event_type = models.CharField(max_length=1, choices=VISIT_EVENT_CHOICES, null=False, blank=False,
        help_text="The type of visit event.")

    sync1 = models.BooleanField(default=False,
        help_text="True if this event has been sync'ed to 'other system #1'")

    def __str__(self):
        return "%s, %s, %s" % (self.when.isoformat()[:10], self.who, self.event_type)

    class Meta:
        ordering = ['when']
        unique_together = ('who', 'when')


class WifiMacDetected(models.Model):

    when = models.DateTimeField(null=False, blank=False, default=timezone.now,
        help_text="Date/time when MAC was noticed to be present.")

    mac = models.CharField(max_length=12, null=False, blank=False,
        help_text="A MAC address as 12 hex digits.")

    def __str__(self):
        localwhen = TZ.normalize(self.when)
        return "{} @ {}".format(self.mac, localwhen)

    class Meta:
        verbose_name = "Wifi MAC detected"
        verbose_name_plural = "Wifi MACs detected"


class MemberLogin(models.Model):
    """ Record member, datetime, ip for each login. """

    member = models.ForeignKey(Member,
        null=True, blank=True,  # Might log IPs for unauthenticated users.
        on_delete=models.SET_NULL,  # Keep login even if member is deleted, since IP info could be useful.
        help_text="The member who logged in.")

    when = models.DateTimeField(null=False, blank=False, default=timezone.now,
        help_text="Date/time member logged in.")

    ip = models.GenericIPAddressField(null=False, blank=False,
        help_text="IP address from which member logged in.")

    class Meta:
        verbose_name = "Login"


def next_paidmembership_ctrlid():
    '''Provides an arbitrary default value for the ctrlid field, necessary when check, cash, or gift-card data is being entered manually.'''

    # Can't raise this exception while old migrations exist and blank dbs will be initialized by others.
    #raise NotImplementedError("PaidMembership has been replaced with Membership.")

    return "ERROR"


class GroupMembership(models.Model):

    group_tag = models.ForeignKey(Tag, null=False, blank=False,
        on_delete=models.PROTECT,  # A group membership's tag should be changed before deleting the unwanted tag.
        help_text="The group to which this membership applies, defined by a tag.")

    start_date = models.DateField(null=False, blank=False,
        help_text="The first day on which the membership is valid.")

    end_date = models.DateField(null=False, blank=False,
        help_text="The last day on which the membership is valid.")

    max_members = models.IntegerField(default=None, null=True, blank=True,
        help_text="The maximum number of members to which this group membership can be applied. Blank if no limit.")

    # A membership can be sold. Sale related fields: sale, sale_price

    sale = models.ForeignKey(Sale, null=False, blank=False,
        on_delete=models.CASCADE,  # Line items are parts of the sale so they should be deleted.
        help_text="The sale on which this group membership appears as a line item, if any.")

    sale_price = models.DecimalField(max_digits=6, decimal_places=2, null=False, blank=False,
        help_text="The price at which this item sold.")

    def __str__(self):
        return "{}, {} to {}".format(self.group_tag, self.start_date, self.end_date)

    def matches(self, membership):
        if membership.start_date      != self.start_date: return False
        if membership.end_date        != self.end_date: return False
        if membership.membership_type != membership.MT_GROUP: return False
        return True

    def copy_to(self, membership):
        membership.start_date      = self.start_date
        membership.end_date        = self.end_date
        membership.membership_type = Membership.MT_GROUP
        membership.save()

    def get_or_create_membership_for(self, member):
        """Get or create a membership and ensure that it matches the group membership's parameters."""

        defaults = {
            'start_date':      self.start_date,
            'end_date':        self.end_date,
            'membership_type': Membership.MT_GROUP
        }
        membership, created = Membership.objects.get_or_create(member=member, group=self, defaults=defaults)
        if created or not self.matches(membership): self.copy_to(membership)
        return membership

    def sync_memberships(self):
        # Create or update the membership for each person in the group:
        for member in self.group_tag.members.all():
            # Following ensures that the membership is synched
            self.get_or_create_membership_for(member)
        # Deletion of memberships for people who are no longer in the group will be handled in
            # a signal handler for Tagging deletions.

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError(_("End date must be later than start date."))


class PaidMembershipNudge(models.Model):
    """ Records the fact that we reminded somebody that they should renew their paid membership """

    member = models.ForeignKey(Member, null=False, blank=False,
        on_delete=models.CASCADE,  # If a member is deleted, we don't care that we've nudged him to pay.
        help_text="The member we reminded.")

    when = models.DateField(null=False, blank=False, default=timezone.now,
        help_text="Date on which the member was reminded.")

    class Meta:
        verbose_name = "Renewal reminder"


class MembershipGiftCard(models.Model):

    redemption_code = models.CharField(max_length=20, unique=True, null=False, blank=False,
        help_text="A random string printed on the card, used during card redemption / membership activation.")

    date_created = models.DateField(null=False, blank=False, default=timezone.now,
        help_text="The date on which the gift card was created.")

    price = models.DecimalField(max_digits=6, decimal_places=2, null=False, blank=False,
        help_text="The price to buy this gift card.")

    month_duration = models.IntegerField(null=False, blank=False,
        help_text="The number of months of membership this gift card grants when redeemed.")

    def __str__(self):
        return "{} months for ${}, code: {}".format(self.month_duration, self.price, self.redemption_code)

    class Meta:
        verbose_name = "Gift card"


class MembershipGiftCardRedemption(models.Model):

    redemption_date = models.DateField(null=False, blank=False, default=timezone.now,
        help_text="The date on which the gift card was redeemed.")

    card = models.OneToOneField(MembershipGiftCard, null=False, blank=False,
        on_delete=models.PROTECT,  # It's nonsensical to delete a gift card after it's redeemed.
        help_text="The membership gift card that was redeemed.")

    def __str__(self):
        return "{}, code: {}".format(
            str(self.membership_set.first()),
            self.card.redemption_code
        )

    class Meta:
        verbose_name = "Gift card redemption"


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# MEMBERSHIP
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class Membership(models.Model):

    # A membership can arise from redemption of a gift card.
    redemption = models.ForeignKey(MembershipGiftCardRedemption, null=True, blank=True, default=None,
        on_delete=models.CASCADE,  # If the redemption is deleted, this membership is meaningless.
        help_text="The associated membership gift card redemption, if any. Usually none.")

    # A membership can be part of a group membership
    group = models.ForeignKey(GroupMembership, null=True, blank=True, default=None,
        on_delete=models.CASCADE,  # This membership is part of the group membership, so it should also go.
        help_text="The associated group membership, if any. Usually none.")

    member = models.ForeignKey(Member,
        # There are records of payments which no longer seem to have an associated account.
        # Name used when paying may be different enough to prevent auto-linking.
        # For two reasons listed above, we allow nulls in next line.
        default=None, null=True, blank=True,
        on_delete=models.SET_NULL,  # If the member is deleted, this membership info is still useful for stats.
        help_text="The member to whom this membership applies.")

    # Note: Strictly speaking, memberships have types, and members don't.
    # Note: If there's no membership term covering some period, member has an "unpaid" membership during that time.
    # REVIEW: Should Scholarship collapse into Complimentary?
    MT_REGULAR       = "R"  # E.g. members who pay $50/mo
    MT_WORKTRADE     = "W"  # E.g. members who work 9 hrs/mo and pay reduced $10/mo
    MT_SCHOLARSHIP   = "S"  # The so-called "full scholarship", i.e. $0/mo. These function as paid memberships.
    MT_COMPLIMENTARY = "C"  # E.g. for directors, certain sponsors, etc. These function as paid memberships.
    MT_GROUP         = "G"  # E.g. Bit Buckets, Pima Engineering Club, JobPath
    MT_FAMILY        = "F"  # An add-on family membership associated with a regular or work-trade membership.
    MT_GIFTCARD      = "K"  # A membership that was funded with a gift card, otherwise identical to REGULAR.
    MEMBERSHIP_TYPE_CHOICES = [
        (MT_REGULAR,       "Regular"),
        (MT_WORKTRADE,     "Work-Trade"),
        (MT_SCHOLARSHIP,   "Scholarship"),
        (MT_COMPLIMENTARY, "Complimentary"),
        (MT_GROUP,         "Group"),
        (MT_FAMILY,        "Family"),
        (MT_GIFTCARD,      "Gift Card"),
    ]
    membership_type = models.CharField(max_length=1, choices=MEMBERSHIP_TYPE_CHOICES,
        null=False, blank=False, default=MT_REGULAR,
        help_text="The type of membership.")

    start_date = models.DateField(null=False, blank=False, default=date.today,
        help_text="The first day on which the membership is valid.")

    end_date = models.DateField(null=False, blank=False, default=date.today,
        help_text="The last day on which the membership is valid.")

    # A membership can be sold. Sale related fields: sale, sale_price

    sale = models.ForeignKey(Sale, null=True, blank=True, default=None,
        on_delete=models.CASCADE,  # Line items are parts of the sale so they should be deleted.
        help_text="The sale that includes this line item, if any. E.g. comp memberships don't have a corresponding sale.")

    sale_price = models.DecimalField(max_digits=6, decimal_places=2, null=False, blank=False,
        # In the gift-card redemption context I don't want to confuse admin users by requiring them to provide
        # a sale price of $0. So I'll let this default to zero even though it must be non-zero in other contexts.
        default=Decimal(0.0),
        help_text="The price at which this item sold.")

    # ETL related fields: ctrlid, protected

    ctrlid = models.CharField(max_length=40, null=False, blank=False, unique=True,
        default=next_membership_ctrlid,
        help_text="Payment processor's id for this membership if it was part of an online purchase.")

    protected = models.BooleanField(default=False,
        help_text="Protect against further auto processing by ETL, etc. Prevents overwrites of manually entered data.")

    def link_to_member(self):

        if self.protected: return  # REVIEW: Should 'protected' checks only appear in ETL code?
        if self.member is not None: return
        if self.sale is None: return

        self.sale.link_to_user()
        self.sale.save()

        # If payer's acct was specified in sale, link to it.
        if self.sale.payer_acct is not None:
            self.member = self.sale.payer_acct.member
            return

    def dbcheck(self):
        if self.redemption is not None and self.membership_type != self.MT_GIFTCARD:
            raise ValidationError(_("Memberships that result from gift card redemptions should have type 'Gift Card'"))
        if self.group is not None and self.membership_type != self.MT_GROUP:
            raise ValidationError(_("Memberships that result from group purchases should have type 'Group'"))

    def clean(self):
        zero_sale_price_types = [self.MT_GIFTCARD, self.MT_COMPLIMENTARY, self.MT_GROUP]
        if self.start_date >= self.end_date:
            raise ValidationError(_("End date must be later than start date."))
        if self.membership_type not in zero_sale_price_types and self.sale_price == 0:
            raise ValidationError(_("This membership type requires a sale price greater than zero."))
        if self.membership_type in zero_sale_price_types and self.sale_price != 0:
            raise ValidationError(_("Sale price should be $0 for this membership type."))

    def __str__(self):
        return "%s, %s to %s" % (self.member, self.start_date, self.end_date)


class DiscoveryMethod(models.Model):
    """Different ways that members learn about us. E.g. 'Tucson Meet Yourself', 'Radio', 'TV', 'Website', etc """

    name = models.CharField(max_length=30, unique=True, null=False, blank=False,
        help_text="The name of some means by which people learn about our organization.")

    order = models.IntegerField(default=None, unique=True, null=False, blank=False,
        help_text="These values define the order in which the discovery methods should be presented to users.")


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# Additional Line-Item Models for SaleAdmin in Books app.
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

# NOTE: Making MembershipGiftCard a LineItem results in user needing to create the card info at time of sale.
# Adding this MembershipGiftCardReference class lets the user select an existing MembershipGiftCard instead.

class MembershipGiftCardReference(models.Model):

    # NOTE: Cards have been sold online without any info about which card was sold.
    # That situation will be mapped to a card value of None and should be rectified manually.
    card = models.OneToOneField(MembershipGiftCard, null=True, blank=True,
        on_delete=models.PROTECT,  # It doesn't make sense to delete a gift card if it's sold.
        help_text="The membership gift card being sold.")

    # Membership gift cards can be sold. Sales related fields: sale, sale_price

    sale = models.ForeignKey(Sale, null=True, blank=True,
        on_delete=models.CASCADE,  # Line items are parts of the sale so they should be deleted.
        help_text="The sale that includes the card as a line item.")

    sale_price = models.DecimalField(max_digits=6, decimal_places=2, null=False, blank=False,
        help_text="The price at which this item sold.")

    # ETL related fields: ctrlid, protected

    ctrlid = models.CharField(max_length=40, null=False, blank=False, unique=True,
        default=next_giftcardref_ctrlid,
        help_text="Payment processor's id if this was part of an online purchase.")

    protected = models.BooleanField(default=False,
        help_text="Protect against further auto processing by ETL, etc. Prevents overwrites of manually entered data.")

    def __str__(self):
        return "CARD NOT YET SPECIFIED!" if self.card is None else self.card.redemption_code

    class Meta:
        verbose_name = "Membership gift card"
