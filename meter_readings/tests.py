"""
Comprehensive test suite for the Meter Reading application.

This test suite covers:
- Model functionality and constraints
- Parser functionality (UFF, CSV, JSON, XML, TXT)
- View functionality and URL routing
- Admin interface
- Database constraints and data integrity
- Error handling and edge cases
- File upload and processing
- Search functionality
"""

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.timezone import make_aware
from django.contrib.auth.models import User
from django.db import IntegrityError
from datetime import datetime
import tempfile
import os
import hashlib
import json
import csv
import xml.etree.ElementTree as ET
from .models import FlowFile, Meter, RegisterReading
from .universal_parser import UniversalParser
from .d0010_standard_parser import D0010StandardParser
from .fallback_parser import FallbackParser


class ModelTests(TestCase):
    """Test model functionality and basic operations"""
    
    def setUp(self):
        self.flow_file = FlowFile.objects.create(
            filename="test.uff",
            file_type="UFF",
            record_count=10,
            checksum="test_checksum_123"
        )
        self.meter = Meter.objects.create(
            serial_number="F75A00802",
            mpan="1200023305967",
            meter_type="C",
            flow_file=self.flow_file
        )
    
    def test_flow_file_creation(self):
        """Test FlowFile model creation and string representation"""
        self.assertEqual(str(self.flow_file), "test.uff")
        self.assertTrue(isinstance(self.flow_file, FlowFile))
        self.assertEqual(self.flow_file.file_type, "UFF")
        self.assertEqual(self.flow_file.record_count, 10)
    
    def test_meter_creation(self):
        """Test Meter model creation and string representation"""
        self.assertEqual(str(self.meter), "F75A00802 (1200023305967)")
        self.assertEqual(Meter.objects.count(), 1)
        self.assertEqual(self.meter.mpan, "1200023305967")
        self.assertEqual(self.meter.serial_number, "F75A00802")
        self.assertEqual(self.meter.meter_type, "C")
    
    def test_reading_creation(self):
        """Test RegisterReading model creation"""
        reading = RegisterReading.objects.create(
            meter=self.meter,
            flow_file=self.flow_file,
            register_id="S",
            reading_date=make_aware(datetime(2023, 1, 1)),
            reading_value=12345.67
        )
        self.assertEqual(RegisterReading.objects.count(), 1)
        self.assertEqual(reading.reading_value, 12345.67)
        self.assertEqual(reading.register_id, "S")
        self.assertEqual(str(reading), "F75A00802 - S - 12345.67")


class ParserTests(TestCase):
    """Test parser functionality for different file formats"""
    
    def create_test_file(self, content, suffix='.uff'):
        """Helper to create temporary test file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix)
        temp_file.write(content)
        temp_file.flush()
        return temp_file.name
    
    def test_universal_parser_uff_standard(self):
        """Test UniversalParser with standard D0010 UFF file"""
        content = """ZHD|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|
026|1200023305967|V|
028|F75A00802|S|kWh|A|20160222000000|20160222000000|20160222000000|20160222000000|56311.0|N|
029|S|20160222000000|56311.0|N|T|
ZTR|5|"""
        
        file_path = self.create_test_file(content, '.uff')
        
        try:
            parser = UniversalParser()
            flow_file, stats = parser.parse_file(file_path)
            
            self.assertEqual(flow_file.record_count, 5)
            self.assertEqual(Meter.objects.count(), 1)
            self.assertEqual(RegisterReading.objects.count(), 1)
            
            meter = Meter.objects.first()
            self.assertEqual(meter.serial_number, "F75A00802")
            self.assertEqual(meter.mpan, "1200023305967")
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_universal_parser_uff_fallback(self):
        """Test UniversalParser with non-standard UFF file"""
        content = """ZHV|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|
026|1200023305967|V|
028|F75A00802|D|
030|S|20160222000000|56311.0|||T|N|
ZPT|4|"""
        
        file_path = self.create_test_file(content, '.uff')
        
        try:
            parser = UniversalParser()
            flow_file, stats = parser.parse_file(file_path)
            
            self.assertEqual(flow_file.record_count, 4)
            self.assertEqual(Meter.objects.count(), 1)
            self.assertEqual(RegisterReading.objects.count(), 1)
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_universal_parser_csv(self):
        """Test UniversalParser with CSV file"""
        content = """mpan,serial,reading,date
