"""
ServiceNow Data Pipeline Demo
============================

This script demonstrates the complete ServiceNow data extraction and processing pipeline.
It shows both API connectivity and local file processing capabilities.
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def demo_pipeline_overview():
    """
    Display an overview of the ServiceNow data pipeline capabilities
    """
    print("🔄 ServiceNow Data Extraction Pipeline Demo")
    print("=" * 50)
    print()
    
    print("📋 Pipeline Capabilities:")
    print("  ✅ ServiceNow API connectivity")
    print("  ✅ Local file processing")
    print("  ✅ ETL transformations")
    print("  ✅ PII redaction")
    print("  ✅ Multiple output formats")
    print("  ✅ Comprehensive logging")
    print()
    
    print("🔧 Available Scripts:")
    print("  • test_servicenow_api.py     - Test API connection")
    print("  • real_data_extraction.py    - Main extraction pipeline")
    print("  • servicenow_extraction_improved.py - Sample data generator")
    print()
    
    print("📊 Data Processing Features:")
    print("  • Network incident analysis")
    print("  • Priority and impact scoring")
    print("  • Resolution time calculations")
    print("  • Pattern-based categorization")
    print("  • Location parsing and standardization")
    print("  • SLA compliance tracking")
    print()
    
    print("🔒 Security Features:")
    print("  • Automatic PII redaction")
    print("  • Secure credential management")
    print("  • HTTPS-only API connections")
    print("  • Audit trail logging")
    print()

def demo_configuration():
    """
    Show configuration options
    """
    print("⚙️  Configuration Options:")
    print("-" * 30)
    print()
    
    print("🔑 Environment Variables (.env file):")
    print("  SNOW_INSTANCE_URL=https://your-instance.service-now.com")
    print("  SNOW_USERNAME=your_username")
    print("  SNOW_PASSWORD=your_password")
    print()
    
    print("📋 ServiceNow Query Filters:")
    print("  • Network incidents: assignment_groupLIKEnetwork")
    print("  • High priority: priority<=2")
    print("  • Recent incidents: opened_at>=javascript:gs.daysAgoStart(30)")
    print()
    
    print("🎯 ETL Transformations:")
    print("  • isActive: Boolean for active incidents")
    print("  • isHighImpact: Priority/impact analysis")
    print("  • patternCategory: Description-based categorization")
    print("  • resolutionTimeHrs: Time to resolution")
    print("  • slaBreach: SLA compliance status")
    print("  • locationParsed: Structured location data")
    print("  • priorityScore: Numerical priority scoring")
    print()

def demo_usage_examples():
    """
    Show usage examples
    """
    print("💡 Usage Examples:")
    print("-" * 20)
    print()
    
    print("🌐 API Extraction:")
    print("  python scripts\\real_data_extraction.py --api --sample-size 100")
    print("  python scripts\\real_data_extraction.py --api --config config\\custom.json")
    print()
    
    print("📁 File Processing:")
    print("  python scripts\\real_data_extraction.py --file data\\raw\\incidents.csv")
    print("  python scripts\\real_data_extraction.py --sample-size 50")
    print()
    
    print("🧪 Testing:")
    print("  python scripts\\test_servicenow_api.py")
    print("  python scripts\\servicenow_extraction_improved.py")
    print()

def demo_file_structure():
    """
    Show the project file structure
    """
    print("📁 Project Structure:")
    print("-" * 20)
    print()
    
    structure = """
    snow_extract/
    ├── 📂 src/                     # Core modules
    │   ├── 🔄 network_incident_etl.py    # ETL transformations
    │   ├── 🔒 redact5.py                 # PII redaction
    │   └── ⚙️  config_manager.py          # Configuration
    ├── 📂 scripts/                 # Executable scripts
    │   ├── 🚀 real_data_extraction.py    # Main pipeline
    │   ├── 🧪 test_servicenow_api.py    # API testing
    │   └── 📊 servicenow_extraction_improved.py # Sample generator
    ├── 📂 data/                    # Data storage
    │   ├── 📥 raw/                # Original data
    │   ├── 🔄 processed/          # Transformed data
    │   └── 🔒 redacted/           # PII-safe data
    ├── 📂 config/                  # Configuration files
    ├── 📂 logs/                    # Application logs
    └── 📂 output/                  # Final results
    """
    
    print(structure)

def check_dependencies():
    """
    Check if required dependencies are installed
    """
    print("🔍 Dependency Check:")
    print("-" * 20)
    
    required_packages = [
        'pandas', 'numpy', 'requests', 'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("   Run: pip install -r requirements.txt")
    else:
        print("\n✅ All dependencies installed!")
    
    print()

def demo_sample_data():
    """
    Show sample data structure
    """
    print("📊 Sample Data Structure:")
    print("-" * 25)
    print()
    
    print("🔗 ServiceNow API Fields:")
    print("  • number: Incident number (INC0010001)")
    print("  • short_description: Brief description")
    print("  • priority: Priority level (1-5)")
    print("  • state: Incident state (Active, Resolved, etc.)")
    print("  • assignment_group: Assigned team")
    print("  • opened_at: Creation timestamp")
    print("  • resolved_at: Resolution timestamp")
    print("  • caller_id: Reporting user")
    print("  • location: Geographic location")
    print("  • cmdb_ci: Configuration item")
    print()
    
    print("🔄 ETL Enhanced Fields:")
    print("  • isActive: Boolean (True/False)")
    print("  • isHighImpact: Boolean (True/False)")
    print("  • patternCategory: String (Network, Server, etc.)")
    print("  • resolutionTimeHrs: Float (hours)")
    print("  • slaBreach: Boolean (True/False)")
    print("  • locationParsed: Dict (structured location)")
    print("  • priorityScore: Integer (1-10)")
    print()

def main():
    """
    Main demo function
    """
    print("🎉 Welcome to the ServiceNow Data Pipeline!")
    print("=" * 50)
    print()
    
    # Run all demo sections
    demo_pipeline_overview()
    print()
    
    demo_configuration()
    print()
    
    demo_usage_examples()
    print()
    
    demo_file_structure()
    print()
    
    check_dependencies()
    print()
    
    demo_sample_data()
    print()
    
    print("🚀 Next Steps:")
    print("-" * 15)
    print("1. Configure ServiceNow credentials in .env file")
    print("2. Test API connection: python scripts\\test_servicenow_api.py")
    print("3. Run sample extraction: python scripts\\real_data_extraction.py --sample-size 10")
    print("4. Process real data: python scripts\\real_data_extraction.py --api --sample-size 100")
    print()
    print("📚 Documentation: See README.md for detailed instructions")
    print("🐛 Issues: Check logs/ directory for troubleshooting")
    print()
    print("Happy data extracting! 🎯")

if __name__ == "__main__":
    main()
