#!/usr/bin/env python3
"""
Email Dashboard API Server
Fetches real Gmail data and serves it to the dashboard
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import re
import threading
import time

# Cache for email data
email_cache = {
    'data': None,
    'last_update': 0
}

def get_email_config():
    """Read email credentials from config"""
    config_path = '/root/.openclaw/workspace/.email_config'
    with open(config_path, 'r') as f:
        lines = f.readlines()
        email_addr = None
        app_pass = None
        for line in lines:
            if 'address' in line:
                email_addr = line.split('=')[1].strip().strip('"')
            if 'app_password' in line:
                app_pass = line.split('=')[1].strip().strip('"')
        return email_addr, app_pass

def extract_tasks(body):
    """Extract potential tasks from email body"""
    tasks = []
    task_patterns = [
        r'(?:please|kindly|need to|should|must|todo|to-do|action item|follow up|deadline)[\s:]*([^\.\n]+)',
        r'\b(due by|due on|deadline|complete by|finish by)[\s:]*([^\.\n]+)',
        r'\b(meeting|call|schedule|appointment)[\s:]*([^\.\n]+)',
    ]
    for pattern in task_patterns:
        matches = re.findall(pattern, body, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                task = ' '.join(match).strip()
            else:
                task = match.strip()
            if task and len(task) > 10 and len(task) < 200:
                tasks.append(task)
    return list(set(tasks))[:5]

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
                tasks = extract_tasks(body)
                events = extract_events(body, subject)
                
                # Clean up sender name
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

def get_dashboard_data():
    """Get dashboard data with caching"""
    global email_cache
    current_time = time.time()
    
    # Refresh cache if older than 5 minutes
    if email_cache['data'] is None or (current_time - email_cache['last_update']) > 300:
        print("Fetching fresh email data...")
        emails = fetch_emails(20)
        
        categories = {}
        all_tasks = []
        all_events = []
        
        for e in emails:
            cat = e['category']
            categories[cat] = categories.get(cat, 0) + 1
            all_tasks.extend(e['tasks'])
            all_events.extend(e['events'])
        
        email_cache['data'] = {
            'summary': {
                'total_emails': len(emails),
                'categories': categories,
                'task_count': len(all_tasks),
                'event_count': len(all_events)
            },
            'emails': emails,
            'tasks': list(set(all_tasks))[:10],
            'events': all_events
        }
        email_cache['last_update'] = current_time
    
    return email_cache['data']

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/dashboard':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            data = get_dashboard_data()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress logs
        pass

def run_server(port=8000):
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"Email Dashboard API running on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
