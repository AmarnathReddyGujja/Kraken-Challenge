import os
import hashlib
import logging
from datetime import datetime
from django.utils.timezone import make_aware
from django.db import transaction
from .models import FlowFile, Meter, RegisterReading

logger = logging.getLogger(__name__)

class D0010StandardParser:
    """D0010 UFF file parser following UK DTC D0010 standard specification"""
    
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

    def _parse_zhd_record(self, fields):
        """Parse ZHD (File Header) record according to D0010 standard"""
        if len(fields) < 8:
            logger.warning("ZHD record has insufficient fields")
            return
            
        # ZHD|FlowRef|Version|FromRole|ToRole|CreationDate|CreationTime|AppRef
        flow_ref = fields[1].strip() if len(fields) > 1 else ""
        version = fields[2].strip() if len(fields) > 2 else ""
        from_role = fields[3].strip() if len(fields) > 3 else ""
        to_role = fields[4].strip() if len(fields) > 4 else ""
        creation_date = fields[5].strip() if len(fields) > 5 else ""
        creation_time = fields[6].strip() if len(fields) > 6 else ""
        app_ref = fields[7].strip() if len(fields) > 7 else ""
        
        logger.info(f"ZHD: Flow={flow_ref}, Version={version}, From={from_role}, To={to_role}")
        
        # Store header information in FlowFile
        if self.current_flow_file:
            self.current_flow_file.sequence_number = flow_ref
            self.current_flow_file.version = version
            self.current_flow_file.sender = from_role
            self.current_flow_file.receiver = to_role
            
            # Parse creation date/time (CCYYMMDD HHMMSS)
            if creation_date and creation_time:
                try:
                    date_str = f"{creation_date}{creation_time}"
                    creation_dt = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    self.current_flow_file.creation_date = make_aware(creation_dt)
                except ValueError as e:
                    logger.warning(f"Error parsing creation date/time: {e}")

    def _parse_026_record(self, fields):
        """Parse 026 (MPAN Core) record according to D0010 standard"""
        if len(fields) < 3:
            logger.warning("026 record has insufficient fields")
            return
            
        # 026|MPANCore|MeasurementClass
        mpan = fields[1].strip()
        measurement_class = fields[2].strip() if len(fields) > 2 else "E"
        
        if not mpan or len(mpan) != 13:
            logger.warning(f"Invalid MPAN in 026 record: {mpan}")
            return
            
        logger.info(f"026: MPAN={mpan}, Class={measurement_class}")
        
        # Store MPAN for later use
        self.current_mpan = mpan

    def _parse_028_record(self, fields):
        """Parse 028 (Meter Reading and Register Details) record according to D0010 standard"""
        if len(fields) < 12:
            logger.warning("028 record has insufficient fields")
            return
            
        # 028|RegisterID|TPRCode|MeasurementQuantityID|MeterSerial|ReadingType|PrevDate|PrevTime|CurrDate|CurrTime|CurrValue|MDResetFlag
        register_id = fields[1].strip()
        tpr_code = fields[2].strip() if len(fields) > 2 else ""
        measurement_quantity = fields[3].strip() if len(fields) > 3 else "kWh"
        meter_serial = fields[4].strip() if len(fields) > 4 else ""
        reading_type = fields[5].strip() if len(fields) > 5 else "A"
        prev_date = fields[6].strip() if len(fields) > 6 else ""
        prev_time = fields[7].strip() if len(fields) > 7 else ""
        curr_date = fields[8].strip() if len(fields) > 8 else ""
        curr_time = fields[9].strip() if len(fields) > 9 else ""
        curr_value = fields[10].strip() if len(fields) > 10 else ""
        md_reset = fields[11].strip() if len(fields) > 11 else "N"
        
        if not meter_serial or not curr_value:
            logger.warning("Missing meter serial or current value in 028 record")
            return
            
        logger.info(f"028: Register={register_id}, Serial={meter_serial}, TPR={tpr_code}, Value={curr_value}")
        
        # Check if we have current MPAN
        if not self.current_mpan:
            logger.warning("No current MPAN for 028 record, skipping")
            return
        
        # Create or get meter
        # Use ZHD creation date if available, otherwise use current time
        creation_date = self.current_flow_file.creation_date if self.current_flow_file and self.current_flow_file.creation_date else make_aware(datetime.now())
        
        meter, created = Meter.objects.get_or_create(
            serial_number=meter_serial,
            defaults={
                'mpan': self.current_mpan,
                'meter_type': 'E',  # Default to Electricity
                'flow_file': self.current_flow_file,
                'created_date': creation_date
            }
        )
        if created:
            self.stats['meters_created'] += 1
            logger.info(f"Created new meter: {meter_serial}")
        
        self.current_meter_serial = meter_serial
        self.current_register_id = register_id
        
        # Create current reading from 028 record
        try:
            reading_val = float(curr_value)
            if curr_date and curr_time:
                try:
                    date_str = f"{curr_date}{curr_time}"
                    reading_dt = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    reading_dt = make_aware(reading_dt)
                except ValueError as e:
                    logger.warning(f"Error parsing current reading date/time: {e}")
                    reading_dt = make_aware(datetime.now())
            else:
                reading_dt = make_aware(datetime.now())
            
            reading, created = RegisterReading.objects.get_or_create(
                meter=meter,
                register_id=register_id,
                reading_date=reading_dt,
                reading_value=reading_val,
                defaults={
                    'reading_type': reading_type,
                    'flow_file': self.current_flow_file
                }
            )
            if created:
                self.stats['readings_created'] += 1
                logger.info(f"Created current reading: {reading_val} for {meter_serial}")
            else:
                self.stats['duplicates_skipped'] += 1
                logger.debug(f"Skipped duplicate current reading")
        except ValueError as e:
            logger.warning(f"Invalid current reading value: {curr_value}")
        except Exception as e:
            logger.error(f"Error creating current reading: {e}")
        
        # Create previous reading if available
        if prev_date and prev_time and prev_date != curr_date:
            try:
                prev_date_str = f"{prev_date}{prev_time}"
                prev_reading_dt = datetime.strptime(prev_date_str, '%Y%m%d%H%M%S')
                prev_reading_dt = make_aware(prev_reading_dt)
                
                # For previous reading, we need to estimate the value
                # In a real scenario, this would come from historical data
                # For now, we'll create a placeholder
                prev_reading, created = RegisterReading.objects.get_or_create(
                    meter=meter,
                    register_id=register_id,
                    reading_date=prev_reading_dt,
                    reading_value=0.0,  # Placeholder - would need actual previous value
                    defaults={
                        'reading_type': 'E',  # Estimated
                        'flow_file': self.current_flow_file
                    }
                )
                if created:
                    self.stats['readings_created'] += 1
                    logger.info(f"Created previous reading placeholder for {meter_serial}")
            except ValueError as e:
                logger.warning(f"Error parsing previous reading date/time: {e}")

    def _parse_029_record(self, fields):
        """Parse 029 (Individual Register Reading Details) record according to D0010 standard"""
        if len(fields) < 8:
            logger.warning("029 record has insufficient fields")
            return
            
        # 029|ReadingSequence|ReadingDate|ReadingTime|RegisterReading|ReadingReason|ReadingMethod|ReceivedDateTime
        reading_sequence = fields[1].strip() if len(fields) > 1 else "1"
        reading_date = fields[2].strip() if len(fields) > 2 else ""
        reading_time = fields[3].strip() if len(fields) > 3 else ""
        register_reading = fields[4].strip() if len(fields) > 4 else ""
        reading_reason = fields[5].strip() if len(fields) > 5 else "S"
        reading_method = fields[6].strip() if len(fields) > 6 else "A"
        received_datetime = fields[7].strip() if len(fields) > 7 else ""
        
        if not register_reading or not reading_date:
            logger.warning("Missing reading value or date in 029 record, skipping")
            return
            
        try:
            reading_value = float(register_reading)
        except ValueError:
            logger.warning(f"Invalid reading value: {register_reading}")
            return
            
        # Parse reading date/time
        try:
            date_str = f"{reading_date}{reading_time}"
            reading_dt = datetime.strptime(date_str, '%Y%m%d%H%M%S')
            reading_dt = make_aware(reading_dt)
        except ValueError as e:
            logger.warning(f"Error parsing reading date/time: {e}")
            reading_dt = make_aware(datetime.now())
        
        # Get current meter
        if not self.current_meter_serial:
            logger.warning("No current meter serial for 029 record, skipping")
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
                reading_value=reading_value,
                defaults={
                    'reading_type': reading_method,
                    'flow_file': self.current_flow_file
                }
            )
            if created:
                self.stats['readings_created'] += 1
                logger.info(f"Created 029 reading: {reading_value} for {self.current_meter_serial}")
            else:
                self.stats['duplicates_skipped'] += 1
                logger.debug(f"Skipped duplicate 029 reading")
        except Exception as e:
            logger.error(f"Error creating 029 reading: {e}")

    def _parse_ztr_record(self, fields):
        """Parse ZTR (File Trailer) record according to D0010 standard"""
        if len(fields) < 3:
            logger.warning("ZTR record has insufficient fields")
            return
            
        # ZTR|RecordCount|Checksum
        record_count = fields[1].strip() if len(fields) > 1 else "0"
        checksum = fields[2].strip() if len(fields) > 2 else ""
        
        logger.info(f"ZTR: Record count={record_count}, Checksum={checksum}")

    def parse_record(self, record_line):
        """Parse a single record line according to D0010 standard"""
        if not record_line.strip():
            return
            
        fields = record_line.split('|')
        record_type = fields[0].strip()
        
        logger.debug(f"Parsing D0010 record type: {record_type}")
        
        if record_type == 'ZHD':
            self._parse_zhd_record(fields)
        elif record_type == '026':
            self._parse_026_record(fields)
        elif record_type == '028':
            self._parse_028_record(fields)
        elif record_type == '029':
            self._parse_029_record(fields)
        elif record_type == 'ZTR':
            self._parse_ztr_record(fields)
        else:
            logger.warning(f"Unknown D0010 record type: {record_type}")

    @transaction.atomic
    def parse_file(self, file_path, original_filename=None):
        """Parse a D0010 UFF file and import data with duplicate prevention"""
        logger.info(f"Attempting to parse D0010 file: {file_path}")
        
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
                        logger.warning(f"Error parsing D0010 line {line_num}: {e}")
                        continue
            
            # Update FlowFile with final stats
            self.current_flow_file.record_count = (
                self.stats['meter_points_created'] + 
                self.stats['meters_created'] + 
                self.stats['readings_created']
            )
            self.current_flow_file.status = 'IMPORTED'
            self.current_flow_file.save()
            
            logger.info(f"Successfully imported D0010 file {filename}: {self.stats}")
            return self.current_flow_file, self.stats
            
        except Exception as e:
            self.current_flow_file.status = 'ERROR'
            self.current_flow_file.save()
            logger.error(f"Error parsing D0010 file {filename}: {e}")
            raise
