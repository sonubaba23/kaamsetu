from django import forms

from apps.core.forms import GlassFormMixin
from apps.jobs.models import Job


class JobForm(GlassFormMixin, forms.ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Job
        fields = [
            "title", "skill_category", "description",
            "city", "address",
            "wage_type", "budget_min", "budget_max",
            "workers_required", "start_date",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean(self):
        cleaned_data = super().clean()
        budget_min = cleaned_data.get("budget_min")
        budget_max = cleaned_data.get("budget_max")
        if budget_min is not None and budget_max is not None and budget_min > budget_max:
            raise forms.ValidationError("Minimum budget can't be higher than the maximum budget.")
        return cleaned_data
