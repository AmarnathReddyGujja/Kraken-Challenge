"""
Django models for the Meter Reading Import System.

This module defines the core data models for storing meter reading data
imported from various file formats (UFF, PDF, CSV, JSON, XML, TXT).

The system follows the UK DTC D0010 standard for meter data exchange
and implements robust duplicate prevention mechanisms.
"""

from django.db import models
from django.utils import timezone


class FlowFile(models.Model):
    """
    Represents a data file that has been imported into the system.
    
    This model stores metadata about imported files including:
    - File identification (filename, checksum for duplicate prevention)
    - Processing status and statistics
    - Header information from D0010 ZHV records
    
    The checksum field enables idempotent imports - files with identical
    content will be automatically skipped to prevent duplicate data.
    """
    
    # File identification and metadata
    filename = models.CharField(
        max_length=255,
        help_text="Original filename of the imported file"
    )
    file_type = models.CharField(
        max_length=10, 
        default='D0010',
        help_text="Type of file format (UFF, PDF, CSV, JSON, XML, TXT, EXCEL, WORD)"
    )
    import_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When this file was imported into the system"
    )
    record_count = models.IntegerField(
        default=0,
        help_text="Total number of records processed from this file"
    )
    status = models.CharField(
        max_length=20, 
        default='IMPORTED',
        choices=[
            ('PROCESSING', 'Processing'),
            ('IMPORTED', 'Imported'),
            ('ERROR', 'Error'),
        ],
        help_text="Current processing status of the file"
    )
    checksum = models.CharField(
        max_length=64, 
        unique=True, 
        null=True, 
        blank=True,
        help_text='SHA-256 checksum of file contents for duplicate prevention'
    )
    
    # Header fields from D0010 ZHV record (UK industry standard)
    sequence_number = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Sequence number from ZHV header record"
    )
    version = models.CharField(
        max_length=10, 
        blank=True,
        help_text="D0010 version number from ZHV header record"
    )
    record_type = models.CharField(
        max_length=1, 
        blank=True,
        help_text="Record type indicator from ZHV header record"
    )
    sender = models.CharField(
        max_length=10, 
        blank=True,
        help_text="Sender identifier from ZHV header record"
    )
    receiver = models.CharField(
        max_length=10, 
        blank=True,
        help_text="Receiver identifier from ZHV header record"
    )
    creation_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="File creation date from ZHV header record"
    )
    
    class Meta:
        """Model metadata configuration."""
        indexes = [
            models.Index(fields=['filename']),
            models.Index(fields=['checksum']),
        ]
        verbose_name = "Flow File"
        verbose_name_plural = "Flow Files"
    
    def __str__(self):
        """String representation of the FlowFile."""
        return self.filename


class Meter(models.Model):
    """
    Represents a physical meter device that takes readings.
    
    Each meter is identified by a unique serial number and is associated
    with a Meter Point Administration Number (MPAN) for billing purposes.
    
    The meter type indicates what kind of energy it measures (electricity,
    gas, water, or heat) following industry standards.
    """
    
    # Energy type choices following industry standards
    METER_TYPES = [
        ('E', 'Electricity'),
        ('G', 'Gas'),
        ('W', 'Water'),
        ('H', 'Heat'),
    ]
    
    # Primary identification
    serial_number = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text="Unique serial number of the physical meter device"
    )
    mpan = models.CharField(
        max_length=20, 
        db_index=True, 
        help_text='Meter Point Administration Number for billing identification',
        default='0000000000000'
    )
    meter_type = models.CharField(
        max_length=1, 
        choices=METER_TYPES, 
        default='E',
        help_text="Type of energy measured by this meter"
    )
    
    # Relationships and metadata
    flow_file = models.ForeignKey(
        FlowFile, 
        on_delete=models.CASCADE,
        help_text="The file from which this meter was imported"
    )
    created_date = models.DateTimeField(
        default=timezone.now,
        help_text="When this meter record was created"
    )
    
    class Meta:
        """Model metadata configuration."""
        indexes = [
            models.Index(fields=['serial_number']),
            models.Index(fields=['mpan']),
        ]
        verbose_name = "Meter"
        verbose_name_plural = "Meters"
    
    def __str__(self):
        """String representation of the Meter."""
        return f"{self.serial_number} ({self.mpan})"


class RegisterReading(models.Model):
    """
    Represents a single meter reading taken at a specific time.
    
    Each reading is associated with a meter and a specific register
    (e.g., day/night rates, different measurement periods). The system
    prevents duplicate readings through unique constraints on the natural
    key combination of meter, register, date, and value.
    
    Reading types follow D0010 standards:
    - A: Actual reading (physical meter reading)
    - E: Estimated reading
    - C: Customer reading
    - W: Withdrawn reading
    - Z: Zero consumption
    """
    
    # Relationships
    meter = models.ForeignKey(
        Meter, 
        on_delete=models.CASCADE, 
        related_name='readings',
        help_text="The meter that took this reading"
    )
    flow_file = models.ForeignKey(
        FlowFile, 
        on_delete=models.CASCADE,
        help_text="The file from which this reading was imported"
    )
    
    # Reading data
    register_id = models.CharField(
        max_length=10,
        help_text="Register identifier (S, TO, A1, 01, 02, etc.)"
    )
    reading_date = models.DateTimeField(
        help_text="When this reading was taken"
    )
    reading_value = models.DecimalField(
        max_digits=12, 
        decimal_places=3,
        help_text="The actual reading value"
    )
    
    # Reading metadata
    reading_type = models.CharField(
        max_length=1, 
        default='N',
        help_text="Type of reading (A=Actual, E=Estimate, C=Customer, W=Withdrawn, Z=Zero)"
    )
    measurement_method = models.CharField(
        max_length=1, 
        default='T',
        help_text="How the reading was obtained (T=Telemetry, E=Estimated, etc.)"
    )
    
    class Meta:
        """Model metadata configuration."""
        ordering = ['reading_date']
        constraints = [
            # Prevent duplicate readings with same meter, register, date, and value
            models.UniqueConstraint(
                fields=['meter', 'register_id', 'reading_date', 'reading_value'],
                name='uniq_reading_natural_key'
            )
        ]
        indexes = [
            models.Index(fields=['meter', 'register_id']),
            models.Index(fields=['reading_date']),
        ]
        verbose_name = "Register Reading"
        verbose_name_plural = "Register Readings"
    
    def __str__(self):
        """String representation of the RegisterReading."""
        return f"{self.meter.serial_number} - {self.register_id} - {self.reading_value}"