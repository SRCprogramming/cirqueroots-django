import tasks.models as tm
from rest_framework import serializers


class TaskSerializer(serializers.ModelSerializer):

    # TODO: owner, reviewer, etc, should not be read-only.
    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='memb:member-detail')
    reviewer = serializers.HyperlinkedRelatedField(read_only=True, view_name='memb:member-detail')

    class Meta:
        model = tm.Task
        fields = (
            'id',
            'owner',
            'instructions',
            'short_desc',
            'scheduled_date',
            'max_workers',
            'max_work',
            # eligible_claimants,
            # eligible_tags,
            'reviewer',
            'work_start_time',
            'work_duration',
            # uninterested,
            'priority',
            'should_nag',
            'creation_date',
            'scheduled_date',
            'deadline',
            # claimants,
            'status'
        )

