#!/usr/bin/env python3
"""
Fetch and summarize today's emails using LLM
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import re
import json
import subprocess

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

def fetch_todays_emails():
    """Fetch all emails from today"""
    try:
        email_addr, app_pass = get_email_config()
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(email_addr, app_pass)
        mail.select('inbox')
        
        # Get today's date
        today = datetime.now().strftime('%d-%b-%Y')
        status, messages = mail.search(None, f'(ON "{today}")')
        
        emails = []
        if status == 'OK' and messages[0]:
            email_ids = messages[0].split()
            
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
                
                # Get full body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
                
                # Clean body
                body = re.sub(r'http[s]?://\S+', '[URL]', body)
                body = re.sub(r'\s+', ' ', body).strip()
                
                sender_name = from_addr.split('<')[0].strip() if '<' in from_addr else from_addr
                
                emails.append({
                    'subject': subject,
                    'from': sender_name,
                    'date': date_str,
                    'body': body[:2000]  # First 2000 chars
                })
        
        mail.logout()
        return emails
    except Exception as e:
        print(f"Error: {e}")
        return []

def summarize_with_llm(emails):
    """Use LLM to summarize all emails"""
    
    # Format emails for the LLM
    email_texts = []
    for i, e in enumerate(emails, 1):
        email_texts.append(f"""
EMAIL {i}:
From: {e['from']}
Subject: {e['subject']}
Body: {e['body'][:800]}
---""")
    
    all_emails_text = "\n".join(email_texts)
    
    prompt = f"""You are an executive assistant summarizing the user's inbox. Write a clear, concise paragraph (4-6 sentences) summarizing these {len(emails)} emails from today.

Focus on:
1. What are the main themes/topics?
2. Are there any urgent items requiring attention?
3. What actions might be needed?
4. Any patterns or notable senders?

Here are the emails:
{all_emails_text}

Write a natural, flowing summary paragraph:"""

    # Save prompt to file for the LLM to process
    with open('/tmp/email_summary_prompt.txt', 'w') as f:
        f.write(prompt)
    
    print(f"Prepared {len(emails)} emails for summarization")
    print("\n" + "="*60)
    print("TODAY'S EMAIL SUMMARY")
    print("="*60)
    
    # Since we can't directly call the LLM from here, we'll output the structured data
    # and the user can see the emails formatted
    return emails

if __name__ == "__main__":
    print("Fetching today's emails...")
    emails = fetch_todays_emails()
    
    if not emails:
        print("No emails found from today.")
    else:
        print(f"\nFound {len(emails)} emails from today:\n")
        for e in emails:
            print(f"• {e['from']}: {e['subject']}")
        
        print("\n" + "="*60)
        print("PREPARING LLM SUMMARY...")
        print("="*60)
        
        # Format for LLM
        summarize_with_llm(emails)