1200023305967,F75A00802,12345.67,2023-01-01
1900001059816,S95105287,67890.12,2023-01-02"""
        
        file_path = self.create_test_file(content, '.csv')
        
        try:
            parser = UniversalParser()
            flow_file, stats = parser.parse_file(file_path)
            
            self.assertEqual(Meter.objects.count(), 2)
            self.assertEqual(RegisterReading.objects.count(), 2)
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_universal_parser_json(self):
        """Test UniversalParser with JSON file"""
        data = {
            "readings": [
                {
                    "mpan": "1200023305967",
                    "serial": "F75A00802",
                    "reading": 12345.67,
                    "date": "2023-01-01"
                },
                {
                    "mpan": "1900001059816",
                    "serial": "S95105287",
                    "reading": 67890.12,
                    "date": "2023-01-02"
                }
            ]
        }
        
        file_path = self.create_test_file(json.dumps(data), '.json')
        
        try:
            parser = UniversalParser()
            flow_file, stats = parser.parse_file(file_path)
            
            self.assertEqual(Meter.objects.count(), 2)
            self.assertEqual(RegisterReading.objects.count(), 2)
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_universal_parser_xml(self):
        """Test UniversalParser with XML file"""
        content = """<?xml version="1.0" encoding="UTF-8"?>
<readings>
    <reading mpan="1200023305967" serial="F75A00802" value="12345.67" date="2023-01-01" />
    <reading mpan="1900001059816" serial="S95105287" value="67890.12" date="2023-01-02" />
</readings>"""
        
        file_path = self.create_test_file(content, '.xml')
        
        try:
            parser = UniversalParser()
            flow_file, stats = parser.parse_file(file_path)
            
            self.assertEqual(Meter.objects.count(), 2)
            self.assertEqual(RegisterReading.objects.count(), 2)
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_universal_parser_txt(self):
        """Test UniversalParser with TXT file"""
        content = """1200023305967|F75A00802|12345.67|2023-01-01
