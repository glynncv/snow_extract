# ServiceNow Analytics Toolkit - ITSM Workflow Support

## Overview

This document outlines how the ServiceNow Analytics toolkit supports IT Service Management (ITSM) workflows based on ITIL best practices and ServiceNow platform capabilities.

---

## Table of Contents

1. [Incident Management](#1-incident-management)
2. [Problem Management](#2-problem-management)
3. [Change Management](#3-change-management)
4. [SLA Management](#4-sla-management)
5. [Service Level Management](#5-service-level-management)
6. [Knowledge Management](#6-knowledge-management)
7. [Continuous Service Improvement](#7-continuous-service-improvement)
8. [Major Incident Management](#8-major-incident-management)
9. [Reporting & Analytics](#9-reporting--analytics)
10. [Assignment & Routing Optimization](#10-assignment--routing-optimization)

---

## 1. Incident Management

### ITSM Workflow
**Objective:** Restore normal service operation as quickly as possible with minimal business impact.

**Key Activities:**
- Incident detection and recording
- Categorization and prioritization
- Investigation and diagnosis
- Resolution and recovery
- Incident closure

### Toolkit Support

#### 1.1 Incident Data Acquisition
```python
from snow_analytics import load_incidents

# Load recent incidents from ServiceNow API
df_incidents = load_incidents(
    source='api',
    limit=5000,
    query_filter='opened_atONToday@javascript:gs.beginningOfToday()@javascript:gs.endOfToday()'
)

# Or load from exported CSV for offline analysis
df_incidents = load_incidents('csv', file_path='data/incidents_export.csv')
```

**Supports:**
- Real-time incident data extraction via API
- Batch processing of incident exports
- Historical incident analysis

#### 1.2 Incident Categorization & Enrichment
```python
from snow_analytics import transform_incidents

# Apply transformations to categorize and enrich incidents
df_enriched = transform_incidents(df_incidents, transformations=[
    'normalize',      # Standardize column names
    'dates',          # Parse datetime fields
    'status',         # Add isActive, isResolved flags
    'categorization', # Auto-categorize by pattern
    'durations',      # Calculate ages and resolution times
    'impact'          # Estimate user impact
])
```

**Supports:**
- Automatic incident categorization (WiFi, VPN, DNS, etc.)
- Priority classification validation
- User impact estimation
- Status tracking (Active/Resolved/Closed)

**ITSM Benefit:** Reduces manual categorization effort, ensures consistency

#### 1.3 Incident Priority Validation
```python
from snow_analytics.analysis.quality import detect_priority_misclassification

# Identify incidents with incorrect priority
df_quality = detect_priority_misclassification(df_enriched)

# Find P1/P2 incidents that resolved too slowly
misclassified = df_quality[
    (df_quality['quality_priority_mismatch'] == True) &
    (df_quality['priority'].isin(['1 - Critical', '2 - High']))
]

print(f"Found {len(misclassified)} potentially misclassified incidents")
```

**Supports:**
- Priority vs. resolution time validation
- Impact vs. urgency alignment checks
- Escalation recommendations

**ITSM Benefit:** Ensures incidents receive appropriate attention and resources

#### 1.4 Incident Backlog Management
```python
from snow_analytics.analysis import calculate_backlog_metrics

# Analyze current incident backlog
backlog_metrics = calculate_backlog_metrics(df_enriched)

print(f"Total active incidents: {backlog_metrics['total_backlog']}")
print(f"Incidents > 1 week old: {backlog_metrics['by_age']['1week_to_1month']}")
print(f"P1/P2 backlog: {backlog_metrics['by_priority'].get('1 - Critical', 0)}")
```

**Supports:**
- Real-time backlog monitoring
- Age-based backlog analysis (< 24h, 24h-3d, 3d-1w, etc.)
- Priority-based backlog breakdown
- Trend analysis over time

**ITSM Benefit:** Enables proactive backlog management and resource planning

---

## 2. Problem Management

### ITSM Workflow
**Objective:** Prevent incidents by identifying and resolving root causes of recurring issues.

**Key Activities:**
- Problem detection (reactive & proactive)
- Problem investigation and diagnosis
- Root cause analysis
- Known error documentation
- Problem resolution

### Toolkit Support

#### 2.1 Pattern Detection & Recurring Issue Identification
```python
from snow_analytics.analysis import analyze_patterns, find_recurring_issues

# Analyze incident patterns
patterns = analyze_patterns(df_enriched)

# Find recurring issues (same category + CI)
recurring_issues = find_recurring_issues(
    df_enriched,
    min_occurrences=5  # 5+ incidents = potential problem
)

# Display recurring issues
for issue in recurring_issues:
    print(f"Recurring: {issue['category']} on {issue['ci']} - {issue['occurrences']} times")
```

**Output Example:**
```
Recurring: WiFi/Wireless on WAP-BUILDING-A-03 - 12 times
Recurring: VPN/Remote Access on VPN-GATEWAY-01 - 8 times
Recurring: DNS/Resolution on DNS-SERVER-EMEA - 7 times
```

**Supports:**
- Identification of repeat incidents
- CI-specific failure patterns
- Category-based clustering
- Temporal pattern analysis (time of day, day of week)

**ITSM Benefit:** Proactively identifies candidates for problem records

#### 2.2 Root Cause Analysis (RCA)
```python
from snow_analytics.rca import RCAGenerator, RCAReportFormatter

# Initialize RCA generator
rca_gen = RCAGenerator(
    instance_url=config.get('servicenow.instance_url'),
    username=config.get('servicenow.username'),
    password=config.get('servicenow.password')
)

# Generate RCA for a major incident or problem
incident_data = rca_gen.extract_incident_data('INC0012345')
analysis = rca_gen.analyze_root_cause(incident_data)

# Create formatted report
formatter = RCAReportFormatter()
rca_report = formatter.generate_report(
    incident_data,
    analysis,
    format='markdown'
)

# Save for problem record attachment
formatter.save_report(rca_report, 'reports/problem_prb001234_rca.md')
```

**Supports:**
- Incident timeline reconstruction
- Root cause identification from notes/descriptions
- Contributing factor analysis
- Impact assessment (business, technical, user)
- Duration analysis (time to detect, time to resolve)
- Related incident/problem/change correlation

**ITSM Benefit:** Structured RCA process, comprehensive documentation for problem records

#### 2.3 Known Error Database Support
```python
# Identify top issues for Known Error documentation
top_patterns = patterns['category_distribution']

# Sort by frequency to prioritize known error creation
for category, count in sorted(top_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"{category}: {count} incidents → Create Known Error + Workaround")
```

**Supports:**
- Prioritization of known error candidates
- Frequency-based ranking
- Impact-based ranking (by affected users)

**ITSM Benefit:** Data-driven approach to building knowledge base

---

## 3. Change Management

### ITSM Workflow
**Objective:** Ensure changes are implemented with minimal service disruption.

**Key Activities:**
- Change assessment
- Change approval
- Change implementation
- Post-implementation review

### Toolkit Support

#### 3.1 Post-Change Incident Analysis
```python
# Analyze incidents after a change window
change_date = '2025-01-15'

df_post_change = df_enriched[
    df_enriched['openedDate'] >= pd.to_datetime(change_date)
]

# Compare to baseline
print(f"Incidents 24h after change: {len(df_post_change)}")
print(f"Priority 1/2 incidents: {df_post_change['isHighImpact'].sum()}")
```

**Supports:**
- Post-implementation incident volume analysis
- Category-based impact assessment (did change affect specific services?)
- Priority distribution changes
- Mean time to resolve (MTTR) comparison

**ITSM Benefit:** Validates change success, identifies change-related issues early

#### 3.2 Change-Related Incident Correlation
```python
# Using RCA generator to link incidents to changes
incident_data = rca_gen.extract_incident_data('INC0012345')

# Check for related changes
related_changes = incident_data.get('related_changes', [])

if related_changes:
    print("Potentially related to these changes:")
    for change in related_changes:
        print(f"  {change['number']}: {change['short_description']}")
```

**Supports:**
- Incident-to-change linking
- Change impact analysis
- Failed change identification

**ITSM Benefit:** Rapid identification of problematic changes

---

## 4. SLA Management

### ITSM Workflow
**Objective:** Ensure service level agreements are met and tracked.

**Key Activities:**
- SLA definition and configuration
- SLA monitoring
- Breach prevention
- Breach reporting and analysis

### Toolkit Support

#### 4.1 Configurable SLA Rules
```yaml
# config/default_config.yaml
sla:
  rules:
    "1 - Critical": 4      # 4 hours
    "2 - High": 24         # 24 hours
    "3 - Moderate": 72     # 72 hours
    "4 - Low": 120         # 120 hours
```

**Supports:**
- Priority-based SLA thresholds
- Custom SLA rules per organization
- Easy configuration updates

#### 4.2 SLA Breach Detection & Calculation
```python
from snow_analytics.analysis import calculate_sla_metrics

# Calculate SLA performance
sla_metrics = calculate_sla_metrics(df_enriched)

print(f"Overall SLA Performance:")
print(f"  Total resolved: {sla_metrics['total_resolved']}")
print(f"  Met SLA: {sla_metrics['sla_met']} ({100 - sla_metrics['breach_rate_pct']:.1f}%)")
print(f"  Breached SLA: {sla_metrics['sla_breached']} ({sla_metrics['breach_rate_pct']:.1f}%)")

# By priority breakdown
print(f"\nSLA Performance by Priority:")
for priority, metrics in sla_metrics['by_priority'].items():
    print(f"  {priority}: {metrics['breach_rate_pct']:.1f}% breach rate")
```

**Output Example:**
```
Overall SLA Performance:
  Total resolved: 450
  Met SLA: 387 (86.0%)
  Breached SLA: 63 (14.0%)

SLA Performance by Priority:
  1 - Critical: 5.2% breach rate
  2 - High: 12.8% breach rate
  3 - Moderate: 15.3% breach rate
  4 - Low: 18.9% breach rate
```

**Supports:**
- Real-time SLA breach calculation
- Historical SLA performance tracking
- Priority-based SLA breakdown
- SLA margin calculation (how close to breach)

**ITSM Benefit:** Proactive SLA management, early breach detection

#### 4.3 SLA Breach Alerting & Reporting
```python
# Identify incidents at risk of SLA breach (active incidents close to deadline)
if 'slaMarginHrs' in df_enriched.columns:
    at_risk = df_enriched[
        (df_enriched['isActive'] == True) &
        (df_enriched['slaMarginHrs'] < 2) &  # Less than 2 hours to breach
        (df_enriched['slaMarginHrs'] > 0)     # Not yet breached
    ]

    print(f"⚠️  {len(at_risk)} incidents at risk of SLA breach within 2 hours")

    # Export for escalation
    at_risk[['number', 'short_description', 'priority', 'slaMarginHrs']].to_csv(
        'output/sla_at_risk.csv',
        index=False
    )
```

**Supports:**
- At-risk incident identification
- Breach prediction
- Escalation lists
- Management reporting

**ITSM Benefit:** Prevents SLA breaches through early warning

---

## 5. Service Level Management

### ITSM Workflow
**Objective:** Ensure IT services meet agreed-upon service levels and customer expectations.

**Key Activities:**
- Service performance monitoring
- Trend analysis
- Service improvement planning
- Customer satisfaction tracking

### Toolkit Support

#### 5.1 Resolution Time Analysis
```python
from snow_analytics.analysis import analyze_resolution_times

# Comprehensive resolution time analysis
resolution_analysis = analyze_resolution_times(
    df_enriched,
    by_priority=True,
    by_category=True
)

# Overall performance
print("Overall Resolution Performance:")
print(f"  Mean: {resolution_analysis['overall']['mean_hrs']:.1f} hours")
print(f"  Median: {resolution_analysis['overall']['median_hrs']:.1f} hours")
print(f"  90th percentile: {resolution_analysis['overall']['percentile_90_hrs']:.1f} hours")

# By priority
print("\nResolution Time by Priority:")
for priority, metrics in resolution_analysis['by_priority'].items():
    print(f"  {priority}: {metrics['mean_hrs']:.1f}h avg, {metrics['median_hrs']:.1f}h median")

# By category
print("\nResolution Time by Category:")
for category, metrics in resolution_analysis['by_category'].items():
    print(f"  {category}: {metrics['mean_hrs']:.1f}h avg ({metrics['count']} incidents)")
```

**Supports:**
- Mean Time to Resolve (MTTR) calculation
- Percentile-based analysis (50th, 90th, 95th)
- Priority-based performance
- Category-based performance
- Trend analysis over time

**ITSM Benefit:** Identifies service performance trends, improvement opportunities

#### 5.2 Service Quality Metrics
```python
# Calculate service quality score
total_incidents = len(df_enriched)
quality_issues = df_enriched['quality_issues_count'].sum()

quality_score = ((total_incidents - quality_issues) / total_incidents) * 100

print(f"Service Quality Score: {quality_score:.1f}%")
print(f"Quality issues found: {quality_issues} across {total_incidents} incidents")

# Breakdown by issue type
quality_types = {
    'Priority Mismatch': df_enriched['quality_priority_mismatch'].sum(),
    'On Hold Abuse': df_enriched['quality_on_hold_abuse'].sum(),
    'Poor Descriptions': df_enriched['quality_poor_description'].sum(),
    'Excessive Reassignments': df_enriched['quality_excessive_reassignments'].sum()
}

for issue_type, count in quality_types.items():
    if count > 0:
        print(f"  {issue_type}: {count}")
```

**ITSM Benefit:** Quantifies service quality, identifies improvement areas

---

## 6. Knowledge Management

### ITSM Workflow
**Objective:** Enable efficient incident resolution through knowledge sharing.

**Key Activities:**
- Knowledge article creation
- Knowledge base maintenance
- Knowledge article usage tracking
- Knowledge gap identification

### Toolkit Support

#### 6.1 Knowledge Gap Identification
```python
# Find high-volume issues without clear resolutions
high_volume_categories = df_enriched['patternCategory'].value_counts().head(10)

print("Top 10 Incident Categories (Candidates for KB Articles):")
for category, count in high_volume_categories.items():
    # Check if resolution times are high (indicates knowledge gap)
    category_incidents = df_enriched[df_enriched['patternCategory'] == category]
    avg_resolution = category_incidents['resolutionTimeHrs'].mean()

    print(f"  {category}: {count} incidents, avg {avg_resolution:.1f}h resolution")

    if avg_resolution > 24:
        print(f"    ⚠️  Consider creating KB article (slow resolution)")
```

**Supports:**
- High-volume incident category identification
- Resolution time-based prioritization
- Recurring issue detection for KB articles

**ITSM Benefit:** Data-driven knowledge article creation

#### 6.2 Common Issue Documentation
```python
# Identify most common short descriptions for KB article titles
from collections import Counter

# Extract common keywords from short descriptions
common_issues = Counter()

for desc in df_enriched['short_description'].dropna():
    # Simple keyword extraction (can be enhanced with NLP)
    keywords = desc.lower().split()
    common_issues.update(keywords)

print("Most Common Issue Keywords (for KB search optimization):")
for keyword, count in common_issues.most_common(20):
    if len(keyword) > 4:  # Filter short words
        print(f"  {keyword}: {count} occurrences")
```

**ITSM Benefit:** Optimizes KB article titles and tags for searchability

---

## 7. Continuous Service Improvement (CSI)

### ITSM Workflow
**Objective:** Continually improve IT service quality and efficiency.

**Key Activities:**
- Process measurement
- Gap analysis
- Improvement identification
- Implementation and monitoring

### Toolkit Support

#### 7.1 Quality Issue Detection
```python
from snow_analytics.analysis.quality import check_incident_quality

# Comprehensive quality check
df_quality = check_incident_quality(df_enriched)

# Identify improvement areas
improvement_areas = {
    'Priority Misclassification': df_quality['quality_priority_mismatch'].sum(),
    'On Hold Abuse (>72h)': df_quality['quality_on_hold_abuse'].sum(),
    'Poor Short Descriptions': df_quality['quality_poor_description'].sum(),
    'Excessive Reassignments': df_quality['quality_excessive_reassignments'].sum()
}

print("Process Improvement Opportunities:")
for area, count in improvement_areas.items():
    if count > 0:
        pct = (count / len(df_quality)) * 100
        print(f"  {area}: {count} incidents ({pct:.1f}%)")
```

**Supports:**
- Process gap identification
- Quality metric calculation
- Trend monitoring over time
- Improvement opportunity prioritization

**ITSM Benefit:** Quantifies improvement opportunities, tracks CSI initiatives

#### 7.2 Assignment & Routing Analysis
```python
from snow_analytics.analysis import analyze_reassignments

# Identify routing inefficiencies
excessive_reassignments = analyze_reassignments(df_enriched, threshold=2)

print(f"Found {len(excessive_reassignments)} incidents with >2 reassignments")

# Group by assignment group to identify routing issues
routing_analysis = excessive_reassignments.groupby('assignment_group').agg({
    'number': 'count',
    'reassignment_count': 'mean'
}).sort_values('number', ascending=False)

print("\nAssignment Groups with Routing Issues:")
print(routing_analysis.head(10))
```

**Output Example:**
```
Assignment Groups with Routing Issues:
                          number  reassignment_count
assignment_group
IT Service Desk              23                 4.2
Network Team EMEA            18                 3.8
Local IT Support             12                 3.3
```

**Supports:**
- Routing efficiency analysis
- Assignment group performance
- Incident bouncing detection
- Training needs identification

**ITSM Benefit:** Improves first-time assignment accuracy

#### 7.3 Performance Benchmarking
```python
# Compare current period vs. previous period
current_period = df_enriched[df_enriched['openedDate'] >= '2025-01-01']
previous_period = df_enriched[df_enriched['openedDate'] < '2025-01-01']

# Calculate KPIs for both periods
current_metrics = calculate_sla_metrics(current_period)
previous_metrics = calculate_sla_metrics(previous_period)

# Compare
print("Period Comparison:")
print(f"  Current SLA Breach Rate: {current_metrics['breach_rate_pct']:.1f}%")
print(f"  Previous SLA Breach Rate: {previous_metrics['breach_rate_pct']:.1f}%")

improvement = previous_metrics['breach_rate_pct'] - current_metrics['breach_rate_pct']
print(f"  Improvement: {improvement:+.1f}% {'✅' if improvement > 0 else '❌'}")
```

**ITSM Benefit:** Tracks improvement over time, validates CSI initiatives

---

## 8. Major Incident Management

### ITSM Workflow
**Objective:** Manage high-impact incidents requiring urgent attention and coordination.

**Key Activities:**
- Major incident declaration
- War room coordination
- Stakeholder communication
- Post-incident review

### Toolkit Support

#### 8.1 Major Incident Identification
```python
# Identify potential major incidents (P1 + high user impact)
major_incidents = df_enriched[
    (df_enriched['isCritical'] == True) &
    (df_enriched['userImpactEstimate'] >= 100)
]

print(f"Identified {len(major_incidents)} potential major incidents")

# Active major incidents requiring immediate attention
active_major = major_incidents[major_incidents['isActive'] == True]

if not active_major.empty:
    print(f"\n⚠️  {len(active_major)} ACTIVE MAJOR INCIDENTS:")
    for _, inc in active_major.iterrows():
        print(f"  {inc['number']}: {inc['short_description']}")
        print(f"    Impact: ~{inc['userImpactEstimate']} users, Age: {inc['ageHrs']:.1f}h")
```

**Supports:**
- Automated major incident detection
- User impact assessment
- Priority-based filtering
- Real-time alerting capability

**ITSM Benefit:** Ensures critical incidents receive appropriate attention

#### 8.2 Major Incident Timeline & RCA
```python
# Generate comprehensive timeline for major incident
from snow_analytics.rca import RCAGenerator

rca_gen = RCAGenerator(...)
major_inc_data = rca_gen.extract_incident_data('INC0012345')

# Detailed timeline with all events
timeline = major_inc_data['timeline']

print(f"Major Incident Timeline ({len(timeline)} events):")
for event in timeline:
    print(f"  {event['timestamp']}: {event['event_type']} - {event['description']}")
```

**Supports:**
- Comprehensive incident timeline
- Event correlation
- Post-incident review documentation
- Lessons learned capture

**ITSM Benefit:** Structured post-incident review process

---

## 9. Reporting & Analytics

### ITSM Workflow
**Objective:** Provide stakeholders with actionable insights and performance metrics.

**Key Activities:**
- KPI dashboard creation
- Executive reporting
- Trend analysis
- Operational metrics

### Toolkit Support

#### 9.1 Executive Summary Dashboard
```python
# Generate executive summary
def generate_executive_summary(df):
    summary = {
        'total_incidents': len(df),
        'active_incidents': df['isActive'].sum(),
        'sla_compliance': 100 - calculate_sla_metrics(df)['breach_rate_pct'],
        'avg_resolution_hrs': df['resolutionTimeHrs'].mean(),
        'p1_p2_incidents': df['isHighImpact'].sum(),
        'recurring_issues': len(find_recurring_issues(df, min_occurrences=3))
    }
    return summary

summary = generate_executive_summary(df_enriched)

print("📊 Executive Summary:")
print(f"  Total Incidents: {summary['total_incidents']}")
print(f"  Active/Open: {summary['active_incidents']}")
print(f"  SLA Compliance: {summary['sla_compliance']:.1f}%")
print(f"  Avg Resolution: {summary['avg_resolution_hrs']:.1f} hours")
print(f"  P1/P2 Incidents: {summary['p1_p2_incidents']}")
print(f"  Recurring Issues: {summary['recurring_issues']}")
```

**Supports:**
- Executive KPI summary
- Operational metrics
- Performance indicators
- Trend visualization (when combined with visualization libraries)

#### 9.2 Operational Reports
```python
# Daily operational report
def generate_daily_report(df, date):
    daily_data = df[df['openedDate'].dt.date == pd.to_datetime(date).date()]

    report = {
        'date': date,
        'new_incidents': len(daily_data),
        'resolved_incidents': daily_data['isResolved'].sum(),
        'p1_incidents': (daily_data['priority'] == '1 - Critical').sum(),
        'sla_breaches': daily_data['slaBreach'].sum(),
        'top_categories': daily_data['patternCategory'].value_counts().head(5).to_dict()
    }

    return report

today_report = generate_daily_report(df_enriched, '2025-01-15')
print(f"Daily Report for {today_report['date']}:")
print(f"  New: {today_report['new_incidents']}")
print(f"  Resolved: {today_report['resolved_incidents']}")
print(f"  P1s: {today_report['p1_incidents']}")
print(f"  SLA Breaches: {today_report['sla_breaches']}")
```

**ITSM Benefit:** Automated reporting, consistent metrics

---

## 10. Assignment & Routing Optimization

### ITSM Workflow
**Objective:** Ensure incidents are routed to the correct teams efficiently.

**Key Activities:**
- Incident categorization
- Assignment group determination
- Skill-based routing
- Queue management

### Toolkit Support

#### 10.1 Routing Efficiency Analysis
```python
# Analyze first-time assignment success
first_time_success = df_enriched[df_enriched['reassignment_count'] == 0]
success_rate = (len(first_time_success) / len(df_enriched)) * 100

print(f"First-Time Assignment Success Rate: {success_rate:.1f}%")

# By category
routing_by_category = df_enriched.groupby('patternCategory').agg({
    'reassignment_count': 'mean',
    'number': 'count'
}).sort_values('reassignment_count', ascending=False)

print("\nRouting Efficiency by Category:")
print(routing_by_category)
```

**Supports:**
- Routing accuracy measurement
- Category-based routing analysis
- Assignment group performance
- Improvement opportunity identification

**ITSM Benefit:** Data-driven routing rule optimization

#### 10.2 Queue Depth Monitoring
```python
# Current queue depth by assignment group
queue_depth = df_enriched[df_enriched['isActive'] == True].groupby('assignment_group').agg({
    'number': 'count',
    'ageHrs': 'mean'
}).sort_values('number', ascending=False)

print("Current Queue Depth:")
for group, metrics in queue_depth.head(10).iterrows():
    print(f"  {group}: {metrics['number']} incidents (avg age: {metrics['ageHrs']:.1f}h)")
```

**ITSM Benefit:** Real-time workload visibility, resource allocation

---

## Integration Points with ServiceNow

### API Integration
```python
# Real-time data sync
from snow_analytics import load_incidents
from snow_analytics.connectors import ServiceNowAPI

# Scheduled data extraction (e.g., hourly)
with ServiceNowAPI(url, user, pass) as api:
    recent_incidents = api.get_incidents(
        query='sys_updated_on>=javascript:gs.hoursAgo(1)',
        limit=500
    )
```

### Export/Import Workflows
```python
# Export analysis results back to ServiceNow
# (e.g., update custom fields with quality scores)

# 1. Analyze locally
df_analyzed = transform_incidents(df_raw)
df_quality = check_incident_quality(df_analyzed)

# 2. Identify incidents needing attention
needs_review = df_quality[df_quality['quality_issues_count'] > 0]

# 3. Export for import into ServiceNow
needs_review[['number', 'quality_issues_count', 'quality_priority_mismatch']].to_csv(
    'output/incidents_for_review.csv',
    index=False
)

# 4. Use ServiceNow Import Sets or API to update records
```

---

## Best Practices for ITSM Workflows

### 1. **Scheduled Analytics Jobs**
```python
# Daily morning report
# Run at 8 AM to review previous day's activity

from datetime import datetime, timedelta
import schedule

def daily_itsm_report():
    # Load yesterday's incidents
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    df = load_incidents('api', query_filter=f'opened_atON{yesterday}')
    df = transform_incidents(df)

    # Generate metrics
    sla_metrics = calculate_sla_metrics(df)
    quality_check = check_incident_quality(df)

    # Email report (pseudo-code)
    send_email(
        to='itsm_managers@company.com',
        subject=f'Daily ITSM Report - {yesterday}',
        body=format_report(sla_metrics, quality_check)
    )

# Schedule daily at 8 AM
schedule.every().day.at("08:00").do(daily_itsm_report)
```

### 2. **PII Redaction for Reporting**
```python
from snow_analytics import redact_dataframe

# Always redact before sharing with non-IT stakeholders
df_for_business = redact_dataframe(
    df_enriched,
    text_columns=['short_description', 'description'],
    drop_columns=['caller_id', 'assigned_to', 'opened_by']
)

df_for_business.to_excel('reports/executive_report.xlsx', index=False)
```

### 3. **Continuous Monitoring**
```python
# Real-time SLA breach alerting
def monitor_sla_breaches():
    df = load_incidents('api', query_filter='active=true')
    df = transform_incidents(df, transformations=['dates', 'status', 'durations', 'sla'])

    # Find incidents at risk (< 2 hours to SLA breach)
    at_risk = df[
        (df['isActive'] == True) &
        (df['slaMarginHrs'] < 2) &
        (df['slaMarginHrs'] > 0)
    ]

    if not at_risk.empty:
        alert_team(f"⚠️ {len(at_risk)} incidents at risk of SLA breach!")

# Run every 15 minutes
schedule.every(15).minutes.do(monitor_sla_breaches)
```

---

## Summary: ITSM Value Proposition

| ITSM Process | Toolkit Capability | Business Value |
|--------------|-------------------|----------------|
| **Incident Management** | Auto-categorization, backlog tracking | Faster resolution, better prioritization |
| **Problem Management** | Pattern detection, RCA generation | Reduced repeat incidents, proactive fixes |
| **Change Management** | Post-change analysis, correlation | Safer changes, faster rollback decisions |
| **SLA Management** | Real-time tracking, breach prediction | Improved compliance, proactive escalation |
| **Service Level Management** | Resolution time analysis, quality metrics | Data-driven service improvement |
| **Knowledge Management** | Gap identification, common issue detection | Better knowledge articles, faster resolution |
| **CSI** | Quality checks, routing analysis | Measurable process improvements |
| **Major Incident Mgmt** | Timeline reconstruction, impact assessment | Better post-incident reviews |
| **Reporting** | Automated KPIs, executive dashboards | Stakeholder transparency |
| **Assignment & Routing** | Efficiency analysis, queue monitoring | Optimized resource allocation |

---

## Next Steps: Implementing ITSM Workflows

### Phase 1: Foundation (Week 1-2)
1. ✅ Install and configure toolkit
2. ✅ Set up ServiceNow API connection
3. ✅ Configure SLA rules and categorization
4. ✅ Run initial data load and validation

### Phase 2: Basic Workflows (Week 3-4)
1. Implement daily SLA reporting
2. Set up backlog monitoring
3. Configure quality checks
4. Create executive dashboard

### Phase 3: Advanced Workflows (Month 2)
1. Implement RCA generation for major incidents
2. Set up pattern detection for problem management
3. Configure automated alerts (SLA breach, quality issues)
4. Integrate with change management process

### Phase 4: Optimization (Month 3+)
1. Refine categorization rules based on results
2. Optimize routing based on analysis
3. Implement continuous monitoring
4. Create custom reports for stakeholders

---

## Conclusion

The ServiceNow Analytics toolkit provides comprehensive support for ITSM workflows by:

1. **Automating manual analysis** - Reduces time spent on reporting and metrics
2. **Providing actionable insights** - Data-driven decision making for ITSM processes
3. **Ensuring compliance** - SLA tracking and quality monitoring
4. **Enabling continuous improvement** - Identifies process gaps and improvement opportunities
5. **Supporting best practices** - Aligns with ITIL framework and ServiceNow platform

**Ready to get started?** See `README_REFACTORED.md` for installation and usage instructions.
