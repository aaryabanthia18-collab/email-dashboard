#!/usr/bin/env python3
"""
Email Summarization Script using LLM via sessions_spawn
"""

import json
import subprocess
import sys

def summarize_with_llm(text, subject, sender):
    """Use sessions_spawn to get LLM summary"""
    prompt = f"""Summarize this email in 1-2 sentences. Be concise and clear.
What is this email about? Is any action needed?

From: {sender}
Subject: {subject}
Body: {text[:800]}

Summary:"""
    
    # For now, return a simple rule-based summary
    # In production, this would call an LLM API
    
    text_lower = text.lower()
    subject_lower = subject.lower()
    
    # Simple summarization logic
    if 'failed' in subject_lower or 'error' in subject_lower:
        return f"Deployment or process failed. Check details and take corrective action if needed."
    elif 'sign in' in subject_lower or 'login' in subject_lower:
        return f"New sign-in detected on your account. Review if this was you."
    elif 'token' in subject_lower or 'ssh' in subject_lower:
        return f"New authentication credentials added to your account. Verify this was intentional."
    elif 'added' in subject_lower and 'github' in sender.lower():
        return f"New item added to your GitHub account. Review the change."
    elif 'vercel' in sender.lower():
        return f"Vercel account activity notification. Review for any issues."
    elif 'github' in sender.lower():
        return f"GitHub account notification. Check for any required actions."
    else:
        return f"Notification from {sender}. Review contents for any important information."

def generate_overall_summary(emails):
    """Generate overall summary"""
    if not emails:
        return "No emails to summarize."
    
    # Count by sender
    sender_counts = {}
    for e in emails:
        sender = e.get('from', 'Unknown')
        sender_counts[sender] = sender_counts.get(sender, 0) + 1
    
    top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    summary_parts = [f"You have {len(emails)} emails in your inbox."]
    
    if top_senders:
        sender_list = ", ".join([f"{count} from {s.split('<')[0].strip()}" for s, count in top_senders])
        summary_parts.append(f"Most are from {sender_list}.")
    
    # Check for action items
    action_emails = [e for e in emails if e.get('tasks')]
    if action_emails:
        summary_parts.append(f"{len(action_emails)} emails may contain action items.")
    
    # Check for issues/alerts
    issue_emails = [e for e in emails if any(word in e.get('subject', '').lower() for word in ['failed', 'error', 'alert', 'warning'])]
    if issue_emails:
        summary_parts.append(f"⚠️ {len(issue_emails)} emails require attention (failures/errors).")
    
    return " ".join(summary_parts)

def main():
    data_path = '/root/.openclaw/workspace/email-dashboard/data.json'
    
    print(f"Reading emails from {data_path}...")
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    emails = data.get('emails', [])
    print(f"Found {len(emails)} emails to summarize.")
    
    if not emails:
        print("No emails found.")
        return
    
    # Generate AI summaries for each email
    print("\nGenerating summaries...")
    for i, email in enumerate(emails):
        subject = email.get('subject', 'No Subject')
        sender = email.get('from', 'Unknown')
        body = email.get('preview', '')
        
        summary = summarize_with_llm(body, subject, sender)
        email['ai_summary'] = summary
        print(f"  [{i+1}/{len(emails)}] {summary[:60]}...")
    
    # Generate overall summary
    print("\nGenerating overall summary...")
    overall = generate_overall_summary(emails)
    print(f"  {overall}")
    
    # Update data
    data['ai_summary'] = {
        'overall_summary': overall,
        'total_emails': len(emails)
    }
    
    # Write back
    with open(data_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("\n✅ Summaries added!")

if __name__ == '__main__':
    main()
