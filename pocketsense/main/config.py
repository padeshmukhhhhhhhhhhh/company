
 
from django.core.mail import send_mail
from .models import *
from datetime import date


def send_payment_reminders():
    reminders = Settlement.objects.filter(payment_status="pending",amount__gt=0)

    for reminder in reminders:
        student_email = reminder.user.email
        message = f"Reminder: You have an outstanding balance of ₹{reminder.amount} . Please settle it by {reminder.due_date}."
        send_mail(
            'Payment Reminder',
            message,
            'noreply@collegegroup.com',
            [student_email]
        )

