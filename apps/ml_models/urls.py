from django.urls import path

from apps.ml_models import views

app_name = "ml_models"

urlpatterns = [
    path("trust-score/recompute/", views.RecomputeTrustScoreView.as_view(), name="recompute-trust-score"),
]
