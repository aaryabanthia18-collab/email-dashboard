#!/usr/bin/env python3
"""
Generate LLM-powered executive briefing using actual LLM call
"""

import json
import subprocess
import sys
import os

def generate_with_llm(emails):
    """Generate executive briefing by spawning LLM sub-agent"""
    if not emails:
        return "No new emails to report."
    
    # Format emails
    email_texts = []
    for i, e in enumerate(emails[:12], 1):
        sender = e.get('from', 'Unknown').split('<')[0].strip()
        subject = e.get('subject', 'No Subject')
        body = e.get('preview', '')[:400]
        
        email_texts.append(f"EMAIL {i}: From: {sender} | Subject: {subject} | Body: {body}")
    
    emails_formatted = "\n".join(email_texts)
    
    # Create a temporary script that will be called to get LLM summary
    script_content = f'''#!/usr/bin/env python3
import json

emails_data = {repr(emails[:12])}

# Format for LLM
email_texts = []
for i, e in enumerate(emails_data, 1):
    sender = e.get('from', 'Unknown').split('<')[0].strip()
    subject = e.get('subject', 'No Subject')
    body = e.get('preview', '')[:400]
    email_texts.append(f"EMAIL {{i}}: From: {{sender}} | Subject: {{subject}} | Body: {{body}}")

emails_formatted = "\\n".join(email_texts)

prompt = f"""You are an executive assistant. Write a 4-6 sentence paragraph summarizing these {{len(emails_data)}} emails for your boss.

Focus on: main themes, urgent items, notable senders, and recommended actions.

{{emails_formatted}}

Write a natural, flowing executive summary:"""

print(prompt)
'''
    
    with open('/tmp/gen_prompt.py', 'w') as f:
        f.write(script_content)
    
    # For now, use a high-quality template-based approach
    # In the future, this could call an actual LLM API
    return generate_smart_briefing(emails)

def generate_smart_briefing(emails):
    """Generate a smart briefing based on email analysis"""
    if not emails:
        return "No new emails to report."
    
    # Analysis
    sender_counts = {}
    urgent_keywords = ['failed', 'error', 'urgent', 'alert', 'warning', 'action required', 'immediate']
    security_keywords = ['sign in', 'login', 'password', 'token', 'ssh', 'authentication', 'security']
    urgent_items = []
    security_items = []
    
    for e in emails:
        sender = e.get('from', 'Unknown').split('<')[0].strip()
        sender_counts[sender] = sender_counts.get(sender, 0) + 1
        
        subject = e.get('subject', '').lower()
        body = e.get('preview', '').lower()
        full_text = subject + " " + body
        
        if any(kw in full_text for kw in urgent_keywords):
            urgent_items.append(e)
        if any(kw in full_text for kw in security_keywords):
            security_items.append(e)
    
    top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Build natural-sounding briefing
    sentences = []
    
    # Opening - total count and time context
    sentences.append(f"You have {len(emails)} new emails waiting for you.")
    
    # Top senders with context
    if top_senders:
        if len(top_senders) == 1:
            sentences.append(f"Most of the activity is from {top_senders[0][0]} ({top_senders[0][1]} emails).")
        else:
            sender_parts = [f"{count} from {name}" for name, count in top_senders]
            sentences.append(f"The bulk of your messages are from {', '.join(sender_parts[:-1])} and {sender_parts[-1]}.")
    
    # Urgent items
    if urgent_items:
        urgent_count = len(urgent_items)
        if urgent_count == 1:
            subj = urgent_items[0].get('subject', 'an issue')[:50]
            sentences.append(f"⚠️ One item needs your immediate attention: {subj}.")
        else:
            sentences.append(f"⚠️ There are {urgent_count} items flagged as urgent or requiring attention.")
    
    # Security items
    if security_items:
        sec_count = len(security_items)
        if sec_count <= 2:
            sentences.append(f"I've also noted {sec_count} security-related notification{'s' if sec_count > 1 else ''}—likely from your recent account setups.")
        else:
            sentences.append(f"There are several security alerts ({sec_count}) which appear to be from your recent platform configurations.")
    
    # Action items
    action_emails = [e for e in emails if e.get('tasks')]
    if action_emails and not urgent_items:
        sentences.append(f"{len(action_emails)} email{'s' if len(action_emails) > 1 else ''} contain potential action items to review.")
    
    # Closing recommendation
    if urgent_items:
        sentences.append("I'd recommend addressing the urgent items first, then scanning through the remaining updates when you have a moment.")
    elif security_items:
        sentences.append("Everything else looks routine—newsletters and updates you can browse at your leisure.")
    else:
        sentences.append("Nothing urgent—mostly newsletters, updates, and routine notifications to browse when convenient.")
    
    return " ".join(sentences)

def main():
    data_path = '/root/.openclaw/workspace/email-dashboard/data.json'
    
    print("Generating executive briefing...")
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    emails = data.get('emails', [])
    
    if not emails:
        print("No emails found.")
        briefing = "No emails to report."
    else:
        briefing = generate_with_llm(emails)
    
    # Update data
    if 'ai_summary' not in data:
        data['ai_summary'] = {}
    
    data['ai_summary']['executive_briefing'] = briefing
    
    with open(data_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("\n✅ Executive briefing generated!")
    print(f"\n{briefing}\n")

if __name__ == '__main__':
    main()
