"""
URL configuration for Home4U project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from contents import urls
from accounts import urls
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)
from drf_yasg import openapi
from drf_yasg.views import get_schema_view as swagger_get_scheme_view
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

schema_view = swagger_get_scheme_view(
    openapi.Info(
        title="Home4U Reservation API",
        default_version='1.21.8',
        description="API documentation of Home4U"
    ),
    public=True
)


urlpatterns = [
    # YOUR PATTERNS
   
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('reservation/', include('contents.urls')),
    path('', include('accounts.urls')),
    path('payments/', include('payments.urls')),
    # path('token/', TokenObtainPairView.as_view(), name='token_obtain'),
    # path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # path('api/v1/', 
    #      include([
    #          path('swagger_ui/schema/', schema_view.with_ui('swagger', cache_timeout=0), name="swagger-schema")
    #      ]))
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

        