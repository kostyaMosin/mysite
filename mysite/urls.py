from django.contrib import admin
from django.urls import path, re_path, include
from django.contrib.sitemaps.views import sitemap
from blog.sitemaps import PostSitemap

sitemaps = {
    'posts': PostSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'blog/', include('blog.urls')),
    re_path(r'^sitemap\.xml$', sitemap,
            {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]
