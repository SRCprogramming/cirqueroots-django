
# Standard

# Third Party
from django.contrib import admin
from django.utils.html import format_html
from reversion.admin import VersionAdmin

# Local
from inventory.models import PermitScan, PermitRenewal, ParkingPermit, Location, \
    Shop, Tool, ToolIssue, ToolIssueNote


class PermitRenewalInline(admin.TabularInline):
    model = PermitRenewal
    extra = 0


class PermitScanInline(admin.TabularInline):
    model = PermitScan
    extra = 0


@admin.register(ParkingPermit)
class ParkingPermitAdmin(VersionAdmin):
    list_display = ['short_desc', 'owner', 'created', 'ok_to_move', 'is_in_inventoried_space']
    fields = ['short_desc', 'owner', 'created', 'ok_to_move', 'is_in_inventoried_space']
    readonly_fields = ['created']
    inlines = [PermitRenewalInline, PermitScanInline]
    raw_id_fields = ['owner']


@admin.register(PermitScan)
class PermitScanAdmin(VersionAdmin):
    list_display = ['pk', 'when', 'permit', 'where']


@admin.register(Location)
class LocationAdmin(VersionAdmin):
    pass


@admin.register(PermitRenewal)
class PermitRenewalAdmin(VersionAdmin):
    pass


class ToolInline(admin.TabularInline):

    def more_info(self, obj):
        # TODO: Use reverse as in the answer at http://stackoverflow.com/questions/2857001
        url_str = "/admin/inventory/tool/{}".format(obj.id)
        return format_html("<a href='{}'>Tool Details</a>", url_str)

    model = Tool
    extra = 0
    readonly_fields = ['more_info']


@admin.register(Shop)
class ShopAdmin(VersionAdmin):
    list_display = ['pk', 'name', 'manager', 'backup_manager']
    list_display_links = ['pk', 'name']
    raw_id_fields = ['manager', 'backup_manager']
    inlines = [ToolInline]


class ToolIssueInline(admin.TabularInline):
    model = ToolIssue
    extra = 0

    def more_info(self, obj):
        # TODO: Use reverse as in the answer at http://stackoverflow.com/questions/2857001
        url_str = "/admin/inventory/toolissue/{}".format(obj.id)
        return format_html("<a href='{}'>Issue Details</a>", url_str)

    readonly_fields = ['more_info']
    raw_id_fields = ['reporter']


@admin.register(Tool)
class ToolAdmin(VersionAdmin):

    def manager(self, obj):
        return obj.shop.manager

    def backup_mgr(self, obj):
        return obj.shop.backup_manager

    list_display = ['pk', 'name', 'shop', 'manager', 'backup_mgr', 'location']

    list_display_links = ['pk', 'name']

    inlines = [ToolIssueInline]


class ToolIssueNoteInline(admin.StackedInline):
    model = ToolIssueNote
    extra = 0
    raw_id_fields = ['author']
    fields = [
        ('author', 'when_written'),
        'content'
    ]
    readonly_fields = ['when_written']


@admin.register(ToolIssue)
class ToolIssueAdmin(VersionAdmin):
    inlines = [ToolIssueNoteInline]
    raw_id_fields = ['reporter']
