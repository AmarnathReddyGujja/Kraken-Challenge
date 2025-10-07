from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import FlowFile, Meter, RegisterReading
from .forms import FlowFileUploadForm
from .universal_parser import UniversalParser
import tempfile
import os

def home(request):
    """Home page with upload form and recent files"""
    if request.method == 'POST':
        form = FlowFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            
            # Save uploaded file to temporary location with original extension
            original_ext = os.path.splitext(uploaded_file.name)[1] or '.txt'
            with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            try:
                # Parse and import the file
                parser = UniversalParser()
                result = parser.parse_file(tmp_path, original_filename=uploaded_file.name)
                
                # Handle both single return and tuple return for backward compatibility
                if isinstance(result, tuple):
                    flow_file, stats = result
                    messages.success(
                        request, 
                        f'Successfully imported {uploaded_file.name}. '
                        f'Processed {flow_file.record_count} records. '
                        f'New meters: {stats["meters_created"]}, '
                        f'new readings: {stats["readings_created"]}, '
                        f'duplicates skipped: {stats["duplicates_skipped"]}'
                    )
                else:
                    flow_file = result
                    messages.success(
                        request, 
                        f'Successfully imported {uploaded_file.name}. '
                        f'Processed {flow_file.record_count} records.'
                    )
                
                return redirect('file_detail', pk=flow_file.pk)
                
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
    else:
        form = FlowFileUploadForm()
    
    recent_files = FlowFile.objects.all().order_by('-import_date')[:5]
    stats = {
        'total_files': FlowFile.objects.count(),
        'total_meters': Meter.objects.count(),
        'total_readings': RegisterReading.objects.count(),
    }
    
    return render(request, 'meter_readings/home.html', {
        'form': form,
        'recent_files': recent_files,
        'stats': stats
    })

class FlowFileListView(ListView):
    model = FlowFile
    template_name = 'meter_readings/flowfile_list.html'
    context_object_name = 'files'
    paginate_by = 10
    ordering = ['-import_date']

class FlowFileDetailView(DetailView):
    model = FlowFile
    template_name = 'meter_readings/flowfile_detail.html'
    context_object_name = 'flow_file'
    
    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        return get_object_or_404(FlowFile, pk=pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meters'] = Meter.objects.filter(flow_file=self.object)
        context['readings'] = RegisterReading.objects.filter(flow_file=self.object)
        return context
class FlowFileDeleteView(DeleteView):
    model = FlowFile
    template_name = 'meter_readings/flowfile_confirm_delete.html'
    success_url = reverse_lazy('file_list')
    success_message = "File and all associated data were deleted successfully"
    
    def get_object(self, queryset=None):
        """Get the object and ensure it exists"""
        pk = self.kwargs.get('pk')
        return get_object_or_404(FlowFile, pk=pk)
    
    def get_context_data(self, **kwargs):
        """Add flow_file to context for template"""
        context = super().get_context_data(**kwargs)
        context['flow_file'] = self.object  # Ensure flow_file is in context
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class MeterListView(ListView):
    model = Meter
    template_name = 'meter_readings/meter_list.html'
    context_object_name = 'meters'
    paginate_by = 20
    ordering = ['serial_number']

class ReadingListView(ListView):
    model = RegisterReading
    template_name = 'meter_readings/reading_list.html'
    context_object_name = 'readings'
    paginate_by = 50
    ordering = ['-reading_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by MPAN if provided
        mpan = self.request.GET.get('mpan')
        if mpan:
            queryset = queryset.filter(meter__mpan__icontains=mpan)
        
        # Filter by serial number if provided
        serial = self.request.GET.get('serial')
        if serial:
            queryset = queryset.filter(meter__serial_number__icontains=serial)
        
        return queryset

def search_readings(request):
    """Advanced search for readings"""
    readings = RegisterReading.objects.all()
    
    if request.method == 'GET':
        mpan = request.GET.get('mpan')
        serial = request.GET.get('serial')
        register_id = request.GET.get('register_id')
        
        if mpan:
            readings = readings.filter(meter__mpan__icontains=mpan)
        if serial:
            readings = readings.filter(meter__serial_number__icontains=serial)
        if register_id:
            readings = readings.filter(register_id__icontains=register_id)
    
    return render(request, 'meter_readings/search.html', {
        'readings': readings.order_by('-reading_date')[:100],  # Limit results
        'search_params': request.GET
    })