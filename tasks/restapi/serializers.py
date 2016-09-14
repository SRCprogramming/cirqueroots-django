
# Standard

# Third Party
from rest_framework import serializers

# Local
import tasks.models as tm
import members.models as mm


class ClaimSerializer(serializers.ModelSerializer):

    claimed_task = serializers.HyperlinkedRelatedField(
        view_name='task:task-detail',
        queryset = tm.Task.objects.all()
    )

    claiming_member = serializers.HyperlinkedRelatedField(
        view_name='memb:member-detail',
        queryset = mm.Member.objects.all()
    )

    work_set = serializers.HyperlinkedRelatedField(
        view_name='task:work-detail',
        read_only=True,
        many=True,
    )

    class Meta:
        model = tm.Claim
        fields = (
            'id',
            'status',
            'claimed_task',
            'claiming_member',
            'claimed_start_time',
            'claimed_duration',
            'date_verified',
            'work_set',
        )


class TaskSerializer(serializers.ModelSerializer):

    # TODO: owner, reviewer, etc, should not be read-only.
    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='memb:member-detail')
    reviewer = serializers.HyperlinkedRelatedField(read_only=True, view_name='memb:member-detail')
    eligible_claimants = serializers.HyperlinkedRelatedField(read_only=True, many=True, view_name='memb:member-detail')
    claimants = serializers.HyperlinkedRelatedField(read_only=True, many=True, view_name='memb:member-detail')
    claim_set = serializers.HyperlinkedRelatedField(read_only=True, many=True, view_name='task:claim-detail')

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
            'eligible_claimants',
            # eligible_tags,
            'reviewer',
            'work_start_time',
            'work_duration',
            'priority',
            'should_nag',
            'creation_date',
            'scheduled_date',
            'deadline',
            'claimants',
            'status',
            'claim_set',
        )


class WorkSerializer(serializers.ModelSerializer):

    claim = serializers.HyperlinkedRelatedField(read_only=True, view_name='task:claim-detail')

    class Meta:
        model = tm.Work
        fields = (
            'id',
            'claim',
            'work_date',
            'work_duration',
        )

