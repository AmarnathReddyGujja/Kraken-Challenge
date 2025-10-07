import os
import hashlib
import logging
from datetime import datetime
from django.utils.timezone import make_aware
from django.db import transaction
from .models import FlowFile, Meter, RegisterReading

logger = logging.getLogger(__name__)

class FallbackParser:
    """Fallback parser for non-standard UFF files and other formats"""
    
    def __init__(self):
        self.stats = {
            'meters_created': 0,
            'readings_created': 0,
            'duplicates_skipped': 0
        }
        self.current_flow_file = None
        self.current_mpan = None
        self.current_meter_serial = None
        self.current_register_id = None

    def _calculate_checksum(self, file_path):
        """Calculate SHA-256 checksum of file contents"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _parse_zhv_record(self, fields):
        """Parse ZHV (Header) record - non-standard variant"""
        logger.info("Parsing ZHV record (non-standard variant)")
        if len(fields) < 8:
            logger.warning("ZHV record has insufficient fields")
            return
            
        flow_ref = fields[1] if len(fields) > 1 else ""
        version = fields[2] if len(fields) > 2 else ""
        from_role = fields[3] if len(fields) > 3 else ""
        to_role = fields[4] if len(fields) > 4 else ""
        creation_date = fields[5] if len(fields) > 5 else ""
        creation_time = fields[6] if len(fields) > 6 else ""
        
        logger.info(f"ZHV: Flow={flow_ref}, Version={version}, From={from_role}, To={to_role}")
        
        # Store header information in FlowFile
        if self.current_flow_file:
            self.current_flow_file.sequence_number = flow_ref
            self.current_flow_file.version = version
            self.current_flow_file.sender = from_role
            self.current_flow_file.receiver = to_role
            
            # Parse creation date/time
            if creation_date and creation_time and creation_date.isdigit() and creation_time.isdigit():
                try:
                    date_str = f"{creation_date}{creation_time}"
                    creation_dt = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    self.current_flow_file.creation_date = make_aware(creation_dt)
                except ValueError as e:
                    logger.warning(f"Error parsing creation date/time: {e}")

    def _parse_026_record(self, fields):
        """Parse 026 (MPAN Core) record - simplified for non-standard format"""
        if len(fields) < 3:
            logger.warning("026 record has insufficient fields")
            return
            
        mpan = fields[1].strip()
        measurement_class = fields[2].strip() if len(fields) > 2 else "E"
        
        if not mpan:
            logger.warning("Empty MPAN in 026 record, skipping")
            return
            
        logger.info(f"026: MPAN={mpan}, Class={measurement_class}")
        
        # Store MPAN for later use
        self.current_mpan = mpan

    def _parse_028_record(self, fields):
        """Parse 028 (Meter Reading and Register Details) record - simplified for non-standard format"""
        if len(fields) < 2:
            logger.warning("028 record has insufficient fields")
            return
            
        # In non-standard format, 028 seems to be just the meter serial
        meter_serial = fields[1].strip()
        
        if not meter_serial:
            logger.warning("Empty meter serial in 028 record, skipping")
            return
            
        logger.info(f"028: Serial={meter_serial}")
        
        # Check if we have current MPAN
        if not self.current_mpan:
            logger.warning("No current MPAN for 028 record, skipping")
            return
        
        # Create or get meter
        meter, created = Meter.objects.get_or_create(
            serial_number=meter_serial,
            defaults={
                'mpan': self.current_mpan,
                'meter_type': 'E',  # Default to Electricity
                'flow_file': self.current_flow_file,
                'created_date': make_aware(datetime.now())
            }
        )
        if created:
            self.stats['meters_created'] += 1
            logger.info(f"Created new meter: {meter_serial}")
        
        self.current_meter_serial = meter_serial
        self.current_register_id = "00"  # Default register ID

    def _parse_030_record(self, fields):
        """Parse 030 (Reading) record - non-standard variant"""
        if len(fields) < 5:
            logger.warning("030 record has insufficient fields")
            return
            
        reading_type = fields[1].strip() if len(fields) > 1 else "S"
        reading_date = fields[2].strip() if len(fields) > 2 else ""
        reading_value = fields[3].strip() if len(fields) > 3 else ""
        
        if not reading_value or not reading_date:
            logger.warning("Missing reading value or date in 030 record, skipping")
            return
            
        try:
            reading_val = float(reading_value)
        except ValueError:
            logger.warning(f"Invalid reading value: {reading_value}")
            return
            
        # Parse reading date (format: YYYYMMDDHHMMSS)
        try:
            reading_dt = datetime.strptime(reading_date, '%Y%m%d%H%M%S')
            reading_dt = make_aware(reading_dt)
        except ValueError as e:
            logger.warning(f"Error parsing reading date: {e}")
            reading_dt = make_aware(datetime.now())
        
        # Get current meter
        if not self.current_meter_serial:
            logger.warning("No current meter serial for 030 record, skipping")
            return
            
        meter = Meter.objects.filter(serial_number=self.current_meter_serial).first()
        if not meter:
            logger.warning(f"Meter not found for serial: {self.current_meter_serial}")
            return
        
        # Create reading
        try:
            reading, created = RegisterReading.objects.get_or_create(
                meter=meter,
                register_id=self.current_register_id or "00",
                reading_date=reading_dt,
                reading_value=reading_val,
                defaults={
                    'reading_type': reading_type,
                    'flow_file': self.current_flow_file
                }
            )
            if created:
                self.stats['readings_created'] += 1
                logger.info(f"Created new reading: {reading_val} for {self.current_meter_serial}")
            else:
                self.stats['duplicates_skipped'] += 1
                logger.debug(f"Skipped duplicate reading")
        except Exception as e:
            logger.error(f"Error creating reading: {e}")

    def _parse_zpt_record(self, fields):
        """Parse ZPT (Trailer) record - non-standard variant"""
        logger.info("Parsing ZPT record (non-standard variant)")
        if len(fields) < 2:
            logger.warning("ZPT record has insufficient fields")
            return
            
        record_count = fields[1].strip() if len(fields) > 1 else "0"
        logger.info(f"ZPT: Record count={record_count}")

    def parse_record(self, record_line):
        """Parse a single record line"""
        if not record_line.strip():
            return
            
        fields = record_line.split('|')
        record_type = fields[0].strip()
        
        logger.debug(f"Parsing fallback record type: {record_type}")
        
        if record_type == 'ZHV':
            self._parse_zhv_record(fields)
        elif record_type == '026':
            self._parse_026_record(fields)
        elif record_type == '028':
            self._parse_028_record(fields)
        elif record_type == '030':
            self._parse_030_record(fields)
        elif record_type == 'ZPT':
            self._parse_zpt_record(fields)
        else:
            logger.warning(f"Unknown record type: {record_type}")

    @transaction.atomic
    def parse_file(self, file_path, original_filename=None):
        """Parse a non-standard UFF file and import data with duplicate prevention"""
        logger.info(f"Attempting to parse fallback file: {file_path}")
        
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
            file_type='UFF',
            status='PROCESSING',
            checksum=checksum
        )
        
        try:
            # Parse the file
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self.parse_record(line)
                    except Exception as e:
                        logger.warning(f"Error parsing fallback line {line_num}: {e}")
                        continue
            
            # Update FlowFile with final stats
            self.current_flow_file.record_count = (
                self.stats['meter_points_created'] + 
                self.stats['meters_created'] + 
                self.stats['readings_created']
            )
            self.current_flow_file.status = 'IMPORTED'
            self.current_flow_file.save()
            
            logger.info(f"Successfully imported fallback file {filename}: {self.stats}")
            return self.current_flow_file, self.stats
            
        except Exception as e:
            self.current_flow_file.status = 'ERROR'
            self.current_flow_file.save()
            logger.error(f"Error parsing fallback file {filename}: {e}")
            raise
