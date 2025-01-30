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



logger = logging.getLogger(__name__)




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
        logger.info("Received request for student profile details.")

        # Extract student ID from request data
        student_id = request.data.get('student_id')

        if not student_id:
            logger.error("Student ID is missing in the request.")
            return Response({"error": "Student ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if student_id and not isinstance(student_id, int):
            logger.warning("Invalid Student ID format received: %s", student_id)
            return Response({"error": "Student ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("Fetching profile details for student ID: %s", student_id)

        # Fetch the student record
        student = Student.objects.filter(id=student_id).first()

        if not student:
            logger.error("Student with ID %s not found.", student_id)
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        logger.info("Student profile found for ID: %s", student_id)

        # Prepare the response data
        profile_data = {
            "student_id": student.id,
            "username": student.username,
            "email": student.email,
            "upi_id": student.upi_id,
            "college": student.college,
            "semester": student.semester
        }

        logger.info("Successfully retrieved profile data for student ID: %s", student_id)

        return Response({"profile": profile_data}, status=status.HTTP_200_OK)
    

class StudentProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def put(self, request):
        logger.info("Received request for student profile update.")

        # Extract the student ID from the request
        student_id = request.data.get('student_id')
        
        if not student_id:
            logger.error("Missing student_id in the request.")
            return Response({"error": "Please provide student_id."}, status=status.HTTP_404_NOT_FOUND)
        
        if student_id and not isinstance(student_id, int):
            logger.warning("Invalid Student ID: %s", student_id)
            return Response({"error": "Student ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)


        # Fetch the student record
        student = Student.objects.filter(id=student_id).first()
        
        if not student:
            logger.error("Student with ID %s not found.", student_id)
            return Response({"error": "Student id is incorrect."}, status=status.HTTP_404_NOT_FOUND)

        logger.info("Updating profile for student ID: %s", student_id)

        # Extract fields to update
        username = request.data.get('username')
        email = request.data.get('email')
        upi_id = request.data.get('upi_id')
        college = request.data.get('college')
        semester = request.data.get('semester')

        if not username:
            logger.warning("Username is missing from the request.")
            return Response({"error": "Please provide username."}, status=status.HTTP_404_NOT_FOUND)

        if not email:
            logger.warning("Email is missing from the request.")
            return Response({"error": "Please provide email."}, status=status.HTTP_404_NOT_FOUND)

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            logger.warning("Invalid email format: %s", email)
            return Response({"error": "Invalid email format."}, status=status.HTTP_400_BAD_REQUEST)

        # Update username if provided and unique
        if username != student.username:
            if Student.objects.filter(username=username).exclude(id=student_id).exists():
                logger.warning("Username '%s' is already taken by another student.", username)
                return Response({"error": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)
            logger.info("Updating username to '%s' for student ID: %s", username, student_id)
            student.username = username

        student.email = email

        # Update UPI ID if provided and valid
        if upi_id:
            upi_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+$'
            if not re.match(upi_pattern, upi_id):
                logger.warning("Invalid UPI ID format: %s", upi_id)
                return Response({"error": "Invalid UPI ID format. It should be in the format 'name@bankname' or 'mobile@bankname'."},
                                status=status.HTTP_400_BAD_REQUEST)
            logger.info("Updating UPI ID to '%s' for student ID: %s", upi_id, student_id)
            student.upi_id = upi_id

        # Update college if provided
        if college:
            logger.info("Updating college to '%s' for student ID: %s", college, student_id)
            student.college = college

        # Update semester if provided
        if semester:
            logger.info("Updating semester to '%s' for student ID: %s", semester, student_id)
            student.semester = semester

        # Save the updated student record
        student.save()
        logger.info("Profile updated successfully for student ID: %s", student_id)

        return Response({
            "message": "Profile updated successfully!"
        }, status=status.HTTP_200_OK)


class MonthlyAnalysisAPI(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        logger.info("Received request for monthly analysis.")
        
        month_name = request.data.get('month_name', '').capitalize()
        year = request.data.get('year')

        if not month_name:
            logger.error("Month is missing from the request.")
            return Response({"error": "Month is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not year:
            logger.error("Year is missing from the request.")
            return Response({"error": "Year is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.debug("Month: %s, Year: %s", month_name, year)

        # Convert month name to month number
        month = MONTH_NAME_TO_NUMBER.get(month_name)
        if month is None:
            logger.error("Invalid month name provided: %s", month_name)
            return Response({"error": "Invalid month name."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Filter expenses by month and year
            expenses = Expense.objects.filter(date__month=month, date__year=year)
            logger.info("Retrieved %d expense records for month %s, year %s.", expenses.count(), month_name, year)
            
            # Group by category and sum the amounts
            expense_summary = expenses.values('category__name').annotate(total_amount=Sum('amount'))
            logger.debug("Expense summary generated: %s", expense_summary)

            # Get settlement summary (total paid, total pending)
            settlements = Settlement.objects.filter(due_date__month=month, due_date__year=year)
            logger.info("Retrieved %d settlement records for month %s, year %s.", settlements.count(), month_name, year)

            settlement_summary = {
                "total_paid": settlements.filter(payment_status='paid').aggregate(Sum('amount'))['amount__sum'] or 0,
                "total_pending": settlements.filter(payment_status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
            }
            logger.debug("Settlement summary: %s", settlement_summary)

            # Respond with the expense and settlement summaries
            return Response({
                "expense_summary": expense_summary,
                "settlement_summary": settlement_summary,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error occurred during monthly analysis: %s", str(e))
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def generate_otp():
    return str(random.randint(1000, 9999))



class LoginView(APIView):

    def post(self, request):
        logger.info("Received login request to send OTP.")

        email = request.data.get('email', '').strip()
        
        if not email:
            logger.error("Email not provided in the request.")
            return Response({"error": "Please provide email."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Student.objects.get(email=email)
            logger.info("User found for email: %s", email)

            # Generate and set OTP
            otp = generate_otp()
            user.otp = otp
            user.save()
            logger.debug("OTP generated and saved for user: %s", email)

            # Send OTP email
            send_mail(
                'Subject: Your OTP',
                f'Your OTP is: {otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            logger.info("OTP email sent successfully to: %s", email)

            return Response({"message": "OTP sent successfully!"}, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            logger.warning("No user found for the provided email: %s", email)
            return Response({"error": "Please enter a correct email."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Error occurred while processing login request: %s", str(e))
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OTPView(APIView):
   
    def post(self, request):
        logger.info("Received OTP verification request.")

        email = request.data.get("email")
        if not email:
            logger.error("Email not provided in the request.")
            return Response({"error": "Please provide email."}, status=status.HTTP_400_BAD_REQUEST)

        user_entered_otp = request.data.get("otp", "").strip()
        logger.debug("Received OTP: %s for email: %s", user_entered_otp, email)

        if not user_entered_otp:
            logger.error("OTP not provided for email: %s", email)
            return Response({"error": "OTP is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            logger.warning("Invalid email format: %s", email)
            return Response({"error": "Invalid email format."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the email exists in the database
        user_1 = Student.objects.filter(email=email).first()
        if not user_1:
            logger.warning("Email not found: %s", email)
            return Response({"error": "Email is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the OTP
        user = Student.objects.filter(email=email, otp=user_entered_otp).first()
        if user:
            logger.info("OTP verified successfully for email: %s", email)
            user.otp = None
            user.save()

            # Generate access token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
           
            logger.debug("Access token generated for user: %s", email)
            return Response({
                "message": "OTP verified successfully!",
                "access_token": access_token
            }, status=status.HTTP_200_OK)

        logger.warning("Invalid OTP entered for email: %s", email)
        return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)



class StudentRegistrationView(APIView):

    def post(self, request):
        logger.info("Received request to register a new student.")

        # Extract required fields from the request
        username = request.data.get('username')
        email = request.data.get('email')
        upi_id = request.data.get('upi_id')
        college = request.data.get('college')
        semester = request.data.get('semester')

        logger.debug("Request data: username=%s, email=%s, upi_id=%s, college=%s, semester=%s", 
                     username, email, upi_id, college, semester)

        # Validate required fields
        if not username or not email:
            logger.error("Missing required fields: username=%s, email=%s", username, email)
            return Response({"error": "Username and email are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            logger.warning("Invalid email format: %s", email)
            return Response({"error": "Invalid email format."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the student already exists
        if Student.objects.filter(username=username).exists():
            logger.warning("Username already taken: %s", username)
            return Response({"error": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a default secure password
        default_password = 'student@1234'

        # Validate UPI ID format if provided
        if upi_id:
            upi_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+$'
            if not re.match(upi_pattern, upi_id):
                logger.warning("Invalid UPI ID format: %s", upi_id)
                return Response({"error": "Invalid UPI ID format. It should be in the format 'name@bankname' or 'mobile@bankname'."}, status=status.HTTP_400_BAD_REQUEST)

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

        logger.info("Student registered successfully with ID: %s", student.id)

        return Response({
            "message": "Student registered successfully!",
            "student_id": student.id
        }, status=status.HTTP_201_CREATED)

    


class CreateGroupView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        logger.info("Received request to create a new group.")

        group_name = request.data.get("name")
        logger.debug("Group name from request: %s", group_name)

        if not group_name:
            logger.error("Group name is missing in the request.")
            return Response({"error": "Group name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the group
        try:
            group = CollegeGroup.objects.create(name=group_name)
            logger.info("Group created successfully with ID: %s and name: %s", group.id, group_name)
        except Exception as e:
            logger.exception("Error occurred while creating the group: %s", str(e))
            return Response({"error": "Failed to create group."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info("Returning success response for group creation.")
        return Response({
            "message": "Group created successfully.",
            "group_id": group.id
        }, status=status.HTTP_201_CREATED)


    


class AddStudentToGroupView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        logger.info("Received request to add student to group.")

        group_id = request.data.get("group_id")
        student_id = request.data.get("student_id")
        logger.debug("Request data - group_id: %s, student_id: %s", group_id, student_id)

        # Validate inputs
        if not group_id or not student_id:
            logger.error("Missing group ID or student ID in the request.")
            return Response({"error": "Group ID and Student ID are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(group_id, int):
            logger.warning("Invalid group ID type: %s", type(group_id).__name__)
            return Response({"error": "Group ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(student_id, int):
            logger.warning("Invalid student ID type: %s", type(student_id).__name__)
            return Response({"error": "Student ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch group and student objects
        group = CollegeGroup.objects.filter(id=group_id).first()
        if not group:
            logger.warning("Group not found for ID: %s", group_id)
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        student = Student.objects.filter(id=student_id).first()
        if not student:
            logger.warning("Student not found for ID: %s", student_id)
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Add student to the group
        group.members.add(student)
        group.save()
        logger.info("Student %s added to group %s.", student.username, group.name)

        return Response({
            "message": f"Student {student.username} added to group {group.name}."
        }, status=status.HTTP_200_OK)
    


class GetCollegeGroupInfoView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        logger.info("Received request to get college group info.")
        
        # Get group_id from request data
        group_id = request.data.get("group_id")
        logger.debug("Group ID from request: %s", group_id)

        if not group_id:
            logger.error("Group ID not provided.")
            return Response({"error": "Group ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not isinstance(group_id, int):
            logger.warning("Invalid group ID type: %s", type(group_id).__name__)
            return Response({"error": "Group ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the group object
        group = CollegeGroup.objects.filter(id=group_id).first()

        if not group:
            logger.warning("Group not found for ID: %s", group_id)
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all members (students) of the group
        members = group.members.all()
        logger.info("Fetched %d members for group ID: %s", len(members), group_id)

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
        logger.debug("Member data prepared: %s", member_data)

        # Construct the response data
        group_data = {
            "id": group.id,
            "name": group.name,
            "members": member_data
        }

        logger.info("Successfully fetched group data for group ID: %s", group_id)
        return Response(group_data, status=status.HTTP_200_OK)


class RemoveStudentFromCollegeGroupView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        group_id = request.data.get("group_id")
        student_id = request.data.get("student_id")

        # Log the incoming request data
        logger.info("Received request to remove student with ID: %s from group with ID: %s", student_id, group_id)

        # Validate inputs
        if not group_id or not student_id:
            logger.warning("Missing required fields: group_id or student_id")
            raise ValidationError({"error": "Group ID and Student ID are required."})

        if not isinstance(student_id, int):
            logger.warning("Invalid student ID type: %s", student_id)
            return Response({"error": "Student ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(group_id, int):
            logger.warning("Invalid group ID type: %s", group_id)
            return Response({"error": "Group ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch group and student objects
        group = CollegeGroup.objects.filter(id=group_id).first()
        if not group:
            logger.error("Group with ID %d not found.", group_id)
            raise ValidationError({"error": "Group not found."})

        student = Student.objects.filter(id=student_id).first()
        if not student:
            logger.error("Student with ID %d not found.", student_id)
            raise ValidationError({"error": "Student not found."})

        # Check if the student is in the group
        if student not in group.members.all():
            logger.warning("Student %s is not a member of group %s", student.username, group.name)
            raise ValidationError({"error": "Student is not a member of this group."})

        # Remove student from the group
        group.members.remove(student)
        group.save()

        logger.info("Student %s removed from group %s.", student.username, group.name)

        return Response({
            "message": f"Student {student.username} removed from group {group.name}."
        }, status=status.HTTP_200_OK)




class CreateCategoryView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        category_name = request.data.get("name")
        
        # Log the request
        logger.info("Received request to create category with name: %s", category_name)

        if not category_name:
            logger.warning("Category name is missing in the request.")
            raise ValidationError({"error": "Category name is required."})

        # Create the category
        try:
            category = Category.objects.create(name=category_name)
            logger.info("Category created successfully with ID: %d", category.id)
        except Exception as e:
            logger.error("Error occurred while creating category: %s", str(e))
            raise ValidationError({"error": "An error occurred while creating the category."})

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
            amount = data.get('amount')
            category_id = data.get('category_id')
            split_type = data.get('split_type', 'equal')
            date = parse_date(data.get('date'))
            user_id = data.get('user_id')
            group_id = data.get('group_id')
            receipt_image = request.FILES.get('receipt_image')

            # Validate required fields
            if not all([amount, date, user_id, group_id]):
                logger.warning("Missing required fields in request: %s", data)
                return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

            # Validate that amount, user_id, group_id, and category_id are integers
            if not isinstance(amount, (int, float)):
                logger.warning("Invalid amount value: %s", amount)
                return Response({"error": "Amount must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)

            if not isinstance(user_id, int):
                logger.warning("Invalid user ID: %s", user_id)
                return Response({"error": "User ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

            if not isinstance(group_id, int):
                logger.warning("Invalid group ID: %s", group_id)
                return Response({"error": "Group ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

            if category_id and not isinstance(category_id, int):
                logger.warning("Invalid category ID: %s", category_id)
                return Response({"error": "Category ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch user, category, and group
            try:
                user = Student.objects.get(id=user_id)
            except Student.DoesNotExist:
                logger.error("Student not found: %d", user_id)
                return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

            category = Category.objects.get(id=category_id) if category_id else None
            try:
                group = CollegeGroup.objects.get(id=group_id)
            except CollegeGroup.DoesNotExist:
                logger.error("Group not found: %d", group_id)
                return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

            group_members = group.members.all()  # Assuming Group has ManyToManyField to Student

            expense = Expense.objects.create(
                amount=Decimal(amount),
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
                    logger.warning("Group does not have members: %d", group_id)
                    return Response({"error": "Group does not have members."})

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

                logger.info("Successfully created expense and settlements for group: %d", group_id)
            else:
                logger.warning("Unsupported split type: %s", split_type)
                return Response({"error": "Only 'equal' split type is supported."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Expense recorded and settlements created successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error("An error occurred: %s", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class SettlementListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

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
