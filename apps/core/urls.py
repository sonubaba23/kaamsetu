from django.contrib.auth.views import LogoutView
from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("login/", views.KaamSetuLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.RegisterChoiceView.as_view(), name="register_choice"),
    path("register/worker/", views.WorkerSignUpView.as_view(), name="register_worker"),
    path("register/employer/", views.EmployerSignUpView.as_view(), name="register_employer"),
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
]
