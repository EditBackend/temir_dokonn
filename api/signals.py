from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Sale, WarehouseIncome, ActivityLog # O'zingizdagi log modeli nomi

@receiver(post_save, sender=Sale)
def log_sale_creation(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            employee=instance.employee if hasattr(instance, 'employee') else None,
            action=f"Yangi sotuv amalga oshirildi. Chek #{instance.check_number if hasattr(instance, 'check_number') else instance.id}. Summa: {instance.total_price} so'm"
        )

@receiver(post_delete, sender=Sale)
def log_sale_deletion(sender, instance, **kwargs):
    ActivityLog.objects.create(
        action=f"DIQQAT: Sotuv o'chirildi! Chek #{instance.check_number if hasattr(instance, 'check_number') else instance.id}. Summa: {instance.total_price} so'm kassa/qarzdorlikdan kamaytirildi."
    )