from django import forms
from .models import FlowFile

class FlowFileUploadForm(forms.Form):
    file = forms.FileField(
        label='Upload Data File',
        help_text='Select any data file to import (UFF, CSV, TXT, JSON, XML, etc.)',
        widget=forms.FileInput(attrs={'accept': '*'})
    )
    
    def clean_file(self):
        file = self.cleaned_data['file']
        # Allow all file types - we'll detect format during parsing
        return file