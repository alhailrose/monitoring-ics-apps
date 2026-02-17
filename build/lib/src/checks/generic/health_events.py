"""AWS Health Events Checker"""
import boto3
from datetime import datetime
from src.checks.common.base import BaseChecker

class HealthChecker(BaseChecker):
    def __init__(self, region='us-east-1'):
        super().__init__(region)
        
    def check(self, profile, account_id):
        """Check AWS Health events"""
        try:
            session = boto3.Session(profile_name=profile)
            health = session.client('health', region_name='us-east-1')
            
            response = health.describe_events()
            events = response.get('events', [])
            
            # Get event details
            detailed_events = []
            for event in events:
                event_arn = event['arn']
                
                # Get event description
                try:
                    details = health.describe_event_details(eventArns=[event_arn])
                    event_details = details.get('successfulSet', [{}])[0]
                    description = event_details.get('eventDescription', {}).get('latestDescription', 'N/A')
                except:
                    description = 'N/A'
                
                # Get affected entities
                try:
                    entities = health.describe_affected_entities(filter={'eventArns': [event_arn]})
                    affected = entities.get('entities', [])
                except:
                    affected = []
                
                detailed_events.append({
                    'event': event,
                    'description': description,
                    'affected_entities': affected
                })
            
            return {
                'status': 'success',
                'profile': profile,
                'account_id': account_id,
                'events': detailed_events,
                'total_events': len(events),
                'action_required': len([e for e in events if e.get('actionability') == 'ACTION_REQUIRED'])
            }
            
        except Exception as e:
            error_msg = str(e)
            if 'SubscriptionRequiredException' in error_msg:
                error_msg = 'AWS Health API requires Business or Enterprise Support plan'
            return {
                'status': 'error',
                'profile': profile,
                'account_id': account_id,
                'error': error_msg
            }
    
    def format_report(self, results):
        """Format health events into readable report"""
        if results['status'] == 'error':
            return f"ERROR: {results['error']}"
        
        now = self.timestamp
        date_str = now.strftime('%B %d, %Y')
        time_str = now.strftime('%H:%M WIB')
        
        lines = []
        lines.append("AWS HEALTH EVENTS MONITORING REPORT")
        lines.append(f"Date: {date_str} | Time: {time_str}")
        lines.append(f"Account: {results['profile']} ({results['account_id']})")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("EXECUTIVE SUMMARY")
        
        if results['total_events'] == 0:
            lines.append("Health assessment completed. No AWS Health events detected.")
        else:
            lines.append(f"Health assessment completed. {results['total_events']} events detected")
            if results['action_required'] > 0:
                lines.append(f"requiring attention ({results['action_required']} events need action).")
            else:
                lines.append("for informational purposes.")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("ASSESSMENT RESULTS")
        
        if not results['events']:
            lines.append("")
            lines.append("AWS HEALTH EVENTS")
            lines.append("Status: CLEAR - No health events detected")
            lines.append("")
            lines.append("=" * 80)
            return "\n".join(lines)
        
        # Group by status
        open_events = [e for e in results['events'] if e['event']['statusCode'] in ['open', 'upcoming']]
        closed_events = [e for e in results['events'] if e['event']['statusCode'] == 'closed']
        
        if open_events:
            lines.append("")
            lines.append("AWS HEALTH EVENTS")
            if results['action_required'] > 0:
                lines.append(f"Status: ATTENTION REQUIRED - {results['action_required']} events need action")
            else:
                lines.append(f"Status: {len(open_events)} informational events")
            lines.append("")
            lines.append("Active Events:")
            
            for idx, item in enumerate(open_events, 1):
                event = item['event']
                lines.append(f"\n• Event #{idx}: {event['service']} - {event['eventTypeCode']}")
                lines.append(f"  Status: {event['statusCode'].upper()}")
                
                # Check if overdue
                start_time = event.get('startTime')
                if start_time:
                    start_dt = start_time if isinstance(start_time, datetime) else datetime.fromisoformat(str(start_time).replace('+07:00', ''))
                    if start_dt < datetime.now(start_dt.tzinfo):
                        days_overdue = (datetime.now(start_dt.tzinfo) - start_dt).days
                        lines.append(f"  WARNING: OVERDUE by {days_overdue} days")
                
                lines.append(f"  Region: {event['region']}")
                lines.append(f"  Category: {event['eventTypeCategory']}")
                lines.append(f"  Start Time: {event.get('startTime', 'N/A')}")
                lines.append(f"  Last Updated: {event.get('lastUpdatedTime', 'N/A')}")
                
                if event.get('endTime'):
                    lines.append(f"  End Time: {event['endTime']}")
                
                lines.append(f"  Actionability: {event.get('actionability', 'N/A')}")
                
                if item['description'] != 'N/A':
                    lines.append(f"  Description: {item['description'][:200]}...")
                
                if item['affected_entities']:
                    lines.append(f"  Affected Resources: {len(item['affected_entities'])} resource(s)")
                    for entity in item['affected_entities'][:3]:
                        lines.append(f"    - {entity.get('entityValue', 'N/A')}")
                    if len(item['affected_entities']) > 3:
                        lines.append(f"    ... and {len(item['affected_entities']) - 3} more")
                lines.append("")
        
        if closed_events:
            lines.append("")
            lines.append(f"Recently Closed Events: {len(closed_events)}")
            for idx, item in enumerate(closed_events[:3], 1):
                event = item['event']
                lines.append(f"\n• {event['service']} - {event['eventTypeCode']}")
                lines.append(f"  Closed: {event.get('endTime', 'N/A')}")
        
        # Recommendations
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        lines.append("RECOMMENDATIONS")
        
        rec_count = 1
        if results['action_required'] > 0:
            overdue = [e for e in open_events if e['event'].get('startTime')]
            if overdue:
                lines.append(f"{rec_count}. IMMEDIATE ACTION REQUIRED: Review overdue health events")
                lines.append(f"   {len(overdue)} event(s) past their start date")
                rec_count += 1
            
            lines.append(f"{rec_count}. REVIEW REQUIRED: Address {results['action_required']} actionable events")
            lines.append(f"   Check AWS Health Dashboard for detailed remediation steps")
            rec_count += 1
        else:
            lines.append(f"{rec_count}. ROUTINE MONITORING: Continue health event monitoring")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
