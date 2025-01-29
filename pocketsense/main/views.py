from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
from rest_framework.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.conf import settings
import random
from django.contrib.auth.models import User
from django.utils.dateparse import parse_date
from decimal import Decimal
from datetime import timedelta
from .models import *
from django.db.models import Sum
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
import re
import pytesseract
from PIL import Image
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging


logger = logging.getLogger('file')




MONTH_NAME_TO_NUMBER = {
    'January': 1,
    'February': 2,
    'March': 3,
    'April': 4,
    'May': 5,
    'June': 6,
    'July': 7,
    'August': 8,
    'September': 9,
    'October': 10,
    'November': 11,
    'December': 12
}




def extract_text_from_image(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    print(text)
    return text




class StudentProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        # Extract student ID from request data
        student_id = request.data.get('student_id')

        if not student_id:
            return Response({"error": "Student ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the student record
        student = Student.objects.filter(id=student_id).first()

        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Prepare the response data
        profile_data = {
            "student_id": student.id,
            "username": student.username,
            "email": student.email,
            "upi_id": student.upi_id,
            "college": student.college,
            "semester": student.semester
        }

        return Response({"profile": profile_data}, status=status.HTTP_200_OK)


class StudentProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def put(self, request):
        # Extract the student ID from the request
        student_id = request.data.get('student_id')

        if not student_id:
            return Response({"error": "Please provide student_id."}, status=status.HTTP_404_NOT_FOUND)

        
        # Fetch the student record
        student = Student.objects.filter(id=student_id).first()
        
        if not student:
            return Response({"error": "Student id is incorrect."}, status=status.HTTP_404_NOT_FOUND)

        # Extract fields to update
        username = request.data.get('username')
        email = request.data.get('email')
        upi_id = request.data.get('upi_id')
        college = request.data.get('college')
        semester = request.data.get('semester')

        if not username:
            return Response({"error": "Please provide username."}, status=status.HTTP_404_NOT_FOUND)


        if not email:
            return Response({"error": "Please provide email."}, status=status.HTTP_404_NOT_FOUND)



        # Update username if provided and unique
        if username != student.username:
            if Student.objects.filter(username=username).exclude(id=student_id).exists():
                return Response({"error": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)
            student.username = username

        
        student.email = email

        # Update UPI ID if provided and valid
        if upi_id:
            upi_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+$'
            if not re.match(upi_pattern, upi_id):
                return Response({"error": "Invalid UPI ID format. It should be in the format 'name@bankname' or 'mobile@bankname'."},
                                status=status.HTTP_400_BAD_REQUEST)
            student.upi_id = upi_id

        # Update college if provided
        if college:
            student.college = college

        # Update semester if provided
        if semester:
            student.semester = semester

        # Save the updated student record
        student.save()

        return Response({
            "message": "Profile updated successfully!"
           
        }, status=status.HTTP_200_OK)


class MonthlyAnalysisAPI(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

   
    def post(self, request):
        
        month_name = request.data.get('month_name', '').capitalize()
        year = request.data.get('year')

        if not month_name:
            return Response({"error": "Month is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not year:
            return Response({"error": "year is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        

        # Convert month name to month number
        month = MONTH_NAME_TO_NUMBER.get(month_name) 


        # Filter expenses by month and year
        expenses = Expense.objects.filter(date__month=month, date__year=year)
        
        # Group by category and sum the amounts
        expense_summary = expenses.values('category__name').annotate(total_amount=Sum('amount'))
        
        # Get settlement summary (total paid, total pending, total overdue)
        settlements = Settlement.objects.filter(due_date__month=month, due_date__year=year)
        settlement_summary = {
            "total_paid": settlements.filter(payment_status='paid').aggregate(Sum('amount'))['amount__sum'],
            "total_pending": settlements.filter(payment_status='pending').aggregate(Sum('amount'))['amount__sum']
          
        }

        # Respond with the expense and settlement summaries
        return Response({
            "expense_summary": expense_summary,
            "settlement_summary": settlement_summary,
        }, status=status.HTTP_200_OK)



def generate_otp():
    return str(random.randint(1000, 9999))


class LoginView(APIView):

   
    def post(self, request):
        email = request.data.get('email', '').strip()
        
        if not email:
            raise ValidationError("Email is required.")

        try:
            user = Student.objects.get(email=email)
            
            
            otp = generate_otp()
            user.otp = otp
            user.save()

            # Send OTP email
            send_mail(
                'Subject: Your OTP',
                f'Your OTP is: {otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            
          
            return Response({"message": "OTP sent successfully!"}, status=status.HTTP_200_OK)
        
        except Student.DoesNotExist:
            return Response({"error": "Please enter a correct email."}, status=status.HTTP_400_BAD_REQUEST)


class OTPView(APIView):
   
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Please provide email."}, status=status.HTTP_400_BAD_REQUEST)

        user_entered_otp = request.data.get("otp", "").strip()

        if not user_entered_otp:
            return Response({"error": "OTP is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        user_1 =Student.objects.filter(email=email).first()

        if not user_1:
            return Response({"error": "Email is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        

        user = Student.objects.filter(email=email, otp=user_entered_otp).first()

        if user:
            user.otp=None
            user.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
           
            return Response({"message": "OTP verified successfully!","access_token":access_token}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)


class StudentRegistrationView(APIView):
    
    def post(self, request):
        # Extract required fields from the request
        username = request.data.get('username')
        email = request.data.get('email')
        upi_id = request.data.get('upi_id')
        college = request.data.get('college')
        semester = request.data.get('semester')

        # Validate required fields
        if not username or not email:
            raise ValidationError("Username and email are required.")

        # Check if the student already exists
        if Student.objects.filter(username=username).exists():
            raise ValidationError("Username already taken.")

        # Generate a default secure password
        default_password = 'student@1234'

        if upi_id:
            upi_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+$'
            if not re.match(upi_pattern, upi_id):
                raise ValidationError("Invalid UPI ID format. It should be in the format 'name@bankname' or 'mobile@bankname'.")



        # Create the student object
        student = Student(
            username=username,
            email=email,
            college=college,
            semester=semester,
            upi_id=upi_id
        )
        
        
        
        # Set the default password securely
        student.set_password(default_password)

        student.save()

       
            
        return Response({
            "message": "Student registered successfully!",
            "student_id": student.id
        }, status=status.HTTP_201_CREATED)
    


class CreateGroupView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

   
    def post(self, request):
        group_name = request.data.get("name")
       

        if not group_name:
            raise ValidationError({"error": "Group name is required."})

        # Create the group
        group = CollegeGroup.objects.create(name=group_name)
        return Response({
            "message": "Group created successfully.",
            "group_id": group.id
        }, status=status.HTTP_201_CREATED)


class AddStudentToGroupView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

   
    def post(self, request):
        group_id = request.data.get("group_id")
        student_id = request.data.get("student_id")

        # Validate inputs
        if not group_id or not student_id:
            raise ValidationError({"error": "Group ID and Student ID are required."})

        # Fetch group and student objects
        group = CollegeGroup.objects.filter(id=group_id).first()

        if not group:
            raise ValidationError({"error": "Group not found."})
        
        student = Student.objects.filter(id=student_id).first()

        if not student:
            raise ValidationError({"error": "Student not found."})

       
        # Add student to the group
        group.members.add(student)
        group.save()

        return Response({
            "message": f"Student {student.username} added to group {group.name}."
        }, status=status.HTTP_200_OK)




class GetCollegeGroupInfoView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    
    def post(self, request):
        # Get group_id from request data
        group_id = request.data.get("group_id")

        if not group_id:
            return Response({"error": "Group ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the group object
        group = CollegeGroup.objects.filter(id=group_id).first()

        if not group:
            raise NotFound({"error": "Group not found."})

        # Get all members (students) of the group
        members = group.members.all()

        # Create a list of member details
        member_data = [
            {
                "id": student.id,
                "username": student.username,
                "college": student.college,
                "semester": student.semester
            }
            for student in members
        ]

        # Construct the response data
        group_data = {
            "id": group.id,
            "name": group.name,
            "members": member_data
        }

        return Response(group_data, status=status.HTTP_200_OK)
    



class RemoveStudentFromCollegeGroupView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


   
    def post(self, request):
        group_id = request.data.get("group_id")
        student_id = request.data.get("student_id")

        # Validate inputs
        if not group_id or not student_id:
            raise ValidationError({"error": "Group ID and Student ID are required."})

        # Fetch group and student objects
        group = CollegeGroup.objects.filter(id=group_id).first()

        if not group:
            raise ValidationError({"error": "Group not found."})

        student = Student.objects.filter(id=student_id).first()

        if not student:
            raise ValidationError({"error": "Student not found."})

        # Check if the student is in the group
        if student not in group.members.all():
            raise ValidationError({"error": "Student is not a member of this group."})

        # Remove student from the group
        group.members.remove(student)
        group.save()

        return Response({
            "message": f"Student {student.username} removed from group {group.name}."
        }, status=status.HTTP_200_OK)



class CreateCategoryView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


   
    def post(self, request):
        category_name = request.data.get("name")
       

        if not category_name:
            raise ValidationError({"error": "Category name is required."})

        # Create the group
        category = Category.objects.create(name=category_name)
        return Response({
            "message": "Category created successfully.",
            "category_id": category.id
        }, status=status.HTTP_201_CREATED)
    

class ExpenseEntryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    
    def post(self, request):
        try:
            # Extract data from request
            data = request.data
            amount = Decimal(data.get('amount'))
            category_id = data.get('category')
            split_type = data.get('split_type', 'equal')
            date = parse_date(data.get('date'))
            user_id = data.get('user')
            group_id = data.get('group')
            receipt_image = request.FILES.get('receipt_image')

            # Validate required fields
            if not all([amount, date, user_id, group_id]):
                return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch user, category, and group
            user = Student.objects.get(id=user_id)
            category = Category.objects.get(id=category_id) if category_id else None
            group = CollegeGroup.objects.get(id=group_id)
            group_members = group.members.all()  # Assuming Group has ManyToManyField to Student

           
            expense = Expense.objects.create(
                amount=amount,
                category=category,
                split_type=split_type,
                date=date,
                receipt_image=receipt_image,
                user=user
            )

            expense_creation_date = date  # Use the date from user input
            due_date = expense_creation_date + timedelta(days=30)  # You can adjust the number of days based on your business logic

            # Handle equal split
            if split_type == 'equal':
                if len(group_members) > 0:
                    equal_share = amount / Decimal(len(group_members))
                else:
                    return Response({"error":"Group not have members"})

                settlements = []
                for member in group_members:
                    settlement = Settlement(
                        expense=expense,
                        amount=equal_share,
                        payment_status='pending',
                        settlement_method=None,
                        due_date=due_date,
                        user=member
                    )
                    settlements.append(settlement)

                # Bulk create settlement entries
                Settlement.objects.bulk_create(settlements)
            else:
                return Response({"error": "Only 'equal' split type is supported."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Expense recorded and settlements created successfully."}, status=status.HTTP_201_CREATED)

        except Student.DoesNotExist:
            return Response({"error": "Invalid user ID."}, status=status.HTTP_404_NOT_FOUND)
        except CollegeGroup.DoesNotExist:
            return Response({"error": "Invalid group ID."}, status=status.HTTP_404_NOT_FOUND)
        except Category.DoesNotExist:
            return Response({"error": "Invalid category ID."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class SettlementListView(APIView):
    # permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]

    def get(self, request):
        logger.info("Received request to fetch all settlement records.")

        try:
            # Fetch all settlement records
            settlements = Settlement.objects.all()
            data = []

            logger.info(f"Number of settlements fetched: {settlements.count()}")

            for settlement in settlements:
                data.append({
                    "expense_id": settlement.expense.id if settlement.expense else None,
                    "amount": str(settlement.amount),
                    "payment_status": settlement.payment_status,
                    "settlement_method": settlement.settlement_method,
                    "due_date": settlement.due_date.strftime("%Y-%m-%d") if settlement.due_date else None,
                    "user": settlement.user.username if settlement.user else None
                })

            return Response(data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error while fetching settlement records: {str(e)}")
            return Response({"detail": "Error fetching settlements."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
