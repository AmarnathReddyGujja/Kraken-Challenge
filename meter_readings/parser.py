import os
import hashlib
import logging
from datetime import datetime
from django.utils.timezone import make_aware
from django.db import transaction
from .models import FlowFile, MeterPoint, Meter, RegisterReading

logger = logging.getLogger(__name__)

class D0010Parser:
    def __init__(self):
        self.current_mpan = None
        self.current_meter = None
        self.current_flow_file = None
        self.stats = {
            'meter_points_created': 0,
            'meters_created': 0,
            'readings_created': 0,
            'duplicates_skipped': 0
        }
        
    def _calculate_checksum(self, file_path):
        """Calculate SHA-256 checksum of file contents"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    @transaction.atomic
    def parse_file(self, file_path, original_filename=None):
        """Parse a D0010 UFF file and import data with duplicate prevention"""
        logger.info(f"Attempting to parse file: {file_path}")
        
        if not os.path.exists(file_path):
            raise ValueError(f"File does not exist: {file_path}")
            
        # Use original filename if provided, otherwise use basename of file_path
        filename = original_filename if original_filename else os.path.basename(file_path)
        logger.info(f"Filename: {filename}")
        
        # Calculate checksum for idempotency
        checksum = self._calculate_checksum(file_path)
        logger.info(f"File checksum: {checksum}")
        
        # Check if file with same checksum was already processed
        existing_file = FlowFile.objects.filter(checksum=checksum).first()
        if existing_file:
            logger.warning(f"File with same checksum already processed: {existing_file.filename}")
            raise ValueError(f"File with same content already processed as '{existing_file.filename}'")
        
        # Check if filename was seen before but with different content
        filename_exists = FlowFile.objects.filter(filename=filename).exists()
        if filename_exists:
            logger.warning(f"Filename '{filename}' previously seen with different content; proceeding with checksum-based idempotency")
        
        # Create FlowFile record
        self.current_flow_file = FlowFile.objects.create(
            filename=filename,
            file_type='D0010',
            status='PROCESSING',
            checksum=checksum
        )
        
        record_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    record_count += 1
                    logger.debug(f"Processing line {line_num}: {line[:50]}...")
                    self.parse_record(line)
                    
            logger.info(f"Total records processed: {record_count}")
                    
        except IOError as e:
            # Clean up the flow file record if reading fails
            if self.current_flow_file and self.current_flow_file.pk:
                self.current_flow_file.status = 'ERROR'
                self.current_flow_file.save()
            logger.error(f"Error reading file: {str(e)}")
            raise ValueError(f"Error reading file: {str(e)}")
        except Exception as e:
            # Clean up on any other error
            if self.current_flow_file and self.current_flow_file.pk:
                self.current_flow_file.status = 'ERROR'
                self.current_flow_file.save()
            logger.error(f"Unexpected error during parsing: {str(e)}")
            raise
        
        # Update record count and status
        self.current_flow_file.record_count = record_count
        self.current_flow_file.status = 'IMPORTED'
        self.current_flow_file.save()
        
        logger.info(f"Parse completed. Stats: {self.stats}")
        
        return self.current_flow_file, self.stats
    
    def parse_record(self, record_line):
        """Parse individual record line"""
        try:
            fields = record_line.split('|')
            record_type = fields[0]
            
            logger.debug(f"Parsing record type: {record_type}")
            
            if record_type == 'ZHV':
                self.parse_zhv_record(fields)
            elif record_type == '026':
                self.parse_026_record(fields)
            elif record_type == '028':
                self.parse_028_record(fields)
            elif record_type == '030':
                self.parse_030_record(fields)
            else:
                logger.warning(f"Unknown record type: {record_type}")
        except Exception as e:
            # Log parsing errors but continue processing
            logger.error(f"Error parsing record: {record_line} - {str(e)}")
    
    def parse_zhv_record(self, fields):
        """Parse ZHV header record"""
        logger.debug("Parsing ZHV record")
        if len(fields) >= 8:
            try:
                creation_date = make_aware(datetime.strptime(fields[7], '%Y%m%d%H%M%S'))
            except Exception as e:
                logger.warning(f"Error parsing date: {fields[7]} - {e}")
                creation_date = None
                
            self.current_flow_file.sequence_number = fields[1]
            self.current_flow_file.version = fields[2]
            self.current_flow_file.record_type = fields[3]
            self.current_flow_file.sender = fields[4]
            self.current_flow_file.receiver = fields[6]
            self.current_flow_file.creation_date = creation_date
            self.current_flow_file.save()
            logger.debug(f"ZHV parsed: sender={fields[4]}, receiver={fields[6]}")
    
    def parse_026_record(self, fields):
        """Parse 026 Meter Point record - prevent duplicates by MPAN"""
        logger.debug("Parsing 026 record")
        if len(fields) >= 2:
            mpan = fields[1].strip()
            if not mpan:
                logger.warning("Empty MPAN, skipping")
                return
                
            logger.debug(f"MPAN: {mpan}")
                
            # Get or create MeterPoint (prevents duplicates by MPAN)
            self.current_mpan, created = MeterPoint.objects.get_or_create(
                mpan=mpan
            )
            if created:
                self.stats['meter_points_created'] += 1
                logger.debug(f"Created new meter point: {mpan}")
            else:
                logger.debug(f"Using existing meter point: {mpan}")
    
    def parse_028_record(self, fields):
        """Parse 028 Meter record - prevent duplicates by serial number"""
        logger.debug("Parsing 028 record")
        if len(fields) >= 2 and self.current_mpan:
            serial_number = fields[1].strip()
            meter_type = fields[2] if len(fields) > 2 else 'C'
            
            if not serial_number:
                logger.warning("Empty serial number, skipping")
                return
            
            logger.debug(f"Meter serial: {serial_number}, type: {meter_type}")
            
            # Get or create Meter (prevents duplicates by serial number)
            self.current_meter, created = Meter.objects.get_or_create(
                serial_number=serial_number,
                defaults={
                    'meter_point': self.current_mpan,
                    'meter_type': meter_type,
                    'flow_file': self.current_flow_file
                }
            )
            if created:
                self.stats['meters_created'] += 1
                logger.debug(f"Created new meter: {serial_number}")
            else:
                # Meter exists, but we still track which flow file contained it
                self.current_meter.flow_file = self.current_flow_file
                self.current_meter.save()
                logger.debug(f"Updated existing meter: {serial_number}")
        else:
            logger.warning("No current MPAN for meter record")
    
    def parse_030_record(self, fields):
        """Parse 030 Reading record - prevent duplicates by unique combination"""
        logger.debug("Parsing 030 record")
        if len(fields) >= 4 and self.current_meter:
            register_id = fields[1].strip()
            
            try:
                reading_date = make_aware(datetime.strptime(fields[2], '%Y%m%d%H%M%S'))
                logger.debug(f"Reading date parsed: {reading_date}")
            except Exception as e:
                logger.warning(f"Error parsing reading date: {fields[2]} - {e}")
                reading_date = make_aware(datetime.now())
            
            try:
                reading_value = float(fields[3])
                logger.debug(f"Reading value: {reading_value}")
            except Exception as e:
                logger.warning(f"Error parsing reading value: {fields[3]} - {e}")
                reading_value = 0.0
            
            reading_type = fields[7] if len(fields) > 7 else 'N'
            measurement_method = fields[6] if len(fields) > 6 else 'T'
            
            logger.debug(f"Creating reading: register={register_id}, date={reading_date}, value={reading_value}")
            
            # Prevent duplicate readings - unique by meter, register, reading_date, and reading_value
            reading, created = RegisterReading.objects.get_or_create(
                meter=self.current_meter,
                register_id=register_id,
                reading_date=reading_date,
                reading_value=reading_value,
                defaults={
                    'reading_type': reading_type,
                    'measurement_method': measurement_method,
                    'flow_file': self.current_flow_file
                }
            )
            
            if created:
                self.stats['readings_created'] += 1
                logger.debug(f"Created new reading")
            else:
                self.stats['duplicates_skipped'] += 1
                logger.debug(f"Skipped duplicate reading")
        else:
            logger.warning("No current meter for reading record")