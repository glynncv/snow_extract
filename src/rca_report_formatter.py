"""
ServiceNow RCA Report Formatter
================================

Formats RCA analysis into executive-friendly reports in multiple formats.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class RCAReportFormatter:
    """
    Formats RCA analysis into various output formats
    """
    
    def __init__(self):
        """Initialize formatter"""
        pass
    
    def generate_report(self, incident_data: Dict[str, Any], analysis: Dict[str, Any], 
                       format: str = 'markdown') -> str:
        """
        Generate RCA report in specified format
        
        Args:
            incident_data: Incident data from RCA generator
            analysis: Analysis results from RCA generator
            format: Output format ('markdown', 'json', 'text')
            
        Returns:
            Formatted report string
        """
        if format.lower() == 'markdown':
            return self._generate_markdown(incident_data, analysis)
        elif format.lower() == 'json':
            return self._generate_json(incident_data, analysis)
        elif format.lower() == 'text':
            return self._generate_text(incident_data, analysis)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_markdown(self, incident_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate Markdown format report"""
        incident = incident_data['incident']
        timeline = incident_data['timeline']
        
        report = []
        
        # Header
        report.append("# Root Cause Analysis Report")
        report.append("")
        report.append(f"**Incident Number:** {incident.get('number', 'N/A')}")
        report.append(f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append("")
        exec_summary = self._generate_executive_summary(incident, analysis)
        report.append(exec_summary)
        report.append("")
        
        # Incident Details
        report.append("## Incident Details")
        report.append("")
        report.append(f"- **Title:** {incident.get('short_description', 'N/A')}")
        report.append(f"- **Priority:** {incident.get('priority', 'N/A')}")
        report.append(f"- **Impact:** {incident.get('impact', 'N/A')}")
        report.append(f"- **Urgency:** {incident.get('urgency', 'N/A')}")
        report.append(f"- **State:** {incident.get('state', 'N/A')}")
        report.append(f"- **Category:** {incident.get('category', 'N/A')}")
        report.append(f"- **Assignment Group:** {self._get_display_value(incident.get('assignment_group', {}))}")
        report.append(f"- **Opened:** {incident.get('opened_at', 'N/A')}")
        report.append(f"- **Resolved:** {incident.get('resolved_at') or incident.get('closed_at') or 'N/A'}")
        report.append("")
        
        # Root Cause Analysis
        report.append("## Root Cause Analysis")
        report.append("")
        report.append(f"**Identified Root Cause:**")
        report.append("")
        report.append(f"{analysis.get('root_cause', 'N/A')}")
        report.append("")
        
        # Contributing Factors
        contributing_factors = analysis.get('contributing_factors', [])
        if contributing_factors:
            report.append("**Contributing Factors:**")
            report.append("")
            for factor in contributing_factors:
                report.append(f"- {factor}")
            report.append("")
        
        # Impact Assessment
        impact = analysis.get('impact_assessment', {})
        report.append("## Impact Assessment")
        report.append("")
        report.append(f"**Business Impact:** {impact.get('business_impact', 'N/A')}")
        report.append("")
        report.append(f"**Technical Impact:** {impact.get('technical_impact', 'N/A')}")
        report.append("")
        report.append(f"**User Impact:** {impact.get('user_impact', 'N/A')}")
        report.append("")
        
        # Duration Analysis
        duration = analysis.get('duration_analysis', {})
        report.append("## Duration Analysis")
        report.append("")
        if duration.get('time_to_detection'):
            report.append(f"- **Time to Detection:** {duration['time_to_detection']}")
        if duration.get('time_to_resolution'):
            report.append(f"- **Time to Resolution:** {duration['time_to_resolution']}")
        if duration.get('total_downtime'):
            report.append(f"- **Total Downtime:** {duration['total_downtime']}")
        if duration.get('resolution_efficiency'):
            report.append(f"- **Resolution Efficiency:** {duration['resolution_efficiency']}")
        report.append("")
        
        # Priority Justification
        report.append("## Priority Classification")
        report.append("")
        report.append(analysis.get('priority_justification', 'N/A'))
        report.append("")
        
        # Timeline
        if timeline:
            report.append("## Timeline of Events")
            report.append("")
            report.append("| Timestamp | Event Type | Actor | Description |")
            report.append("|-----------|------------|-------|-------------|")
            
            for event in timeline[:20]:  # Limit to 20 most recent events
                timestamp = event.get('timestamp', '')[:19] if event.get('timestamp') else 'N/A'
                event_type = event.get('event_type', 'N/A')
                actor = event.get('actor', 'N/A')[:30]
                description = event.get('description', 'N/A')[:50]
                report.append(f"| {timestamp} | {event_type} | {actor} | {description} |")
            
            if len(timeline) > 20:
                report.append(f"| ... | ... | ... | *({len(timeline) - 20} more events)* |")
            report.append("")
        
        # Related Records
        related_incidents = incident_data.get('related_incidents', [])
        related_problems = incident_data.get('related_problems', [])
        related_changes = incident_data.get('related_changes', [])
        
        if related_incidents or related_problems or related_changes:
            report.append("## Related Records")
            report.append("")
            
            if related_incidents:
                report.append("**Related Incidents:**")
                for rel_inc in related_incidents[:5]:
                    report.append(f"- {rel_inc.get('number', 'N/A')}: {rel_inc.get('short_description', '')[:60]}")
                report.append("")
            
            if related_problems:
                report.append("**Related Problems:**")
                for rel_prob in related_problems[:5]:
                    report.append(f"- {rel_prob.get('number', 'N/A')}: {rel_prob.get('short_description', '')[:60]}")
                report.append("")
            
            if related_changes:
                report.append("**Related Changes:**")
                for rel_change in related_changes[:5]:
                    report.append(f"- {rel_change.get('number', 'N/A')}: {rel_change.get('short_description', '')[:60]}")
                report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        report.append("")
        recommendations = self._generate_recommendations(incident, analysis)
        report.append(recommendations)
        report.append("")
        
        # Footer
        report.append("---")
        report.append("")
        report.append(f"*Report generated by ServiceNow RCA Generator on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(report)
    
    def _generate_json(self, incident_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate JSON format report"""
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'incident_number': incident_data['incident'].get('number', 'N/A')
            },
            'incident': incident_data['incident'],
            'analysis': analysis,
            'timeline': incident_data.get('timeline', []),
            'related_records': {
                'incidents': incident_data.get('related_incidents', []),
                'problems': incident_data.get('related_problems', []),
                'changes': incident_data.get('related_changes', [])
            }
        }
        
        return json.dumps(report, indent=2, default=str)
    
    def _generate_text(self, incident_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate plain text format report"""
        # Convert markdown to plain text (simple version)
        markdown = self._generate_markdown(incident_data, analysis)
        # Remove markdown formatting
        text = markdown.replace('**', '').replace('#', '').replace('|', ' | ')
        return text
    
    def _generate_executive_summary(self, incident: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate executive summary (1-2 paragraphs)"""
        incident_number = incident.get('number', 'N/A')
        short_desc = incident.get('short_description', 'N/A')
        priority = incident.get('priority', 'N/A')
        
        root_cause = analysis.get('root_cause', 'Root cause analysis completed')
        impact = analysis.get('impact_assessment', {})
        duration = analysis.get('duration_analysis', {})
        
        # First paragraph: What happened
        summary = f"Incident {incident_number} ({short_desc}) occurred with priority {priority}. "
        
        # Add resolution time if available
        if duration.get('time_to_resolution'):
            summary += f"The incident was resolved in {duration['time_to_resolution']}. "
        
        # Second paragraph: Root cause and impact
        summary += f"The root cause has been identified as: {root_cause[:150]}. "
        
        business_impact = impact.get('business_impact', '')
        if business_impact:
            summary += f"{business_impact}. "
        
        user_impact = impact.get('user_impact', '')
        if user_impact:
            summary += f"{user_impact}. "
        
        # Add recommendations preview
        summary += "Recommendations for prevention have been identified and are detailed in this report."
        
        return summary
    
    def _generate_recommendations(self, incident: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate prevention recommendations"""
        recommendations = []
        
        root_cause = analysis.get('root_cause', '').lower()
        
        # Configuration-related recommendations
        if 'configuration' in root_cause or 'misconfigured' in root_cause:
            recommendations.append("**Configuration Management:** Implement automated configuration validation and change tracking to prevent misconfigurations.")
            recommendations.append("**Change Control:** Ensure all configuration changes go through proper change management process with testing.")
        
        # Hardware-related recommendations
        elif 'hardware' in root_cause or 'device' in root_cause:
            recommendations.append("**Hardware Monitoring:** Enhance hardware monitoring and proactive replacement schedules.")
            recommendations.append("**Redundancy:** Consider implementing redundant systems for critical infrastructure components.")
        
        # Software-related recommendations
        elif 'software' in root_cause or 'application' in root_cause or 'bug' in root_cause:
            recommendations.append("**Software Testing:** Improve testing procedures and quality assurance before deployment.")
            recommendations.append("**Error Handling:** Enhance application error handling and logging for faster issue detection.")
        
        # Network-related recommendations
        elif 'network' in root_cause or 'connectivity' in root_cause:
            recommendations.append("**Network Monitoring:** Strengthen network monitoring and alerting capabilities.")
            recommendations.append("**Documentation:** Maintain up-to-date network documentation and diagrams.")
        
        # Human error recommendations
        elif 'human' in root_cause or 'error' in root_cause or 'mistake' in root_cause:
            recommendations.append("**Training:** Provide additional training to reduce human error.")
            recommendations.append("**Process Automation:** Automate manual processes where possible to reduce error risk.")
            recommendations.append("**Checklists:** Implement standardized checklists for critical operations.")
        
        # Capacity-related recommendations
        elif 'capacity' in root_cause or 'resource' in root_cause:
            recommendations.append("**Capacity Planning:** Implement proactive capacity planning and monitoring.")
            recommendations.append("**Resource Scaling:** Consider auto-scaling solutions for variable workloads.")
        
        # Security-related recommendations
        elif 'security' in root_cause or 'breach' in root_cause or 'unauthorized' in root_cause:
            recommendations.append("**Security Controls:** Review and strengthen security controls and access management.")
            recommendations.append("**Security Monitoring:** Enhance security monitoring and incident response capabilities.")
        
        # General recommendations based on duration
        duration = analysis.get('duration_analysis', {})
        if duration.get('resolution_efficiency', '').startswith('Needs Improvement'):
            recommendations.append("**Response Time:** Review incident response procedures to improve resolution times.")
            recommendations.append("**Escalation:** Ensure proper escalation procedures are followed for complex incidents.")
        
        # Contributing factors recommendations
        contributing_factors = analysis.get('contributing_factors', [])
        if any('reassignment' in factor.lower() for factor in contributing_factors):
            recommendations.append("**Routing:** Improve incident routing and assignment processes to reduce reassignments.")
        
        # Default recommendations if none matched
        if not recommendations:
            recommendations.append("**Documentation:** Ensure all incidents have comprehensive documentation for future reference.")
            recommendations.append("**Post-Incident Review:** Conduct post-incident review to identify process improvements.")
            recommendations.append("**Monitoring:** Enhance monitoring and alerting to detect similar issues earlier.")
        
        return "\n".join(recommendations)
    
    def _get_display_value(self, value: Any) -> str:
        """Extract display value from ServiceNow reference field"""
        if isinstance(value, dict):
            return value.get('display_value', str(value))
        return str(value) if value else 'N/A'
    
    def save_report(self, report_content: str, output_path: Path, format: str = 'markdown'):
        """
        Save report to file
        
        Args:
            report_content: Formatted report content
            output_path: Path to save report
            format: Format of the report (determines file extension)
        """
        output_path = Path(output_path)
        
        # Add extension if not present
        if not output_path.suffix:
            if format.lower() == 'json':
                output_path = output_path.with_suffix('.json')
            elif format.lower() == 'markdown':
                output_path = output_path.with_suffix('.md')
            else:
                output_path = output_path.with_suffix('.txt')
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Report saved to: {output_path}")

