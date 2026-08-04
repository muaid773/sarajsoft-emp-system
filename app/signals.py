from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Application, ApplicationHistory

@receiver(pre_save, sender=Application)
def track_status_change(sender, instance, **kwargs):
    if not instance.pk:
        return  # سجل جديد، لا يوجد قديم

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if old.status != instance.status:
        ApplicationHistory.objects.create(
            application=instance,
            old_status=old.status,
            new_status=instance.status,
        )