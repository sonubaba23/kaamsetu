from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from apps.core.forms import EmployerSignUpForm, WorkerSignUpForm
from apps.core.models import SkillCategory
from apps.jobs.models import Job
from apps.workers.models import Worker


class LandingView(TemplateView):
    template_name = "core/landing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["skill_categories"] = SkillCategory.objects.all()
        ctx["top_workers"] = (
            Worker.objects.filter(is_live=True).select_related("user", "skill_category")[:6]
        )
        ctx["stats"] = {
            "workers": Worker.objects.filter(is_live=True).count(),
            "jobs_completed": Job.objects.filter(status=Job.Status.COMPLETED).count(),
            "cities": Worker.objects.values("city").distinct().count(),
        }
        return ctx


class KaamSetuLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True


class WorkerSignUpView(CreateView):
    form_class = WorkerSignUpForm
    template_name = "core/register_worker.html"
    success_url = reverse_lazy("core:dashboard_redirect")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class EmployerSignUpView(CreateView):
    form_class = EmployerSignUpForm
    template_name = "core/register_employer.html"
    success_url = reverse_lazy("core:dashboard_redirect")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class RegisterChoiceView(TemplateView):
    template_name = "core/register_choice.html"


@login_required
def dashboard_redirect(request):
    if request.user.role == request.user.Role.WORKER:
        return redirect("workers:dashboard")
    if request.user.role == request.user.Role.EMPLOYER:
        return redirect("employers:dashboard")
    return redirect("admin:index")
