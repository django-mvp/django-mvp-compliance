"""The addresses a host project mounts to serve its documents as pages.

Mount them with ``path("legal/", include("mvp_compliance.urls"))`` and link
with ``{% url 'mvp_compliance:document' 'privacy-policy' %}``.
"""

from django.urls import path

from mvp_compliance.views import DocumentView

app_name = "mvp_compliance"

urlpatterns = [
    path("<slug:slug>/", DocumentView.as_view(), name="document"),
]
