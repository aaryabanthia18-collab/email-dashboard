#!/usr/bin/env python3
"""
Email Summarization Script using LLM

This script reads emails from data.json, generates AI summaries for each email,
and creates an overall summary of all emails using the Kimi API.
"""

import json
import os
import sys
from datetime import datetime
import requests

# API Configuration
KIMI_API_KEY = "sk-kimi-UeQQDSmk1jXIa28ZAmWdTcp3e5sfisBGLh2KjHDhOvdl8CW2oeKyxTl9gMbriDsP"
KIMI_API_URL = "https://api.kimi.com/coding/v1/messages"


def call_llm(prompt: str) -> str:
    """
    Call the Kimi LLM API to generate a summary.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "User-Agent": "Kimi Claw Plugin"
    }
    
    payload = {
        "model": "k2p5",
        "max_tokens": 512,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    response = requests.post(KIMI_API_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    
    # Extract the response content
    if "content" in data and len(data["content"]) > 0:
        return data["content"][0]["text"].strip()
    elif "message" in data and "content" in data["message"]:
        return data["message"]["content"].strip()
    else:
        raise RuntimeError(f"Unexpected response format: {data}")


def summarize_email(email: dict) -> str:
    """
    Generate a 1-2 sentence summary of a single email.
    """
    subject = email.get('subject', 'No Subject')
    sender = email.get('from', 'Unknown Sender')
    body = email.get('preview', '') or email.get('body', '')
    
    # Clean up the body text
    body = body.replace('\\r', ' ').replace('\\n', ' ').replace('\r', ' ').replace('\n', ' ').strip()
    if len(body) > 800:
        body = body[:800] + '...'
    
    prompt = f"""Summarize this email in 1-2 sentences. What is it about? What action is needed if any?

Subject: {subject}
From: {sender}
Body: {body}

Summary:"""
    
    try:
        summary = call_llm(prompt)
        return summary
    except Exception as e:
        print(f"    [Error: {str(e)[:50]}]")
        return f"[Error generating summary: {str(e)[:100]}]"


def generate_overall_summary(emails: list, email_summaries: list) -> str:
    """
    Generate an overall summary paragraph of all emails.
    """
    # Create a condensed view of all emails with their summaries
    email_overviews = []
    for email, summary in zip(emails, email_summaries):
        sender = email.get('from', 'Unknown')
        subject = email.get('subject', 'No Subject')[:60]
        summary_short = summary[:100] if len(summary) > 100 else summary
        email_overviews.append(f"- {sender}: {subject} - {summary_short}")
    
    overview_text = "\n".join(email_overviews[:20])
    
    prompt = f"""You are an email assistant. Write a concise paragraph (3-5 sentences) summarizing the overall themes and important items from these emails:

{overview_text}

Overall Summary:"""
    
    try:
        summary = call_llm(prompt)
        return summary
    except Exception as e:
        print(f"    [Error: {str(e)[:50]}]")
        return f"[Error generating overall summary: {str(e)[:100]}]"


def main():
    """
    Main function to process emails and generate summaries.
    """
    data_path = '/root/.openclaw/workspace/email-dashboard/data.json'
    
    # Read the email data
    print(f"Reading emails from {data_path}...")
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    emails = data.get('emails', [])
    print(f"Found {len(emails)} emails to summarize.\n")
    
    if not emails:
        print("No emails found. Exiting.")
        return
    
    # Generate summaries for each email
    print("Generating AI summaries for each email...")
    email_summaries = []
    
    for i, email in enumerate(emails):
        subject_short = email.get('subject', 'No Subject')[:45]
        print(f"  [{i+1}/{len(emails)}] {subject_short}...", end=" ", flush=True)
        summary = summarize_email(email)
        email['ai_summary'] = summary
        email_summaries.append(summary)
        print(f"✓")
    
    # Generate overall summary
    print("\nGenerating overall summary...")
    overall_summary = generate_overall_summary(emails, email_summaries)
    
    # Update the data structure
    data['ai_summary'] = {
        'overall_summary': overall_summary,
        'generated_at': datetime.now().isoformat(),
        'total_emails_summarized': len(emails)
    }
    
    # Write the updated data back
    print(f"\nWriting updated data to {data_path}...")
    with open(data_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("\n" + "="*60)
    print("✅ Done! AI summaries have been added to data.json")
    print("="*60)
    print(f"\n📧 OVERALL SUMMARY:\n{overall_summary}")
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
