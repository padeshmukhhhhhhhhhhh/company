from django.db import models

from django.contrib.auth.models import AbstractUser


class Student(AbstractUser):
    college = models.CharField(max_length=255, blank=True, null=True)
    semester = models.CharField(max_length=50, blank=True, null=True)
    default_payment_methods = models.CharField(max_length=100, blank=True, null=True)
    otp=models.IntegerField(blank=True,null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='student_users',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='student_users_permissions',
        blank=True,
    )

# Category Model
class Category(models.Model):
    name =  models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name


# Expense Model
class Expense(models.Model):
 
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE,blank=True, null=True)
    split_type = models.CharField(max_length=50, default='equal')
    date = models.DateField()
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    user = models.ForeignKey(Student, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.category}"



payment_status = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
       
    ]

# Settlement Model
class Settlement(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=50,choices=payment_status,default='pending')
    settlement_method = models.CharField(max_length=50,blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    user = models.ForeignKey(Student, on_delete=models.CASCADE,blank=True,null=True)


    def __str__(self):
        return f"{self.amount}"
    


# Group Model
class CollegeGroup(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, default='general')  # hostel, project, trip, etc.
    members = models.ManyToManyField(Student, related_name='CollegeGroup')

    def __str__(self):
        return self.name




