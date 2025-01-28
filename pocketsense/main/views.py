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
            return Response({"error": "Session expired or email not found."}, status=status.HTTP_400_BAD_REQUEST)

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
           
            return Response({"message": "OTP verified successfully!"}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)


class StudentRegistrationView(APIView):
    def post(self, request):
        # Extract required fields from the request
        username = request.data.get('username')
        email = request.data.get('email')
        college = request.data.get('college', '')
        semester = request.data.get('semester', '')

        # Validate required fields
        if not username or not email:
            raise ValidationError("Username and email are required.")

        # Check if the student already exists
        if Student.objects.filter(username=username).exists():
            raise ValidationError("Username already taken.")

        # Generate a default secure password
        default_password = 'student@1234'

        # Create the student object
        student = Student(
            username=username,
            email=email,
            college=college,
            semester=semester
        )
        
        # Set the default password securely
        student.set_password(default_password)

        student.save()

       
            
        return Response({
            "message": "Student registered successfully!",
            "student_id": student.id
        }, status=status.HTTP_201_CREATED)
    


class CreateGroupView(APIView):
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

