from django.db import models
from django.conf import settings

class Notification(models.Model):
    class Type(models.TextChoices):
        ORDER = 'ORDER', 'Order Update'
        PAYMENT = 'PAYMENT', 'Payment Update'
        SYSTEM = 'SYSTEM', 'System Alert'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.user.email} - Read: {self.is_read}"