1900001059816|S95105287|67890.12|2023-01-02"""
        
        file_path = self.create_test_file(content, '.txt')
        
        try:
            parser = UniversalParser()
            flow_file, stats = parser.parse_file(file_path)
            
            self.assertEqual(Meter.objects.count(), 2)
            self.assertEqual(RegisterReading.objects.count(), 2)
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)


class ViewTests(TestCase):
    """Test view functionality and URL routing"""
    
    def setUp(self):
        self.client = Client()
        self.flow_file = FlowFile.objects.create(
            filename="test.uff",
            file_type="UFF",
            record_count=10,
            checksum="test_checksum_123"
        )
        self.meter = Meter.objects.create(
            serial_number="F75A00802",
            mpan="1200023305967",
            meter_type="C",
            flow_file=self.flow_file
        )
    
    def test_home_view(self):
        """Test home page view"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload Flow File")
        self.assertContains(response, "Statistics")
    
    def test_file_list_view(self):
        """Test file list view"""
        response = self.client.get(reverse('file_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test.uff")
    
    def test_file_detail_view(self):
        """Test file detail view"""
        response = self.client.get(reverse('file_detail', args=[self.flow_file.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test.uff")
        self.assertContains(response, "F75A00802")
    
    def test_meter_list_view(self):
        """Test meter list view"""
        response = self.client.get(reverse('meter_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F75A00802")
        self.assertContains(response, "1200023305967")
    
    def test_reading_list_view(self):
        """Test reading list view"""
        RegisterReading.objects.create(
            meter=self.meter,
            flow_file=self.flow_file,
            register_id="S",
            reading_date=make_aware(datetime(2023, 1, 1)),
            reading_value=12345.67
        )
        
        response = self.client.get(reverse('reading_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F75A00802")
    
    def test_search_view(self):
        """Test search view"""
        response = self.client.get(reverse('search_readings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Advanced Search")
    
    def test_search_with_parameters(self):
        """Test search view with search parameters"""
        RegisterReading.objects.create(
            meter=self.meter,
            flow_file=self.flow_file,
            register_id="S",
            reading_date=make_aware(datetime(2023, 1, 1)),
            reading_value=12345.67
        )
        
        response = self.client.get(reverse('search_readings'), {
            'mpan': '1200023305967',
            'serial': 'F75A00802'
        })
        self.assertEqual(response.status_code, 200)


class FileUploadTests(TestCase):
    """Test file upload functionality"""
    
    def setUp(self):
        self.client = Client()
    
    def test_file_upload_uff(self):
        """Test UFF file upload"""
        content = """ZHV|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|
026|1200023305967|V|
028|F75A00802|D|
030|S|20160222000000|56311.0|||T|N|
ZPT|4|"""
        
        uploaded_file = SimpleUploadedFile(
            "test.uff",
            content.encode('utf-8'),
            content_type="text/plain"
        )
        
        response = self.client.post(reverse('home'), {
            'file': uploaded_file
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FlowFile.objects.count(), 1)
        self.assertEqual(Meter.objects.count(), 1)
        self.assertEqual(RegisterReading.objects.count(), 1)
    
    def test_file_upload_csv(self):
        """Test CSV file upload"""
        content = """mpan,serial,reading,date
1200023305967,F75A00802,12345.67,2023-01-01"""
        
        uploaded_file = SimpleUploadedFile(
            "test.csv",
            content.encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(reverse('home'), {
            'file': uploaded_file
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FlowFile.objects.count(), 1)
        self.assertEqual(Meter.objects.count(), 1)
        self.assertEqual(RegisterReading.objects.count(), 1)


class DuplicatePreventionTests(TestCase):
    """Test duplicate prevention functionality"""
    
    def create_test_file(self, content, suffix='.uff'):
        """Helper to create temporary test file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix)
        temp_file.write(content)
        temp_file.flush()
        return temp_file.name
    
    def test_checksum_calculation(self):
        """Test that checksum is calculated correctly"""
        content = "ZHV|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|"
        file_path = self.create_test_file(content)
        
        try:
            parser = UniversalParser()
            checksum = parser._calculate_checksum(file_path)
            
            expected_checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
            self.assertEqual(checksum, expected_checksum)
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_duplicate_file_prevention(self):
        """Test that duplicate files are prevented by checksum"""
        content = "ZHV|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|"
        checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Create existing file with same checksum
        FlowFile.objects.create(
            filename="already_processed.uff",
            checksum=checksum
        )
        
        parser = UniversalParser()
        file_path = self.create_test_file(content)
        
        try:
            with self.assertRaises(ValueError) as context:
                parser.parse_file(file_path)
            
            self.assertIn("already processed", str(context.exception))
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_same_filename_different_content(self):
        """Test that files with same filename but different content can be imported"""
        content1 = "ZHV|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|"
        content2 = "ZHV|0000475657|D0010002|D|UDMS|X|MRCY|20160302153152||||OPER|"
        
        file1_path = self.create_test_file(content1)
        file2_path = self.create_test_file(content2)
        
        try:
            parser = UniversalParser()
            
            # Import first file
            flow_file1, stats1 = parser.parse_file(file1_path)
            self.assertEqual(FlowFile.objects.count(), 1)
            
            # Import second file with different content
            flow_file2, stats2 = parser.parse_file(file2_path)
            self.assertEqual(FlowFile.objects.count(), 2)
            self.assertNotEqual(flow_file1.checksum, flow_file2.checksum)
            
        finally:
            for path in [file1_path, file2_path]:
                if os.path.exists(path):
                    os.unlink(path)


class ErrorHandlingTests(TestCase):
    """Test error handling and edge cases"""
    
    def create_test_file(self, content, suffix='.uff'):
        """Helper to create temporary test file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix)
        temp_file.write(content)
        temp_file.flush()
        return temp_file.name
    
    def test_malformed_data_handling(self):
        """Test that malformed data is handled gracefully"""
        content = """ZHV|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|
026|1200023305967|V|
028|F75A00802|D|
INVALID|malformed|record|here|
030|S|20160222000000|56311.0|||T|N|
ZPT|5|"""
        
        file_path = self.create_test_file(content)
        
        try:
            parser = UniversalParser()
            flow_file, stats = parser.parse_file(file_path)
            
            # Should still process valid records
            self.assertEqual(Meter.objects.count(), 1)
            self.assertEqual(RegisterReading.objects.count(), 1)
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_empty_file_handling(self):
        """Test that empty files are handled gracefully"""
        file_path = self.create_test_file("")
        
        try:
            parser = UniversalParser()
            flow_file, stats = parser.parse_file(file_path)
            
            # Should create flow file but no data
            self.assertEqual(FlowFile.objects.count(), 1)
            self.assertEqual(Meter.objects.count(), 0)
            self.assertEqual(RegisterReading.objects.count(), 0)
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def test_invalid_file_format(self):
        """Test that invalid file formats are handled gracefully"""
        content = "This is not a valid data file"
        file_path = self.create_test_file(content, '.invalid')
        
        try:
            parser = UniversalParser()
            
            with self.assertRaises(ValueError) as context:
                parser.parse_file(file_path)
            
            self.assertIn("Unsupported file format", str(context.exception))
            
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)


class DatabaseConstraintTests(TestCase):
    """Test database-level constraints and data integrity"""
    
    def setUp(self):
        self.flow_file = FlowFile.objects.create(
            filename="test.uff",
            file_type="UFF",
            record_count=10,
            checksum="test_checksum_123"
        )
        self.meter = Meter.objects.create(
            serial_number="F75A00802",
            mpan="1200023305967",
            meter_type="C",
            flow_file=self.flow_file
        )
    
    def test_unique_reading_constraint(self):
        """Test that duplicate readings are prevented by database constraint"""
        # Create first reading
        RegisterReading.objects.create(
            meter=self.meter,
            flow_file=self.flow_file,
            register_id="S",
            reading_date=make_aware(datetime(2023, 1, 1)),
            reading_value=12345.67
        )
        
        # Try to create duplicate reading - should raise IntegrityError
        with self.assertRaises(IntegrityError):
            RegisterReading.objects.create(
                meter=self.meter,
                flow_file=self.flow_file,
                register_id="S",
                reading_date=make_aware(datetime(2023, 1, 1)),
                reading_value=12345.67
            )
    
    def test_meter_serial_uniqueness(self):
        """Test that meter serial uniqueness is enforced"""
        # First meter should work
        Meter.objects.create(
            serial_number="TEST999999",
            mpan="9999999999999",
            meter_type="C",
            flow_file=self.flow_file
        )
        
        # Duplicate serial should raise IntegrityError
        with self.assertRaises(IntegrityError):
            Meter.objects.create(
                serial_number="TEST999999",
                mpan="8888888888888",
                meter_type="D",
                flow_file=self.flow_file
            )
    
    def test_flow_file_checksum_uniqueness(self):
        """Test that flow file checksum uniqueness is enforced"""
        # First flow file should work
        FlowFile.objects.create(
            filename="test1.uff",
            checksum="unique_checksum_123"
        )
        
        # Duplicate checksum should raise IntegrityError
        with self.assertRaises(IntegrityError):
            FlowFile.objects.create(
                filename="test2.uff",
                checksum="unique_checksum_123"
            )


class AdminTests(TestCase):
    """Test admin interface functionality"""
    
    def setUp(self):
        # Create test data
        self.flow_file = FlowFile.objects.create(
            filename="test.uff",
            file_type="UFF",
            record_count=10,
            checksum="test_checksum_123"
        )
        self.meter = Meter.objects.create(
            serial_number="F75A00802",
            mpan="1200023305967",
            meter_type="C",
            flow_file=self.flow_file
        )
        self.reading = RegisterReading.objects.create(
            meter=self.meter,
            flow_file=self.flow_file,
            register_id="S",
            reading_date=make_aware(datetime(2023, 1, 1)),
            reading_value=12345.67
        )
        
        # Create superuser for admin access
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')
    
    def test_admin_flowfile_list(self):
        """Test admin flow file list view"""
        response = self.client.get('/admin/meter_readings/flowfile/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test.uff')
    
    def test_admin_meter_list(self):
        """Test admin meter list view"""
        response = self.client.get('/admin/meter_readings/meter/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'F75A00802')
        self.assertContains(response, '1200023305967')
    
    def test_admin_reading_list(self):
        """Test admin reading list view"""
        response = self.client.get('/admin/meter_readings/registerreading/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'F75A00802')
    
    def test_admin_search_by_mpan(self):
        """Test admin search by MPAN"""
        response = self.client.get('/admin/meter_readings/registerreading/', {'q': '1200023305967'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'F75A00802')
    
    def test_admin_search_by_serial(self):
        """Test admin search by meter serial"""
        response = self.client.get('/admin/meter_readings/registerreading/', {'q': 'F75A00802'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1200023305967')


class ManagementCommandTests(TestCase):
    """Test management command functionality"""
    
    def create_test_file(self, content, suffix='.uff'):
        """Helper to create temporary test file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix)
        temp_file.write(content)
        temp_file.flush()
        return temp_file.name
    
    def test_import_command_uff(self):
        """Test import_d0010 command with UFF file"""
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        content = """ZHV|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|
026|1200023305967|V|
028|F75A00802|D|
030|S|20160222000000|56311.0|||T|N|
ZPT|4|"""
        
        file_path = self.create_test_file(content)
        
        try:
            # Capture output
            out = StringIO()
            sys.stdout = out
            
            # Call command
            call_command('import_d0010', file_path)
            
            # Check results
            self.assertEqual(FlowFile.objects.count(), 1)
            self.assertEqual(Meter.objects.count(), 1)
            self.assertEqual(RegisterReading.objects.count(), 1)
            
            # Restore stdout
            sys.stdout = sys.__stdout__
            
        except SystemExit:
            # Command may call sys.exit, which is fine
            pass
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            # Ensure stdout is restored even if test fails
            sys.stdout = sys.__stdout__
    
    def test_import_command_csv(self):
        """Test import_d0010 command with CSV file"""
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        content = """mpan,serial,reading,date
1200023305967,F75A00802,12345.67,2023-01-01"""
        
        file_path = self.create_test_file(content, '.csv')
        
        try:
            # Capture output
            out = StringIO()
            sys.stdout = out
            
            # Call command
            call_command('import_d0010', file_path)
            
            # Check results
            self.assertEqual(FlowFile.objects.count(), 1)
            self.assertEqual(Meter.objects.count(), 1)
            self.assertEqual(RegisterReading.objects.count(), 1)
            
            # Restore stdout
            sys.stdout = sys.__stdout__
            
        except SystemExit:
            # Command may call sys.exit, which is fine
            pass
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            # Ensure stdout is restored even if test fails
            sys.stdout = sys.__stdout__


class PerformanceTests(TestCase):
    """Test performance and scalability"""
    
    def test_bulk_operations(self):
        """Test bulk operations performance"""
        flow_file = FlowFile.objects.create(
            filename="bulk_test.uff",
            file_type="UFF",
            record_count=1000,
            checksum="bulk_test_checksum"
        )
        
        # Create multiple meters and readings
        meters = []
        readings = []
        
        for i in range(100):
            meter = Meter(
                serial_number=f"BULK{i:03d}",
                mpan=f"1900001059{i:03d}",
                meter_type="C",
                flow_file=flow_file
            )
            meters.append(meter)
        
        Meter.objects.bulk_create(meters)
        
        # Create readings for each meter
        for meter in Meter.objects.filter(serial_number__startswith="BULK"):
            reading = RegisterReading(
                meter=meter,
                flow_file=flow_file,
                register_id="S",
                reading_date=make_aware(datetime(2023, 1, 1)),
                reading_value=1000.0
            )
            readings.append(reading)
        
        RegisterReading.objects.bulk_create(readings)
        
        # Verify bulk operations worked
        self.assertEqual(Meter.objects.filter(serial_number__startswith="BULK").count(), 100)
        self.assertEqual(RegisterReading.objects.filter(meter__serial_number__startswith="BULK").count(), 100)


class IntegrationTests(TestCase):
    """Test end-to-end integration scenarios"""
    
    def test_complete_workflow(self):
        """Test complete workflow from file upload to data display"""
        client = Client()
        
        # Step 1: Upload a file
        content = """ZHV|0000475656|D0010002|D|UDMS|X|MRCY|20160302153151||||OPER|
026|1200023305967|V|
028|F75A00802|D|
030|S|20160222000000|56311.0|||T|N|
ZPT|4|"""
        
        uploaded_file = SimpleUploadedFile(
            "integration_test.uff",
            content.encode('utf-8'),
            content_type="text/plain"
        )
        
        response = client.post(reverse('home'), {
            'file': uploaded_file
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FlowFile.objects.count(), 1)
        
        # Step 2: Check file list
        response = client.get(reverse('file_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "integration_test.uff")
        
        # Step 3: Check file detail
        flow_file = FlowFile.objects.first()
        response = client.get(reverse('file_detail', args=[flow_file.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F75A00802")
        
        # Step 4: Check meter list
        response = client.get(reverse('meter_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F75A00802")
        self.assertContains(response, "1200023305967")
        
        # Step 5: Check reading list
        response = client.get(reverse('reading_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F75A00802")
        
        # Step 6: Test search
        response = client.get(reverse('search_readings'), {
            'mpan': '1200023305967'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F75A00802")


# Simple smoke tests
class SmokeTests(TestCase):
    """Simple smoke tests to verify basic functionality"""
    
    def test_basic_addition(self):
        """Test basic Python functionality"""
        self.assertEqual(1 + 1, 2)
    
    def test_model_str_methods(self):
        """Test model string representations"""
        flow_file = FlowFile.objects.create(filename="test.uff")
        self.assertEqual(str(flow_file), "test.uff")
        
        meter = Meter.objects.create(
            serial_number="TEST123",
            mpan="1234567890123",
            meter_type="C",
            flow_file=flow_file
        )
        self.assertEqual(str(meter), "TEST123 (1234567890123)")
    
    def test_database_connection(self):
        """Test that database connection works"""
        self.assertEqual(FlowFile.objects.count(), 0)
        FlowFile.objects.create(filename="test.uff")
        self.assertEqual(FlowFile.objects.count(), 1)