# Daily Operations Workflows - Outline

## Overview

**Current State:** 90 minutes/day spent on reactive morning tasks
**Goal:** Automate analysis and shift focus from reactive → proactive/preventive

---

## Workflow 1: Morning Quality & Escalation Report

**Current Pain:** 45 minutes manually analyzing backlog Excel for issues and drafting escalations

**Target:** < 5 minutes to review automated report and send pre-drafted escalations

### Purpose
Automated daily scan to identify quality issues and generate escalation-ready summaries

### Execution
- **Trigger:** Scheduled (7:30 AM daily, before your workday)
- **Runtime:** ~2-3 minutes
- **Output:** Single Excel report + draft escalation text

### Data Source
```python
# Option A: API query for recent tickets (last 24-48 hours)
df = load_incidents('api',
    query_filter='opened_at>=javascript:gs.daysAgoStart(2)',
    limit=1000
)

# Option B: CSV export from ServiceNow scheduled report
df = load_incidents('csv', file_path='downloads/daily_incidents.csv')
```

### Analysis Steps

**1. Mis-classified Tickets**
- Detect priority mismatches (P1/P2 with slow resolution times)
- Flag tickets with priority vs. impact/urgency inconsistencies
- **Output Sheet:** "Priority Issues" with recommendation column

**2. Mis-routed Tickets (>3 reassignments)**
- Identify tickets reassigned more than 3 times
- Calculate "ping-pong" patterns (A→B→A)
- **Output Sheet:** "Routing Issues" with reassignment history

**3. Invalid On-Hold Tickets**
- Find tickets on-hold > 72 hours without valid reason
- Flag on-hold tickets without "Awaiting..." work notes
- **Output Sheet:** "On-Hold Abuse" with hold duration

**4. Pre-Backlog Warnings (NEW - Prevention)**
- Tickets approaching 10-day threshold (currently 7-9 days old)
- Active tickets nearing SLA breach (< 4 hours remaining)
- **Output Sheet:** "Prevention Required" - catch before backlog

**5. Draft Escalations**
- Generate summary stats for team message/email
- Pre-drafted text for each issue category
- **Output File:** `escalation_draft.txt`

### Report Structure

**Excel File:** `output/morning_quality_report_YYYY-MM-DD.xlsx`

**Sheets:**
1. **Summary Dashboard** - Key metrics and counts
2. **Prevention Required** - ⚠️ Tickets needing immediate attention
3. **Priority Issues** - Mis-classified tickets
4. **Routing Issues** - Mis-routed tickets (>3 reassignments)
5. **On-Hold Abuse** - Invalid on-hold tickets
6. **Action Items** - Sorted by urgency

**Text File:** `output/escalation_drafts_YYYY-MM-DD.txt`
- Pre-formatted messages for Teams/Email
- Ready to copy-paste with minimal editing

### Success Criteria
- Reduces 45 min → 5 min
- Zero manual Excel analysis
- Escalation text ready to send
- **Proactive:** Catches issues before they hit backlog

---

## Workflow 2: Major Incident Monitoring & Context

**Current Pain:** 45 minutes scanning email/Teams for P1/P2s, then manually researching context

**Target:** < 5 minutes to review automated digest with full context

### Purpose
Automated P1/P2 detection with instant context: impact, similar issues, recent changes, known problems

### Execution
- **Trigger:** Scheduled (every 2 hours, or on-demand for real-time check)
- **Runtime:** ~1-2 minutes
- **Output:** Major incident digest with research

### Data Source
```python
# Real-time API query for recent P1/P2 incidents
df = load_incidents('api',
    query_filter='priority=1^ORpriority=2^opened_at>=javascript:gs.hoursAgoStart(2)',
    limit=100
)
```

### Analysis Steps

**1. Major Incident Detection**
- Filter P1 (Critical) and P2 (High) incidents
- Identify new incidents since last check
- Flag incidents without assignment

**2. Impact Assessment**
- Duration since opened (real-time age)
- Affected CIs and services
- User impact estimate (affected user count if available)
- Business criticality

**3. Similar Incident Search**
- Search last 90 days for similar descriptions (keyword matching)
- Cluster by CI and category
- Identify if this is a recurring pattern
- **Output:** "Similar Incidents Found: 5 in last 30 days"

**4. Known Problem Lookup**
- Check if incident matches known problem patterns
- Search resolution notes from similar past incidents
- Identify common workarounds
- **Output:** "Possible Known Issue: VPN auth failure - Workaround: Clear credentials"

**5. Recent Change Correlation**
- Flag if incident opened within 24 hours of related CI change
- Identify potential change-related root cause
- **Output:** "Recent Change: VPN server upgrade 8 hours ago"

**6. RCA Preparation (for P1s)**
- Pre-populate RCA template with available data
- Timeline construction
- Stakeholder identification
- **Output:** Draft RCA skeleton ready to complete

### Report Structure

**Excel File:** `output/major_incidents_digest_YYYY-MM-DD_HHMM.xlsx`

