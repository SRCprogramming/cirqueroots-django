from members.models import Member, Pushover
import os
import pushover
import logging

logger = logging.getLogger("members")

pushover_available = False

api_token = os.getenv('PUSHOVER_API_KEY', None)

if api_token is None:
    logger.info("Pushover not configured. Alerts will not be sent.")
else:
    try:
        pushover.init(api_token)
        pushover_available = True
    except Exception as e:
        logger.info("Pushover could not be initialized. Alerts will not be sent.")
        logger.info("Pushover init exception: "+str(e))


# REVIEW: This sometimes fails. Should it be an asynchronous task with retries?
def notify(target_member: Member, title: str, message: str):
    if not pushover_available:
        return

    try:
        target_key = Pushover.objects.get(who=target_member).key
    except Pushover.DoesNotExist:
        logger.error("Couldn't send msg to %s since there's no pushover key for them.", str(target_member))
        return

    try:
        client = pushover.Client(target_key)
        client.send_message(message, title=title)
    except Exception as e:
        logger.error("Couldn't send msg to %s because %s", str(target_member), str(e))
