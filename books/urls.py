from django.conf.urls import url, include
from . import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'sales', views.SaleViewSet)
router.register(r'sale-notes', views.SaleNoteViewSet)
router.register(r'monetary-donations', views.MonetaryDonationViewSet)
router.register(r'other-items', views.OtherItemViewSet)
router.register(r'other-item-types', views.OtherItemTypeViewSet)

urlpatterns = [

    # DJANGO REST FRAMEWORK API
    url(r'^', include(router.urls)),
]
