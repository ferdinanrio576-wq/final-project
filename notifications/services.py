from .models import Notification
from .tasks import send_email_notification_task
from django.db.models import QuerySet

class NotificationService:
    @staticmethod
    def create_notification(user, title: str, message: str, notif_type: str = 'SYSTEM') -> Notification:
        # Create In-App Notification
        notif = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notif_type
        )

        # Trigger Celery background task for email notification
        send_email_notification_task.delay(
            recipient_email=user.email,
            subject=title,
            message=message
        )

        return notif

    @staticmethod
    def list_user_notifications(user) -> QuerySet:
        return Notification.objects.filter(user=user).order_by('-created_at')

    @staticmethod
    def mark_as_read(notif_id: int, user) -> bool:
        try:
            notif = Notification.objects.get(id=notif_id, user=user)
            notif.is_read = True
            notif.save()
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user):
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)

    @staticmethod
    def get_unread_count(user) -> int:
        if user.is_authenticated:
            return Notification.objects.filter(user=user, is_read=False).count()
        return 0
