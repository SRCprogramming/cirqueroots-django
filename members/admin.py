from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from members.models import Member, Tag

# TODO: TagAdmin with inline Members?

class MemberInline(admin.StackedInline):
    model = Member
    can_delete = False
    verbose_name_plural = 'membership'
    filter_horizontal = ['tags']

    """ TODO: Modify CSS to work in this new inline context:
    class Media:
        css = {
            "all": ("members/member_admin.css",)
        }
    """

class UserAdmin(UserAdmin):

    inlines = (MemberInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

#REVIEW: Can Members be inlined into TagAdmin in a way that's palatable?
class MemberInlineForTag(admin.TabularInline):
    model = Member.tags.through
    extra = 0

class TagAdmin(admin.ModelAdmin):
    fields = ['name','meaning']
    inlines = [MemberInlineForTag]

admin.site.register(Tag)
