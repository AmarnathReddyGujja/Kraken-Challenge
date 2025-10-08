from django.core.management.base import BaseCommand, CommandError
import os
import logging
from meter_readings.universal_parser import UniversalParser

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import data files (UFF, CSV, JSON, XML, TXT) with duplicate prevention'
    
    def add_arguments(self, parser):
        parser.add_argument('file_paths', nargs='+', type=str, help='Path(s) to data file(s)')
    
    def handle(self, *args, **options):
        parser = UniversalParser()
        total_files = len(options['file_paths'])
        successful_imports = 0
        skipped_files = 0
        errors = 0
        
        logger.info(f"Starting import of {total_files} file(s)")
        
        for file_path in options['file_paths']:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                raise CommandError(f"File does not exist: {file_path}")
            
            self.stdout.write(f"Processing file: {file_path}")
            logger.info(f"Processing file: {file_path}")
            
            try:
                flow_file, stats = parser.parse_file(file_path)
                successful_imports += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully imported {file_path}\n"
                        f"Records processed: {flow_file.record_count}\n"
                        f"Meters created: {stats['meters_created']}\n"
                        f"Readings created: {stats['readings_created']}\n"
                        f"Duplicates skipped: {stats['duplicates_skipped']}"
                    )
                )
                logger.info(f"Successfully imported {file_path}: {stats}")
            except ValueError as e:
                skipped_files += 1
                self.stdout.write(self.style.WARNING(f"Skipping {file_path}: {str(e)}"))
                logger.warning(f"Skipping {file_path}: {str(e)}")
            except Exception as e:
                errors += 1
                logger.error(f"Error processing {file_path}: {str(e)}")
                raise CommandError(f"Error processing {file_path}: {str(e)}")
        
        # Summary
        logger.info(f"Import completed: {successful_imports} successful, {skipped_files} skipped, {errors} errors")
        self.stdout.write(
            self.style.SUCCESS(
                f"\nImport Summary:\n"
                f"Total files: {total_files}\n"
                f"Successful: {successful_imports}\n"
                f"Skipped: {skipped_files}\n"
                f"Errors: {errors}"
            )
        )