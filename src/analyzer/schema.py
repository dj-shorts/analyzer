"""
JSON Schema validation module for MVP Analyzer.

This module provides JSON schema validation for analyzer output files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    jsonschema = None
    ValidationError = Exception

logger = logging.getLogger(__name__)


class JSONSchemaValidator:
    """JSON schema validator for analyzer results."""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize validator with schema path."""
        self.schema_path = schema_path or self._get_default_schema_path()
        self.schema = self._load_schema()
    
    def _get_default_schema_path(self) -> Path:
        """Get default schema path."""
        return Path(__file__).parent.parent.parent / "schemas" / "analysis-result.json"
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        
        with open(self.schema_path, 'r') as f:
            return json.load(f)
    
    def validate_result(self, result: Dict[str, Any]) -> bool:
        """
        Validate analyzer result against schema.
        
        Args:
            result: Analyzer result dictionary
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If validation fails and jsonschema is available
        """
        if jsonschema is None:
            logger.warning("jsonschema not available, skipping validation")
            return True
        
        try:
            validate(instance=result, schema=self.schema)
            logger.debug("JSON validation successful")
            return True
        except ValidationError as e:
            logger.error(f"JSON validation failed: {e}")
            raise
    
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate JSON file against schema.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            True if valid, False otherwise
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                result = json.load(f)
            
            return self.validate_result(result)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON file {file_path}: {e}")
            return False
        except ValidationError as e:
            logger.error(f"Schema validation failed for {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating {file_path}: {e}")
            return False
    
    def get_validation_errors(self, result: Dict[str, Any]) -> List[str]:
        """
        Get detailed validation errors.
        
        Args:
            result: Analyzer result dictionary
            
        Returns:
            List of validation error messages
        """
        if jsonschema is None:
            return ["jsonschema not available"]
        
        errors = []
        try:
            validate(instance=result, schema=self.schema)
        except ValidationError as e:
            errors.append(str(e))
            # Get additional error details
            for error in e.context:
                errors.append(f"  - {error.message}")
        
        return errors
    
    def validate_cli_output(self, json_path: Path, csv_path: Path) -> bool:
        """
        Validate both JSON and CSV output files.
        
        Args:
            json_path: Path to JSON output file
            csv_path: Path to CSV output file
            
        Returns:
            True if both files are valid
        """
        logger.info(f"Validating output files: {json_path}, {csv_path}")
        
        # Validate JSON
        json_valid = self.validate_file(json_path)
        if not json_valid:
            logger.error("JSON validation failed")
            return False
        
        # Validate CSV structure
        csv_valid = self._validate_csv_structure(csv_path)
        if not csv_valid:
            logger.error("CSV validation failed")
            return False
        
        logger.info("All output files validated successfully")
        return True
    
    def _validate_csv_structure(self, csv_path: Path) -> bool:
        """Validate CSV file structure."""
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return False
        
        try:
            import csv
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                
                # Check required fields
                required_fields = [
                    'clip_id', 'start', 'end', 'center', 'score', 
                    'seed_based', 'aligned', 'length'
                ]
                
                if not reader.fieldnames:
                    logger.error("CSV file has no headers")
                    return False
                
                missing_fields = set(required_fields) - set(reader.fieldnames)
                if missing_fields:
                    logger.error(f"CSV missing required fields: {missing_fields}")
                    return False
                
                # Validate data types
                rows = list(reader)
                for i, row in enumerate(rows):
                    try:
                        int(row['clip_id'])
                        float(row['start'])
                        float(row['end'])
                        float(row['center'])
                        float(row['score'])
                        row['seed_based'].lower() in ['true', 'false']
                        row['aligned'].lower() in ['true', 'false']
                        float(row['length'])
                    except (ValueError, KeyError) as e:
                        logger.error(f"CSV row {i+1} validation error: {e}")
                        return False
                
                logger.debug(f"CSV validation successful: {len(rows)} rows")
                return True
                
        except Exception as e:
            logger.error(f"CSV validation error: {e}")
            return False


def validate_analysis_result(result: Dict[str, Any], schema_path: Optional[Path] = None) -> bool:
    """
    Convenience function to validate analysis result.
    
    Args:
        result: Analyzer result dictionary
        schema_path: Optional path to schema file
        
    Returns:
        True if valid, False otherwise
    """
    validator = JSONSchemaValidator(schema_path)
    try:
        return validator.validate_result(result)
    except ValidationError:
        return False


def validate_output_files(json_path: Path, csv_path: Path, schema_path: Optional[Path] = None) -> bool:
    """
    Convenience function to validate output files.
    
    Args:
        json_path: Path to JSON output file
        csv_path: Path to CSV output file
        schema_path: Optional path to schema file
        
    Returns:
        True if both files are valid
    """
    validator = JSONSchemaValidator(schema_path)
    return validator.validate_cli_output(json_path, csv_path)


if __name__ == "__main__":
    """CLI for JSON schema validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate analyzer output files")
    parser.add_argument("json_file", type=Path, help="JSON file to validate")
    parser.add_argument("--csv", type=Path, help="CSV file to validate")
    parser.add_argument("--schema", type=Path, help="Schema file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    validator = JSONSchemaValidator(args.schema)
    
    if args.csv:
        success = validator.validate_cli_output(args.json_file, args.csv)
    else:
        success = validator.validate_file(args.json_file)
    
    if success:
        print("✅ Validation successful")
        exit(0)
    else:
        print("❌ Validation failed")
        exit(1)
