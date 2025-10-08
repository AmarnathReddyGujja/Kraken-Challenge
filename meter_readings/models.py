from django.db import models
from django.utils import timezone

class FlowFile(models.Model):
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, default='D0010')
    import_date = models.DateTimeField(auto_now_add=True)
    record_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='IMPORTED')
    checksum = models.CharField(max_length=64, unique=True, null=True, blank=True, 
                                help_text='SHA-256 checksum of file contents for idempotency')
    
    # Header fields from ZHV record
    sequence_number = models.CharField(max_length=20, blank=True)
    version = models.CharField(max_length=10, blank=True)
    record_type = models.CharField(max_length=1, blank=True)
    sender = models.CharField(max_length=10, blank=True)
    receiver = models.CharField(max_length=10, blank=True)
    creation_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['filename']),
            models.Index(fields=['checksum']),
        ]
    
    def __str__(self):
        return self.filename

class Meter(models.Model):
    METER_TYPES = [
        ('E', 'Electricity'),
        ('G', 'Gas'),
        ('W', 'Water'),
        ('H', 'Heat'),
    ]
    
    serial_number = models.CharField(max_length=50, unique=True, db_index=True)
    mpan = models.CharField(max_length=20, db_index=True, help_text='Meter Point Administration Number', default='0000000000000')
    meter_type = models.CharField(max_length=1, choices=METER_TYPES, default='E')
    flow_file = models.ForeignKey(FlowFile, on_delete=models.CASCADE)
    created_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['serial_number']),
            models.Index(fields=['mpan']),
        ]
    
    def __str__(self):
        return f"{self.serial_number} ({self.mpan})"

class RegisterReading(models.Model):
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name='readings')
    flow_file = models.ForeignKey(FlowFile, on_delete=models.CASCADE)
    register_id = models.CharField(max_length=10)  # S, TO, A1, 01, 02, etc.
    reading_date = models.DateTimeField()
    reading_value = models.DecimalField(max_digits=12, decimal_places=3)
    reading_type = models.CharField(max_length=1, default='N')  # N, E, etc.
    measurement_method = models.CharField(max_length=1, default='T')  # T, E, etc.
    
    class Meta:
        ordering = ['reading_date']
        constraints = [
            models.UniqueConstraint(
                fields=['meter', 'register_id', 'reading_date', 'reading_value'],
                name='uniq_reading_natural_key'
            )
        ]
        indexes = [
            models.Index(fields=['meter', 'register_id']),
            models.Index(fields=['reading_date']),
        ]
    
    def __str__(self):
        return f"{self.meter.serial_number} - {self.register_id} - {self.reading_value}"