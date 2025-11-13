"""
ServiceNow Root Cause Analysis (RCA) Generator
=============================================

Generates comprehensive RCA reports from ServiceNow incident data.
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from requests.auth import HTTPBasicAuth
import os
import json
from pathlib import Path

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    URLLIB3_AVAILABLE = True
except ImportError:
    URLLIB3_AVAILABLE = False

logger = logging.getLogger(__name__)


class ServiceNowRCAGenerator:
    """
    Generates Root Cause Analysis reports from ServiceNow incidents
    """
    
    def __init__(self, instance_url: str = None, username: str = None, password: str = None, config_path: str = None, test_mode: bool = False, verify_ssl: bool = True):
        """
        Initialize RCA Generator
        
        Args:
            instance_url: ServiceNow instance URL
            username: ServiceNow username
            password: ServiceNow password
            config_path: Path to configuration file
            test_mode: If True, use mock data instead of connecting to ServiceNow
            verify_ssl: If False, disable SSL certificate verification (not recommended for production)
        """
        # Load .env file if available
        self._load_env_file()
        
        # Load configuration
        if config_path:
            self.config = self._load_config(config_path)
        else:
            script_dir = Path(__file__).parent
            project_root = script_dir.parent
            config_file = project_root / "config" / "config.json"
            self.config = self._load_config(config_file) if config_file.exists() else {}
        
        self.test_mode = test_mode
        self.verify_ssl = verify_ssl
        
        # Disable SSL warnings if verification is disabled
        if not verify_ssl and URLLIB3_AVAILABLE:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL certificate verification is disabled. This is not recommended for production use.")
        
        # Get credentials from config or environment
        self.instance_url = instance_url or self.config.get('servicenow', {}).get('instance_url') or os.getenv('SNOW_INSTANCE_URL', '')
        self.username = username or self.config.get('servicenow', {}).get('username') or os.getenv('SNOW_USERNAME', '')
        self.password = password or self.config.get('servicenow', {}).get('password') or os.getenv('SNOW_PASSWORD', '')
        
        # Initialize session
        self.session = None
        self.auth = None
        
        if not test_mode and self.instance_url and self.username and self.password:
            self._connect_to_servicenow()
        elif test_mode:
            logger.info("Running in test mode - using mock data")
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        if not DOTENV_AVAILABLE:
            return
        
        # Try loading .env from multiple locations
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        
        # Try current project directory
        env_files = [
            project_root / ".env",
            project_root.parent / "snow_extract" / ".env",  # Parent directory
            project_root.parent / ".env",  # Parent root
            Path.home() / "myPython" / "snow_extract" / ".env"  # Absolute path fallback
        ]
        
        for env_file in env_files:
            if env_file.exists():
                try:
                    load_dotenv(env_file, override=False)  # Don't override existing env vars
                    logger.info(f"Loaded environment variables from: {env_file}")
                    return
                except Exception as e:
                    logger.warning(f"Could not load .env from {env_file}: {e}")
    
    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration from JSON file"""
        try:
            if isinstance(config_path, str):
                config_path = Path(config_path)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
        return {}
    
    def _connect_to_servicenow(self):
        """Establish connection to ServiceNow API"""
        try:
            self.auth = HTTPBasicAuth(self.username, self.password)
            self.session = requests.Session()
            self.session.auth = self.auth
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            
            # Test connection
            test_url = f"{self.instance_url}/api/now/table/incident"
            timeout = self.config.get('servicenow', {}).get('timeout', 30)
            
            response = self.session.get(test_url, params={'sysparm_limit': 1}, timeout=timeout, verify=self.verify_ssl)
            response.raise_for_status()
            
            logger.info("Successfully connected to ServiceNow API")
        except Exception as e:
            logger.error(f"Failed to connect to ServiceNow: {e}")
            self.session = None
            self.auth = None
    
    def extract_incident_data(self, incident_number: str) -> Dict[str, Any]:
        """
        Extract comprehensive incident data from ServiceNow
        
        Args:
            incident_number: ServiceNow incident ticket number (e.g., 'INC0012345')
            
        Returns:
            Dictionary containing incident data, timeline, and related records
        """
        if self.test_mode:
            logger.info(f"Using mock data for incident: {incident_number}")
            return self._generate_mock_incident_data(incident_number)
        
        if not self.session:
            raise ConnectionError("Not connected to ServiceNow. Check credentials and connection. Use --test-mode for testing without credentials.")
        
        logger.info(f"Extracting data for incident: {incident_number}")
        
        incident_data = {
            'incident': {},
            'timeline': [],
            'related_incidents': [],
            'related_problems': [],
            'related_changes': [],
            'work_notes': [],
            'comments': []
        }
        
        try:
            # Extract main incident record
            incident_data['incident'] = self._get_incident(incident_number)
            
            if not incident_data['incident']:
                raise ValueError(f"Incident {incident_number} not found")
            
            sys_id = incident_data['incident'].get('sys_id')
            
            # Extract timeline events
            incident_data['timeline'] = self._build_timeline(sys_id, incident_data['incident'])
            
            # Extract work notes and comments
            incident_data['work_notes'] = self._get_work_notes(sys_id)
            incident_data['comments'] = self._get_comments(sys_id)
            
            # Extract related records
            incident_data['related_incidents'] = self._get_related_incidents(sys_id)
            incident_data['related_problems'] = self._get_related_problems(sys_id)
            incident_data['related_changes'] = self._get_related_changes(sys_id)
            
            logger.info(f"Successfully extracted data for incident {incident_number}")
            return incident_data
            
        except Exception as e:
            logger.error(f"Error extracting incident data: {e}")
            raise
    
    def _get_incident(self, incident_number: str) -> Dict[str, Any]:
        """Get incident record by number"""
        try:
            url = f"{self.instance_url}/api/now/table/incident"
            params = {
                'sysparm_query': f'number={incident_number}',
                'sysparm_fields': 'sys_id,number,short_description,description,priority,impact,urgency,state,'
                                 'assignment_group,assigned_to,opened_at,resolved_at,closed_at,'
                                 'caller_id,location,cmdb_ci,category,subcategory,contact_type,'
                                 'reassignment_count,close_code,close_notes,resolution_code,resolution_notes'
            }
            
            response = self.session.get(url, params=params, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            incidents = data.get('result', [])
            
            if incidents:
                return incidents[0]
            return {}
            
        except Exception as e:
            logger.error(f"Error getting incident: {e}")
            return {}
    
    def _build_timeline(self, sys_id: str, incident: Dict) -> List[Dict[str, Any]]:
        """Build chronological timeline of incident events"""
        timeline = []
        
        # Add incident creation
        if incident.get('opened_at'):
            # Handle caller_id field - can be dict or string
            caller_id = incident.get('caller_id', {})
            if isinstance(caller_id, dict):
                actor = caller_id.get('display_value', 'Unknown')
            elif isinstance(caller_id, str):
                actor = caller_id
            else:
                actor = 'Unknown'
            
            timeline.append({
                'timestamp': incident['opened_at'],
                'event_type': 'Incident Created',
                'actor': actor,
                'description': f"Incident {incident.get('number')} created",
                'details': incident.get('short_description', '')
            })
        
        # Get sys_journal_field entries (audit trail)
        try:
            url = f"{self.instance_url}/api/now/table/sys_journal_field"
            params = {
                'sysparm_query': f'name=incident^element_id={sys_id}',
                'sysparm_fields': 'sys_created_on,name,value,element_id,element',
                'sysparm_order_by': 'sys_created_on'
            }
            
            response = self.session.get(url, params=params, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            journal_entries = response.json().get('result', [])
            
            for entry in journal_entries:
                # Handle element field - can be dict or string
                element = entry.get('element', {})
                if isinstance(element, dict):
                    actor = element.get('display_value', 'System')
                elif isinstance(element, str):
                    actor = element
                else:
                    actor = 'System'
                
                timeline.append({
                    'timestamp': entry.get('sys_created_on', ''),
                    'event_type': 'Journal Entry',
                    'actor': actor,
                    'description': entry.get('value', '')[:200] if entry.get('value') else '',  # Truncate long entries
                    'details': entry.get('name', '')
                })
        
        except Exception as e:
            logger.warning(f"Could not retrieve journal entries: {e}")
        
        # Add resolution if available
        if incident.get('resolved_at'):
            # Handle assigned_to field - can be dict or string
            assigned_to = incident.get('assigned_to', {})
            if isinstance(assigned_to, dict):
                actor = assigned_to.get('display_value', 'Unknown')
            elif isinstance(assigned_to, str):
                actor = assigned_to
            else:
                actor = 'Unknown'
            
            timeline.append({
                'timestamp': incident['resolved_at'],
                'event_type': 'Incident Resolved',
                'actor': actor,
                'description': f"Incident resolved",
                'details': incident.get('resolution_notes', incident.get('close_notes', ''))
            })
        
        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x.get('timestamp', ''))
        
        return timeline
    
    def _get_work_notes(self, sys_id: str) -> List[Dict[str, Any]]:
        """Get work notes for the incident"""
        try:
            url = f"{self.instance_url}/api/now/table/sys_journal_field"
            params = {
                'sysparm_query': f'name=incident^element_id={sys_id}^name=work_notes',
                'sysparm_fields': 'sys_created_on,value,element',
                'sysparm_order_by': 'sys_created_on'
            }
            
            response = self.session.get(url, params=params, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            notes = response.json().get('result', [])
            result = []
            for note in notes:
                # Handle element field - can be dict or string
                element = note.get('element', {})
                if isinstance(element, dict):
                    author = element.get('display_value', 'Unknown')
                elif isinstance(element, str):
                    author = element
                else:
                    author = 'Unknown'
                
                result.append({
                    'timestamp': note.get('sys_created_on', ''),
                    'author': author,
                    'note': note.get('value', '')
                })
            return result
            
        except Exception as e:
            logger.warning(f"Could not retrieve work notes: {e}")
            return []
    
    def _get_comments(self, sys_id: str) -> List[Dict[str, Any]]:
        """Get comments for the incident"""
        try:
            url = f"{self.instance_url}/api/now/table/sys_journal_field"
            params = {
                'sysparm_query': f'name=incident^element_id={sys_id}^name=comments',
                'sysparm_fields': 'sys_created_on,value,element',
                'sysparm_order_by': 'sys_created_on'
            }
            
            response = self.session.get(url, params=params, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            comments = response.json().get('result', [])
            result = []
            for comment in comments:
                # Handle element field - can be dict or string
                element = comment.get('element', {})
                if isinstance(element, dict):
                    author = element.get('display_value', 'Unknown')
                elif isinstance(element, str):
                    author = element
                else:
                    author = 'Unknown'
                
                result.append({
                    'timestamp': comment.get('sys_created_on', ''),
                    'author': author,
                    'comment': comment.get('value', '')
                })
            return result
            
        except Exception as e:
            logger.warning(f"Could not retrieve comments: {e}")
            return []
    
    def _get_related_incidents(self, sys_id: str) -> List[Dict[str, Any]]:
        """Get related incidents"""
        try:
            url = f"{self.instance_url}/api/now/table/incident"
            params = {
                'sysparm_query': f'parent={sys_id}',
                'sysparm_fields': 'number,short_description,priority,state,opened_at,resolved_at'
            }
            
            response = self.session.get(url, params=params, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            return response.json().get('result', [])
            
        except Exception as e:
            logger.warning(f"Could not retrieve related incidents: {e}")
            return []
    
    def _get_related_problems(self, sys_id: str) -> List[Dict[str, Any]]:
        """Get related problem records"""
        try:
            url = f"{self.instance_url}/api/now/table/problem"
            params = {
                'sysparm_query': f'incidentsLIKE{sys_id}',
                'sysparm_fields': 'number,short_description,priority,state,opened_at,resolved_at'
            }
            
            response = self.session.get(url, params=params, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            return response.json().get('result', [])
            
        except Exception as e:
            logger.warning(f"Could not retrieve related problems: {e}")
            return []
    
    def _get_related_changes(self, sys_id: str) -> List[Dict[str, Any]]:
        """Get related change requests"""
        try:
            url = f"{self.instance_url}/api/now/table/change_request"
            params = {
                'sysparm_query': f'incidentsLIKE{sys_id}',
                'sysparm_fields': 'number,short_description,priority,state,opened_at,closed_at'
            }
            
            response = self.session.get(url, params=params, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            return response.json().get('result', [])
            
        except Exception as e:
            logger.warning(f"Could not retrieve related changes: {e}")
            return []
    
    def analyze_root_cause(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze incident data to identify root cause
        
        Args:
            incident_data: Dictionary containing incident data from extract_incident_data()
            
        Returns:
            Dictionary containing root cause analysis
        """
        incident = incident_data['incident']
        work_notes = incident_data['work_notes']
        comments = incident_data['comments']
        timeline = incident_data['timeline']
        related_problems = incident_data['related_problems']
        
        analysis = {
            'root_cause': self._identify_root_cause(incident, work_notes, comments, related_problems),
            'contributing_factors': self._identify_contributing_factors(incident, work_notes, timeline),
            'impact_assessment': self._assess_impact(incident, incident_data),
            'duration_analysis': self._analyze_duration(incident, timeline),
            'priority_justification': self._justify_priority(incident)
        }
        
        return analysis
    
    def _identify_root_cause(self, incident: Dict, work_notes: List, comments: List, related_problems: List) -> str:
        """Identify root cause from incident data"""
        # Check resolution notes first
        resolution_notes = incident.get('resolution_notes', '') or incident.get('close_notes', '')
        
        if resolution_notes:
            # Look for common root cause indicators
            root_cause_keywords = {
                'configuration': ['misconfigured', 'configuration error', 'config issue', 'wrong setting'],
                'hardware': ['hardware failure', 'device failed', 'equipment failure', 'hardware issue'],
                'software': ['software bug', 'application error', 'code issue', 'software failure'],
                'network': ['network outage', 'connectivity issue', 'routing problem', 'network failure'],
                'human_error': ['user error', 'mistake', 'accidental', 'human error'],
                'capacity': ['capacity exceeded', 'resource exhaustion', 'out of memory', 'disk full'],
                'security': ['security breach', 'unauthorized access', 'malware', 'attack']
            }
            
            resolution_lower = resolution_notes.lower()
            for cause_type, keywords in root_cause_keywords.items():
                if any(keyword in resolution_lower for keyword in keywords):
                    return f"{cause_type.replace('_', ' ').title()}: {resolution_notes[:200]}"
        
        # Check work notes for root cause indicators
        all_notes = ' '.join([note.get('note', '') for note in work_notes])
        all_comments = ' '.join([comment.get('comment', '') for comment in comments])
        combined_text = (all_notes + ' ' + all_comments).lower()
        
        # Look for root cause patterns in notes
        if 'root cause' in combined_text:
            # Extract sentence containing "root cause"
            import re
            matches = re.findall(r'[^.]*root cause[^.]*\.', combined_text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        # Check related problems for root cause
        if related_problems:
            problem_desc = related_problems[0].get('short_description', '')
            if problem_desc:
                return f"Related Problem: {problem_desc}"
        
        # Default: extract from description
        description = incident.get('description', '') or incident.get('short_description', '')
        if description:
            return f"Based on incident description: {description[:200]}"
        
        return "Root cause not clearly identified from available data. Manual review recommended."
    
    def _identify_contributing_factors(self, incident: Dict, work_notes: List, timeline: List) -> List[str]:
        """Identify contributing factors"""
        factors = []
        
        # Check reassignment count
        reassignment_count = incident.get('reassignment_count', 0)
        # Convert to int if it's a string
        try:
            if isinstance(reassignment_count, str):
                reassignment_count = int(reassignment_count) if reassignment_count else 0
            elif reassignment_count is None:
                reassignment_count = 0
            else:
                reassignment_count = int(reassignment_count)
        except (ValueError, TypeError):
            reassignment_count = 0
        
        if reassignment_count > 2:
            factors.append(f"Incident was reassigned {reassignment_count} times, indicating initial misrouting or complexity")
        
        # Check timeline for delays
        if len(timeline) > 0 and len(timeline) > 1:
            first_event = timeline[0]
            last_event = timeline[-1]
            
            try:
                first_time = datetime.fromisoformat(first_event['timestamp'].replace('Z', '+00:00'))
                last_time = datetime.fromisoformat(last_event['timestamp'].replace('Z', '+00:00'))
                duration = (last_time - first_time).total_seconds() / 3600
                
                if duration > 24:
                    factors.append(f"Extended resolution time ({duration:.1f} hours) suggests complexity or resource constraints")
            except:
                pass
        
        # Check for multiple work notes indicating investigation complexity
        if len(work_notes) > 5:
            factors.append("Multiple investigation notes indicate complex troubleshooting process")
        
        return factors
    
    def _assess_impact(self, incident: Dict, incident_data: Dict) -> Dict[str, Any]:
        """Assess business, technical, and user impact"""
        impact = {
            'business_impact': '',
            'technical_impact': '',
            'user_impact': '',
            'affected_users_estimate': 0
        }
        
        # Business impact based on priority and impact fields
        priority = incident.get('priority', '')
        impact_level = incident.get('impact', '')
        urgency = incident.get('urgency', '')
        
        if '1' in str(priority) or 'critical' in str(impact_level).lower():
            impact['business_impact'] = "Critical business impact - Service disruption affecting core operations"
            impact['affected_users_estimate'] = 500  # High estimate for critical
        elif '2' in str(priority) or 'high' in str(impact_level).lower():
            impact['business_impact'] = "High business impact - Significant service degradation"
            impact['affected_users_estimate'] = 200
        elif '3' in str(priority) or 'medium' in str(impact_level).lower():
            impact['business_impact'] = "Moderate business impact - Limited service disruption"
            impact['affected_users_estimate'] = 50
        else:
            impact['business_impact'] = "Low business impact - Minimal service disruption"
            impact['affected_users_estimate'] = 10
        
        # Technical impact from description and CI
        ci = incident.get('cmdb_ci', {})
        if isinstance(ci, dict):
            ci_name = ci.get('display_value', '')
        elif isinstance(ci, str):
            ci_name = ci
        else:
            ci_name = str(ci) if ci else 'Unknown'
        category = incident.get('category', '')
        
        impact['technical_impact'] = f"Affected CI: {ci_name}. Category: {category}"
        
        # User impact from description
        description = incident.get('description', '') or incident.get('short_description', '')
        if 'user' in description.lower() or 'users' in description.lower():
            # Try to extract number
            import re
            user_matches = re.findall(r'(\d+)\s*(?:users?|people)', description.lower())
            if user_matches:
                impact['affected_users_estimate'] = int(user_matches[0])
        
        impact['user_impact'] = f"Estimated {impact['affected_users_estimate']} users affected"
        
        return impact
    
    def _analyze_duration(self, incident: Dict, timeline: List) -> Dict[str, Any]:
        """Analyze incident duration and timing"""
        duration_analysis = {
            'time_to_detection': None,
            'time_to_resolution': None,
            'total_downtime': None,
            'resolution_efficiency': ''
        }
        
        opened_at = incident.get('opened_at')
        resolved_at = incident.get('resolved_at') or incident.get('closed_at')
        
        if opened_at and resolved_at:
            try:
                opened = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                resolved = datetime.fromisoformat(resolved_at.replace('Z', '+00:00'))
                
                total_duration = (resolved - opened).total_seconds() / 3600
                duration_analysis['time_to_resolution'] = f"{total_duration:.1f} hours"
                duration_analysis['total_downtime'] = f"{total_duration:.1f} hours"
                
                # Time to detection (first event to first work note or assignment)
                if len(timeline) > 1:
                    first_event_time = datetime.fromisoformat(timeline[0]['timestamp'].replace('Z', '+00:00'))
                    # Find first work note or assignment
                    for event in timeline:
                        if 'assignment' in event.get('event_type', '').lower() or 'work' in event.get('event_type', '').lower():
                            detection_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                            detection_duration = (detection_time - first_event_time).total_seconds() / 3600
                            duration_analysis['time_to_detection'] = f"{detection_duration:.1f} hours"
                            break
                
                # Resolution efficiency
                if total_duration < 4:
                    duration_analysis['resolution_efficiency'] = "Excellent - Resolved within 4 hours"
                elif total_duration < 24:
                    duration_analysis['resolution_efficiency'] = "Good - Resolved within 24 hours"
                elif total_duration < 72:
                    duration_analysis['resolution_efficiency'] = "Acceptable - Resolved within 72 hours"
                else:
                    duration_analysis['resolution_efficiency'] = "Needs Improvement - Resolution exceeded 72 hours"
                    
            except Exception as e:
                logger.warning(f"Error analyzing duration: {e}")
        
        return duration_analysis
    
    def _justify_priority(self, incident: Dict) -> str:
        """Justify priority classification"""
        priority = incident.get('priority', '')
        impact = incident.get('impact', '')
        urgency = incident.get('urgency', '')
        
        justification = f"Priority: {priority}"
        
        if impact:
            justification += f", Impact: {impact}"
        if urgency:
            justification += f", Urgency: {urgency}"
        
        # Add context
        if '1' in str(priority) or 'critical' in str(impact).lower():
            justification += " - Critical priority justified by high business impact and urgency"
        elif '2' in str(priority) or 'high' in str(impact).lower():
            justification += " - High priority due to significant service impact"
        else:
            justification += " - Standard priority classification"
        
        return justification
    
    def _generate_mock_incident_data(self, incident_number: str) -> Dict[str, Any]:
        """
        Generate mock incident data for testing without ServiceNow connection
        
        Args:
            incident_number: Incident ticket number
            
        Returns:
            Dictionary containing mock incident data
        """
        opened_time = datetime.now() - timedelta(hours=6)
        resolved_time = datetime.now() - timedelta(hours=2)
        
        mock_data = {
            'incident': {
                'sys_id': 'mock_sys_id_12345',
                'number': incident_number,
                'short_description': 'Network connectivity issue affecting multiple users',
                'description': 'Users in the London office reported inability to access network resources. Initial investigation revealed firewall misconfiguration blocking legitimate traffic.',
                'priority': '2 - High',
                'impact': '2 - High',
                'urgency': '1 - Critical',
                'state': '6 - Resolved',
                'category': 'Network',
                'subcategory': 'Connectivity',
                'assignment_group': {'display_value': 'Global Network Services'},
                'assigned_to': {'display_value': 'Network Admin, John'},
                'opened_at': opened_time.strftime('%Y-%m-%d %H:%M:%S'),
                'resolved_at': resolved_time.strftime('%Y-%m-%d %H:%M:%S'),
                'closed_at': resolved_time.strftime('%Y-%m-%d %H:%M:%S'),
                'caller_id': {'display_value': 'user@company.com'},
                'location': {'display_value': 'London Office'},
                'cmdb_ci': {'display_value': 'Core Firewall FW-LON-01'},
                'contact_type': 'Email',
                'reassignment_count': 1,
                'close_code': 'Solved (Work Around)',
                'close_notes': 'Firewall rule corrected and traffic restored',
                'resolution_code': 'Fixed',
                'resolution_notes': 'Root cause: Misconfigured firewall rule blocking HTTPS traffic. Fixed by correcting firewall rule configuration. All affected users can now access network resources.'
            },
            'timeline': [
                {
                    'timestamp': opened_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'Incident Created',
                    'actor': 'user@company.com',
                    'description': f'Incident {incident_number} created',
                    'details': 'Network connectivity issue reported'
                },
                {
                    'timestamp': (opened_time + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'Assignment',
                    'actor': 'System',
                    'description': 'Incident assigned to Global Network Services',
                    'details': 'Auto-assigned based on category'
                },
                {
                    'timestamp': (opened_time + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'Journal Entry',
                    'actor': 'Network Admin, John',
                    'description': 'Investigating firewall logs',
                    'details': 'Reviewing firewall configuration and logs'
                },
                {
                    'timestamp': (opened_time + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'Journal Entry',
                    'actor': 'Network Admin, John',
                    'description': 'Identified misconfigured firewall rule',
                    'details': 'Found incorrect firewall rule blocking HTTPS traffic'
                },
                {
                    'timestamp': resolved_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'Incident Resolved',
                    'actor': 'Network Admin, John',
                    'description': 'Firewall rule corrected and incident resolved',
                    'details': 'Fixed firewall configuration. All users can now access network resources.'
                }
            ],
            'work_notes': [
                {
                    'timestamp': (opened_time + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'author': 'Network Admin, John',
                    'note': 'Investigating firewall logs and configuration. Multiple users affected in London office.'
                },
                {
                    'timestamp': (opened_time + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S'),
                    'author': 'Network Admin, John',
                    'note': 'Root cause identified: Misconfigured firewall rule blocking HTTPS traffic. Working on fix.'
                },
                {
                    'timestamp': resolved_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'author': 'Network Admin, John',
                    'note': 'Firewall rule corrected. All affected users verified connectivity restored. Incident resolved.'
                }
            ],
            'comments': [
                {
                    'timestamp': (opened_time + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
                    'author': 'user@company.com',
                    'comment': 'Still unable to access network resources. Please prioritize.'
                }
            ],
            'related_incidents': [
                {
                    'number': 'INC0012344',
                    'short_description': 'Similar connectivity issue reported earlier',
                    'priority': '3 - Moderate',
                    'state': '6 - Resolved',
                    'opened_at': (opened_time - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'resolved_at': (opened_time - timedelta(days=1) + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
                }
            ],
            'related_problems': [
                {
                    'number': 'PRB001234',
                    'short_description': 'Firewall configuration management',
                    'priority': '2 - High',
                    'state': '3 - Work in Progress',
                    'opened_at': (opened_time - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    'resolved_at': None
                }
            ],
            'related_changes': [
                {
                    'number': 'CHG001234',
                    'short_description': 'Firewall rule update',
                    'priority': '3 - Moderate',
                    'state': '4 - Approved',
                    'opened_at': (opened_time - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
                    'closed_at': None
                }
            ]
        }
        
        return mock_data