**Sheets:**
1. **Active P1/P2 Summary** - Overview with key metrics
2. **New Since Last Check** - Incidents needing attention
3. **Context Research** - Similar incidents, changes, patterns
4. **Recommended Actions** - Prioritized next steps

**Console Summary (if run interactively):**
```
=====================================================================
MAJOR INCIDENT DIGEST - 2025-11-17 09:00
=====================================================================

🚨 ACTIVE P1 INCIDENTS: 2
⚠️  ACTIVE P2 INCIDENTS: 5

NEW SINCE LAST CHECK (7:00 AM): 3
  • INC0012345 [P1] - Database outage - 15 mins old - UNASSIGNED
  • INC0012346 [P2] - VPN connectivity - 45 mins old - Assigned: J.Smith
  • INC0012347 [P2] - Email delays - 30 mins old - Assigned: Team A

CONTEXT HIGHLIGHTS:
  • INC0012345: Similar issue 2 weeks ago (INC0012100) - Root cause: storage
  • INC0012346: 8 similar VPN issues in last 7 days - Pattern detected
  • INC0012347: Recent change: Email server patch 6 hours ago

RECOMMENDED ACTIONS:
  1. Assign INC0012345 immediately to storage team
  2. Escalate VPN pattern to problem management
  3. Review email server change for rollback
=====================================================================
```

### Success Criteria
- Reduces 45 min → 5 min
- Zero manual email/Teams scanning
- Full context available instantly
- **Proactive:** Identifies patterns and known problems automatically

---

## Workflow 3: SLA Breach Prevention (NEW)

**Purpose:** Catch tickets BEFORE they breach, not after

### Execution
- **Trigger:** Scheduled (every 4 hours, or on-demand)
- **Runtime:** ~1 minute
- **Output:** At-risk ticket list with time remaining

### Analysis Steps

**1. Breach Risk Calculation**
- Identify active tickets with < 4 hours to SLA breach
- Calculate exact time remaining per ticket
- Prioritize by severity (P1 > P2 > P3)

**2. Assignee Alerting**
- List tickets by assignee
- Flag unassigned at-risk tickets
- **Output Sheet:** "Alert by Assignee" - ready for targeted communication

**3. Management Escalation**
- Tickets at risk requiring manager intervention
- Patterns indicating systemic issues (multiple breaches in same category)

### Report Structure

**Excel File:** `output/sla_prevention_YYYY-MM-DD_HHMM.xlsx`

**Sheets:**
1. **Critical - < 2 Hours** - Immediate action required
2. **Warning - 2-4 Hours** - Proactive intervention
3. **By Assignee** - For targeted alerts
4. **By Category** - Pattern identification

### Success Criteria
- Prevents breaches instead of reacting to them
- Targeted assignee notifications
- Early warning for management escalation

---

## Implementation Plan

### Phase 1: Morning Quality Report (Week 1)
- Build quality detection logic
- Create Excel report template
- Generate escalation text
- Schedule daily execution

### Phase 2: Major Incident Digest (Week 2)
- Build P1/P2 detection
- Implement similar incident search
- Add change correlation
- Create digest format

### Phase 3: SLA Prevention (Week 3)
- Calculate breach risk windows
- Build alerting by assignee
- Integrate with quality report

### Phase 4: Automation & Scheduling (Week 4)
- Set up scheduled execution (cron/Task Scheduler)
- Email integration (optional)
- Teams webhook integration (optional)
- Refinement based on usage

---

## Questions to Finalize Design

### For Workflow 1 (Quality Report):

1. **Escalation Recipients:**
   - Team message, email, or both?
   - Specific format preferences (bullet points, table, narrative)?

2. **Threshold Tuning:**
   - Reassignment threshold: Currently 3, adjust?
   - On-hold threshold: Currently 72 hours, adjust?
   - Pre-backlog warning: Currently 7-9 days, adjust?

3. **Mis-classification Criteria:**
   - What defines a mis-classified ticket for your team?
   - P1 resolved > 4 hours? P2 resolved > 8 hours?

### For Workflow 2 (Major Incident Digest):

1. **Frequency:**
   - Every 2 hours automatic?
   - On-demand when you arrive?
   - Real-time webhook (advanced)?

2. **Similar Incident Matching:**
   - Description keyword matching sufficient?
   - Need CI-based clustering?
   - How far back to search (30/60/90 days)?

3. **Change Correlation:**
   - Do you have access to ServiceNow Change Management API?
   - Time window for change correlation (24 hours)?

### For Workflow 3 (SLA Prevention):

1. **Alert Timing:**
   - 4 hours before breach sufficient?
   - Different thresholds per priority (P1: 2hrs, P2: 4hrs)?

2. **Notification Method:**
   - Excel report only?
   - Direct email to assignees?
   - Teams channel alert?

---

## Next Steps

1. **Review this outline** - Adjust thresholds, add/remove checks
2. **Answer design questions** - Finalize specifications
3. **Prioritize workflows** - Which to build first?
4. **Begin implementation** - Start with highest ROI workflow

**Expected Time Savings:** 90 min/day → 15 min/day (75 min/day saved)
**Monthly Impact:** 25+ hours saved
