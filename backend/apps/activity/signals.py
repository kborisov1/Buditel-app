from typing import Any

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.db.models.signals import post_save
from django.dispatch import receiver

from .log import log_event

ACTIONS = {ADDITION: "admin_add", CHANGE: "admin_change", DELETION: "admin_delete"}


@receiver(post_save, sender=LogEntry)
def mirror_admin_change(sender: Any, instance: LogEntry, created: bool, **kwargs: Any) -> None:
    """Every admin add, change and delete becomes a content event (architecture 10)."""
    if not created:
        return
    content_type = instance.content_type
    log_event(
        "content",
        ACTIONS.get(instance.action_flag, "admin_action"),
        instance.user,
        model=f"{content_type.app_label}.{content_type.model}" if content_type else None,
        object_id=instance.object_id,
        object=instance.object_repr,
        message=instance.get_change_message(),
    )
