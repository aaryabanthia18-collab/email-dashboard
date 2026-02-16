#!/usr/bin/env python3
"""
Email Dashboard Generator - Fetches emails and generates static dashboard
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import re
import json

def get_email_config():
    """Read email credentials from config"""
    with open('/root/.openclaw/workspace/.email_config', 'r') as f:
        lines = f.readlines()
        email_addr = None
        app_pass = None
        for line in lines:
            if 'address' in line:
                email_addr = line.split('=')[1].strip().strip('"')
            if 'app_password' in line:
                app_pass = line.split('=')[1].strip().strip('"')
        return email_addr, app_pass

def extract_tasks(body, subject=""):
    """Extract actionable tasks from email body and subject"""
    tasks = []
    text = subject + " " + body
    
    # Clean up text
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Split into sentences for context
    sentences = re.split(r'[.!?]+', text)
    
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20 or len(sent) > 300:
            continue
        
        task = None
        
        # Pattern 1: Direct action requests
        if re.search(r'\b(please|kindly)\s+(review|approve|sign|submit|send|complete|update|check|confirm|read|look at)\b', sent, re.IGNORECASE):
            match = re.search(r'(?:please|kindly)\s+(review|approve|sign|submit|send|complete|update|check|confirm|read|look at)\s+(.+)', sent, re.IGNORECASE)
            if match:
                task = f"{match.group(1).capitalize()} {match.group(2)}"
        
        # Pattern 2: Need to / Need you to
        elif re.search(r'\b(we need to|you need to|i need you to|need to)\s+', sent, re.IGNORECASE):
            match = re.search(r'(?:we need to|you need to|i need you to|need to)\s+(.+)', sent, re.IGNORECASE)
            if match:
                task = match.group(1).capitalize()
        
        # Pattern 3: Don't forget / Remember
        elif re.search(r'\b(don\'t forget to|remember to|make sure to)\s+', sent, re.IGNORECASE):
            match = re.search(r'(?:don\'t forget to|remember to|make sure to)\s+(.+)', sent, re.IGNORECASE)
            if match:
                task = match.group(1).capitalize()
        
        # Pattern 4: Action item
        elif re.search(r'\baction item\b', sent, re.IGNORECASE):
            match = re.search(r'action item[s]?:?\s*(.+)', sent, re.IGNORECASE)
            if match:
                task = match.group(1).capitalize()
        
        # Pattern 5: Schedule/Book/Arrange
        elif re.search(r'\b(schedule|book|arrange|set up)\s+(?:a\s+)?(meeting|call|sync|discussion|demo|review)\b', sent, re.IGNORECASE):
            match = re.search(r'(schedule|book|arrange|set up)\s+(?:a\s+)?(meeting|call|sync|discussion|demo|review)\s*(?:with\s+)?(.+)?', sent, re.IGNORECASE)
            if match:
                with_whom = match.group(3) if match.group(3) else ""
                task = f"{match.group(1).capitalize()} {match.group(2)} {with_whom}".strip()
        
        # Pattern 6: Due/Deadline/By date
        elif re.search(r'\b(due|deadline|by|before)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|tomorrow|today|\d{1,2})', sent, re.IGNORECASE):
            # Get the action before the deadline
            match = re.search(r'(.+?)\s+(?:is\s+)?(?:due|deadline|by|before)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|tomorrow|today|\d{1,2}[^\.\n]*)', sent, re.IGNORECASE)
            if match:
                action = match.group(1).strip()
                deadline = match.group(2)
                if len(action) > 10:
                    task = f"{action} (Due {deadline})"
        
        # Pattern 7: Awaiting/Waiting for/Looking forward to
        elif re.search(r'\b(awaiting|waiting for|looking forward to)\s+(?:your\s+)?(reply|response|feedback|input)', sent, re.IGNORECASE):
            task = "Reply to email"
        
        # Pattern 8: Attached documents
        elif re.search(r'\b(attached|find attached|see attached|please find|enclosed)\b', sent, re.IGNORECASE) and re.search(r'\b(document|file|report|proposal|invoice|contract|agreement)\b', sent, re.IGNORECASE):
            match = re.search(r'(?:attached|enclosed)[^\.\n]*(document|file|report|proposal|invoice|contract|agreement)[^\.\n]*', sent, re.IGNORECASE)
            if match:
                doc_type = match.group(1)
                task = f"Review attached {doc_type}"
        
        # Clean up and add task
        if task:
            # Remove extra whitespace
            task = re.sub(r'\s+', ' ', task)
            # Remove trailing punctuation
            task = re.sub(r'[,;:]+$', '', task)
            # Capitalize first letter
            task = task[0].upper() + task[1:] if task else task
            
            if len(task) > 15 and len(task) < 200:
                tasks.append(task)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tasks = []
    for task in tasks:
        # Create a normalized version for comparison
        normalized = re.sub(r'[^\w\s]', '', task.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        if normalized not in seen and len(normalized) > 10:
            seen.add(normalized)
            unique_tasks.append(task)
    
    return unique_tasks[:10]

def extract_events(body, subject):
    """Extract potential events/meetings"""
    events = []
    meeting_keywords = ['meeting', 'call', 'zoom', 'teams', 'google meet', 'webinar', 'conference', 'appointment']
    text = subject + ' ' + body
    for keyword in meeting_keywords:
        if keyword.lower() in text.lower():
            events.append({'type': keyword, 'details': 'Detected in email'})
    return events[:3]

def categorize_email(subject, body):
    """Categorize email by type"""
    subject_lower = subject.lower()
    body_lower = body.lower()
    categories = {
        'work': ['work', 'project', 'deadline', 'meeting', 'report', 'client', 'boss', 'manager'],
        'personal': ['personal', 'family', 'friend', 'birthday', 'invitation'],
        'finance': ['bank', 'payment', 'invoice', 'bill', 'transaction', 'money', 'salary'],
        'shopping': ['order', 'delivery', 'amazon', 'flipkart', 'shipped', 'tracking'],
        'newsletter': ['newsletter', 'subscription', 'unsubscribe', 'digest', 'update'],
        'social': ['linkedin', 'facebook', 'twitter', 'instagram', 'notification'],
    }
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in subject_lower or keyword in body_lower:
                return category
    return 'other'

def fetch_emails(limit=20):
    """Fetch emails from Gmail"""
    try:
        email_addr, app_pass = get_email_config()
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(email_addr, app_pass)
        mail.select('inbox')
        
        date = (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
        status, messages = mail.search(None, f'(SINCE "{date}")')
        
        emails = []
        if status == 'OK' and messages[0]:
            email_ids = messages[0].split()[-limit:]
            
            for email_id in reversed(email_ids):
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                subject = ""
                if msg['Subject']:
                    decoded = decode_header(msg['Subject'])
                    for part, charset in decoded:
                        if isinstance(part, bytes):
                            subject += part.decode(charset or 'utf-8', errors='ignore')
                        else:
                            subject += part
                
                from_addr = msg['From'] or "Unknown"
                date_str = msg['Date'] or "Unknown"
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')[:1000]
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')[:1000]
                    except:
                        pass
                
                category = categorize_email(subject, body)
                tasks = extract_tasks(body, subject)
                events = extract_events(body, subject)
                
                sender_name = from_addr.split('<')[0].strip() if '<' in from_addr else from_addr
                if len(sender_name) > 30:
                    sender_name = sender_name[:27] + '...'
                
                emails.append({
                    'id': email_id.decode(),
                    'subject': subject[:80] + ('...' if len(subject) > 80 else ''),
                    'from': sender_name,
                    'date': date_str,
                    'category': category,
                    'tasks': tasks,
                    'events': events,
                    'preview': body[:150].replace('\n', ' ').strip() + '...' if body else ''
                })
        
        mail.logout()
        return emails
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return []

def generate_dashboard():
    """Generate dashboard data"""
    print(f"[{datetime.now()}] Fetching emails...")
    emails = fetch_emails(20)
    
    categories = {}
    all_tasks = []
    all_events = []
    
    for e in emails:
        cat = e['category']
        categories[cat] = categories.get(cat, 0) + 1
        all_tasks.extend(e['tasks'])
        all_events.extend(e['events'])
    
    dashboard_data = {
        'summary': {
            'total_emails': len(emails),
            'categories': categories,
            'task_count': len(all_tasks),
            'event_count': len(all_events)
        },
        'emails': emails,
        'tasks': list(set(all_tasks))[:10],
        'events': all_events,
        'last_updated': datetime.now().isoformat()
    }
    
    # Save to JSON file
    with open('/root/.openclaw/workspace/email-dashboard/data.json', 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    print(f"[{datetime.now()}] Dashboard updated: {len(emails)} emails, {len(all_tasks)} tasks")
    return dashboard_data

if __name__ == "__main__":
    generate_dashboard()
