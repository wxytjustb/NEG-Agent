from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.html import format_html
from django.db import models


@staff_member_required
def knowledge_dashboard(request):
    """知识库管理仪表盘"""
    return render(request, 'admin/knowledge/dashboard.html')


class KnowledgeManagementAdmin(admin.ModelAdmin):
    """知识库管理"""
    
    change_list_template = 'admin/knowledge/knowledgemanagement/change_list.html'
    
    def has_module_permission(self, request):
        return request.user.is_staff
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        # 返回空查询集，避免数据库查询
        return self.model.objects.none()


# 创建虚拟模型
class KnowledgeManagement(models.Model):
    class Meta:
        verbose_name = '知识库管理'
        verbose_name_plural = '知识库仪表盘'
        app_label = 'knowledge'
        managed = False  # 不创建实际的数据库表
        db_table = ''


# 注册
admin.site.register(KnowledgeManagement, KnowledgeManagementAdmin)
