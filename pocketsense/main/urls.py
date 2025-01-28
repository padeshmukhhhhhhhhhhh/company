from django.urls import path
from .views import *

urlpatterns = [
    path('register', StudentRegistrationView.as_view(), name='student_register'),
    path('login', LoginView.as_view(), name='login'),
    path('otp', OTPView.as_view(), name='otp'),
    path('group-info', GetCollegeGroupInfoView.as_view(), name='get_college_group_info'),
    path('create-group', CreateGroupView.as_view(), name='create_group'),
    path('create-category', CreateCategoryView.as_view(), name='create_category'),
    path('remove-student-from-group', RemoveStudentFromCollegeGroupView.as_view(), name='remove_student_from_group'),
    path('add-student-to-group', AddStudentToGroupView.as_view(), name='add_student_to_group'),
    path('expenses-create', ExpenseEntryAPIView.as_view(), name='expense-entry'),
    path('setlment-tracking', SettlementListView.as_view(), name='setlment-tracking'),
    path('monthly-analysis', MonthlyAnalysisAPI.as_view(), name='monthly-analysis')
]
