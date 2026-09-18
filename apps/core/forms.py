from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.core.models import SkillCategory, User
from apps.employers.models import Employer
from apps.workers.models import Worker

INPUT_CLASSES = (
    "w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white "
    "placeholder-white/30 outline-none transition focus:border-cyan-glow/60 focus:bg-white/[0.07]"
)


class GlassFormMixin:
    def _style_fields(self):
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {INPUT_CLASSES}".strip()


class WorkerSignUpForm(GlassFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    phone_number = forms.CharField(max_length=15)
    skill_category = forms.ModelChoiceField(queryset=SkillCategory.objects.all())
    experience_years = forms.IntegerField(min_value=0, max_value=60)
    daily_wage = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2)
    city = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "phone_number",
            "skill_category", "experience_years", "daily_wage", "city",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.WORKER
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone_number = self.cleaned_data["phone_number"]
        if commit:
            user.save()
            Worker.objects.create(
                user=user,
                skill_category=self.cleaned_data["skill_category"],
                experience_years=self.cleaned_data["experience_years"],
                daily_wage=self.cleaned_data["daily_wage"],
                city=self.cleaned_data["city"],
            )
        return user


class EmployerSignUpForm(GlassFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    phone_number = forms.CharField(max_length=15)
    employer_type = forms.ChoiceField(choices=Employer.EmployerType.choices)
    company_name = forms.CharField(max_length=150, required=False)
    city = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "phone_number",
            "employer_type", "company_name", "city",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.EMPLOYER
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone_number = self.cleaned_data["phone_number"]
        if commit:
            user.save()
            Employer.objects.create(
                user=user,
                employer_type=self.cleaned_data["employer_type"],
                company_name=self.cleaned_data["company_name"],
                city=self.cleaned_data["city"],
            )
        return user
