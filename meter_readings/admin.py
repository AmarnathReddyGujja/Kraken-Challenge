from django.contrib import admin
from .models import FlowFile, Meter, RegisterReading

class MeterInline(admin.TabularInline):
    model = Meter
    extra = 0

class RegisterReadingInline(admin.TabularInline):
    model = RegisterReading
    extra = 0

@admin.register(FlowFile)
class FlowFileAdmin(admin.ModelAdmin):
    list_display = ['filename', 'file_type', 'import_date', 'record_count', 'status']
    list_filter = ['file_type', 'import_date', 'status']
    search_fields = ['filename']
    inlines = [MeterInline]

@admin.register(Meter)
class MeterAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'mpan', 'meter_type', 'created_date']
    list_filter = ['meter_type', 'created_date']
    search_fields = ['serial_number', 'mpan']
    inlines = [RegisterReadingInline]

@admin.register(RegisterReading)
class RegisterReadingAdmin(admin.ModelAdmin):
    list_display = ['meter', 'register_id', 'reading_date', 'reading_value', 'flow_file']
    list_filter = ['register_id', 'reading_type', 'reading_date']
    search_fields = [
        'meter__serial_number', 
        'meter__mpan',
        'register_id'
    ]
    date_hierarchy = 'reading_date'
    list_select_related = ('meter', 'flow_file')