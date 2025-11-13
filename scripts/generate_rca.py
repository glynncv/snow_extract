"""
ServiceNow RCA Generation CLI Script
====================================

Command-line interface for generating Root Cause Analysis reports from ServiceNow incidents.
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
import os

# Add src directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Try to load .env file early if dotenv is available
try:
    from dotenv import load_dotenv
    # Try loading from common locations
    env_files = [
        project_root / ".env",
        project_root.parent / "snow_extract" / ".env",
        Path(r"C:\Users\cglynn\myPython\snow_extract\.env")
    ]
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=False)
            break
except ImportError:
    pass

from rca_generator import ServiceNowRCAGenerator
from rca_report_formatter import RCAReportFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description='Generate Root Cause Analysis (RCA) report for a ServiceNow incident',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate RCA report for incident INC0012345
  python scripts\\generate_rca.py INC0012345

  # Generate report in JSON format
  python scripts\\generate_rca.py INC0012345 --format json

  # Save to specific output file
  python scripts\\generate_rca.py INC0012345 --output reports\\rca_inc0012345.md

  # Use custom config file
  python scripts\\generate_rca.py INC0012345 --config config\\custom_config.json

  # Test mode (uses mock data, no ServiceNow connection required)
  python scripts\\generate_rca.py INC0012345 --test-mode
        """
    )
    
    parser.add_argument(
        'incident_number',
        help='ServiceNow incident ticket number (e.g., INC0012345)'
    )
    
    parser.add_argument(
        '--format',
        choices=['markdown', 'json', 'text'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: output/rca_<incident_number>_<timestamp>.<ext>)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (default: config/config.json)'
    )
    
    parser.add_argument(
        '--instance-url',
        type=str,
        help='ServiceNow instance URL (overrides config/env)'
    )
    
    parser.add_argument(
        '--username',
        type=str,
        help='ServiceNow username (overrides config/env)'
    )
    
    parser.add_argument(
        '--password',
        type=str,
        help='ServiceNow password (overrides config/env)'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Print report to stdout instead of saving to file'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Use mock data instead of connecting to ServiceNow (for testing)'
    )
    
    parser.add_argument(
        '--env-file',
        type=str,
        help='Path to .env file containing ServiceNow credentials (default: auto-detect)'
    )
    
    parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL certificate verification (use for corporate environments with certificate issues)'
    )
    
    args = parser.parse_args()
    
    # Load .env file if specified
    if args.env_file:
        try:
            from dotenv import load_dotenv
            env_path = Path(args.env_file)
            if env_path.exists():
                load_dotenv(env_path, override=True)
                logger.info(f"Loaded environment variables from: {env_path}")
            else:
                logger.warning(f"Specified .env file not found: {env_path}")
        except ImportError:
            logger.warning("python-dotenv not available. Install it to use --env-file option.")
    
    try:
        # Initialize RCA generator
        logger.info(f"Initializing RCA generator for incident: {args.incident_number}")
        
        generator = ServiceNowRCAGenerator(
            instance_url=args.instance_url,
            username=args.username,
            password=args.password,
            config_path=args.config,
            test_mode=args.test_mode,
            verify_ssl=not args.no_verify_ssl
        )
        
        if not args.test_mode and not generator.session:
            logger.error("Failed to connect to ServiceNow. Check your credentials.")
            logger.error("Set SNOW_INSTANCE_URL, SNOW_USERNAME, and SNOW_PASSWORD environment variables")
            logger.error("or provide --instance-url, --username, and --password arguments")
            logger.error("Use --test-mode to test without ServiceNow credentials")
            return 1
        
        # Extract incident data
        if args.test_mode:
            logger.info("Extracting mock incident data (test mode)...")
        else:
            logger.info("Extracting incident data from ServiceNow...")
        incident_data = generator.extract_incident_data(args.incident_number)
        
        # Analyze root cause
        logger.info("Analyzing root cause...")
        analysis = generator.analyze_root_cause(incident_data)
        
        # Generate report
        logger.info(f"Generating {args.format} report...")
        formatter = RCAReportFormatter()
        report_content = formatter.generate_report(incident_data, analysis, format=args.format)
        
        # Output report
        if args.no_save:
            # Print to stdout
            print(report_content)
        else:
            # Determine output path
            if args.output:
                output_path = Path(args.output)
            else:
                output_dir = project_root / "output"
                output_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                incident_clean = args.incident_number.replace('/', '_')
                
                if args.format == 'json':
                    ext = '.json'
                elif args.format == 'markdown':
                    ext = '.md'
                else:
                    ext = '.txt'
                
                output_path = output_dir / f"rca_{incident_clean}_{timestamp}{ext}"
            
            # Save report
            formatter.save_report(report_content, output_path, format=args.format)
            logger.info(f"RCA report saved to: {output_path}")
            print(f"\n✅ RCA report generated successfully!")
            print(f"📄 Report saved to: {output_path}")
        
        return 0
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error generating RCA report: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

