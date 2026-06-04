"""
Chatbot Generator Module
Takes scraped data and generates:
1. knowledge.json - knowledge base
2. index.html    - standalone chatbot page
3. widget.js     - embeddable widget script
4. meta.json     - metadata
Uses OpenRouter API to build the system prompt
"""

import json
import os
import re
import time
import uuid
from datetime import datetime
import requests


GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated_chatbots")


class ChatbotGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"

    def generate(self, scraped_data: dict, chatbot_id: str, source_url: str) -> dict:
        """Generate all chatbot files from scraped data."""
        chatbot_dir = os.path.join(GENERATED_DIR, chatbot_id)
        os.makedirs(chatbot_dir, exist_ok=True)
        
        # Step 1: Build knowledge base + system prompt via LLM
        system_prompt = self._build_system_prompt(scraped_data)
        
        # Step 2: Extract brand info
        brand = self._extract_brand(scraped_data)
        
        # Step 3: Save knowledge.json
        knowledge = {
            "chatbot_id": chatbot_id,
            "source_url": source_url,
            "brand": brand,
            "system_prompt": system_prompt,
            "api_key": self.api_key,
            "created_at": datetime.now().isoformat(),
            "scraped_data_summary": {
                "title": scraped_data.get("title", ""),
                "services": scraped_data.get("services", [])[:10],
                "products": scraped_data.get("products", [])[:10],
                "contact": scraped_data.get("contact", {}),
                "about": scraped_data.get("about", "")[:500],
                "location": scraped_data.get("location", ""),
            }
        }
        
        with open(os.path.join(chatbot_dir, "knowledge.json"), "w", encoding="utf-8") as f:
            json.dump(knowledge, f, indent=2, ensure_ascii=False)
        
        # Step 4: Generate chatbot HTML
        chatbot_html = self._generate_chatbot_html(brand, chatbot_id)
        with open(os.path.join(chatbot_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(chatbot_html)
        
        # Step 5: Generate embeddable widget.js
        widget_js = self._generate_widget_js(brand, chatbot_id)
        with open(os.path.join(chatbot_dir, "widget.js"), "w", encoding="utf-8") as f:
            f.write(widget_js)
        
        # Step 6: Save meta
        meta = {
            "chatbot_id": chatbot_id,
            "source_url": source_url,
            "title": brand["name"],
            "created_at": datetime.now().isoformat(),
            "pages_scraped": scraped_data.get("pages_scraped", 1),
        }
        with open(os.path.join(chatbot_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        
        # Embed code for user to copy
        embed_code = self._generate_embed_code(chatbot_id)
        
        return {
            "files": [
                {"name": "knowledge.json", "description": "Knowledge base & system prompt"},
                {"name": "index.html", "description": "Standalone chatbot page"},
                {"name": "widget.js", "description": "Embeddable widget script"},
            ],
            "embed_code": embed_code,
            "brand": brand,
        }

    def _build_system_prompt(self, data: dict) -> str:
        """Use OpenRouter LLM to create an expert system prompt from scraped data."""
        
        # Prepare a summary for the LLM
        summary = f"""
Website: {data.get('base_url', '')}
Business Name: {data.get('title', 'Unknown')}
Description: {data.get('description', '')}
About: {data.get('about', '')[:600]}

Services Offered:
{chr(10).join(f'- {s}' for s in data.get('services', [])[:15])}

Products:
{chr(10).join(f'- {p}' for p in data.get('products', [])[:15])}

Contact Information:
{json.dumps(data.get('contact', {}), indent=2)}

Location: {data.get('location', '')}

Social Media: {', '.join(data.get('social_links', {}).keys())}

FAQ:
{chr(10).join(f'Q: {f["q"]}' for f in data.get('faq', [])[:10])}
"""
        
        prompt = f"""Based on this scraped website data, create a comprehensive and friendly system prompt for an AI customer support chatbot for this business.

{summary}

The system prompt should:
1. Give the AI a specific name and persona for this business
2. Include ALL the business information (services, products, contact details, location, hours if mentioned)
3. Tell it to be helpful, friendly, and professional
4. Instruct it to answer questions about the business accurately
5. Tell it to guide users toward contacting the business or taking action
6. Keep responses concise (2-4 sentences usually)
7. Tell it to say it doesn't have that information if asked something not in its knowledge
8. Include the complete contact details so it can share them

Write ONLY the system prompt, nothing else. Start with "You are [Name]..."
"""
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "Web Scraper Chatbot Builder"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.3
                },
                timeout=30
            )
            
            resp_data = response.json()
            if "choices" in resp_data:
                return resp_data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"  [!] LLM prompt generation failed: {e}")
        
        # Fallback system prompt
        return self._fallback_system_prompt(data)

    def _fallback_system_prompt(self, data: dict) -> str:
        name = data.get("title", "the company")
        contact = data.get("contact", {})
        email = contact.get("email", [""])[0] if contact.get("email") else ""
        phone = contact.get("phone", [""])[0] if contact.get("phone") else ""
        services = ", ".join(data.get("services", [])[:8])
        
        return f"""You are a helpful customer support assistant for {name}. 
You help visitors learn about our services and products, answer their questions, and guide them to take action.

Business: {name}
Website: {data.get('base_url', '')}
{f'Email: {email}' if email else ''}
{f'Phone: {phone}' if phone else ''}
{f'Services: {services}' if services else ''}
{f'Location: {data.get("location", "")}' if data.get("location") else ''}

Be friendly, professional, and concise. Keep answers to 2-4 sentences. 
If you don't know something, suggest the visitor contact us directly.
Always aim to help the visitor find what they need or connect with our team."""

    def _extract_brand(self, data: dict) -> dict:
        title = data.get("title", "Business Assistant")
        # Clean up title (remove taglines, domain names)
        name = re.sub(r'\s*[-|–]\s*.*$', '', title).strip() or title
        name = re.sub(r'\.(com|net|org|io|co).*$', '', name, flags=re.IGNORECASE).strip()
        
        contact = data.get("contact", {})
        email = contact.get("email", [""])[0] if contact.get("email") else ""
        phone = contact.get("phone", [""])[0] if contact.get("phone") else ""
        
        # Primary color heuristic from favicon/meta (default to nice blue)
        colors = {
            "primary": "#2563eb",
            "primary_dark": "#1d4ed8",
            "text_on_primary": "#ffffff"
        }
        
        return {
            "name": name,
            "full_title": title,
            "url": data.get("base_url", ""),
            "description": data.get("description", ""),
            "email": email,
            "phone": phone,
            "logo_url": data.get("logo_url", ""),
            "colors": colors,
            "bot_name": f"{name.split()[0]} Assistant" if name else "Assistant",
        }

    def _generate_chatbot_html(self, brand: dict, chatbot_id: str) -> str:
        """Generate a beautiful standalone chatbot HTML page."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{brand['bot_name']} - {brand['name']}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
  
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  
  :root {{
    --primary: {brand['colors']['primary']};
    --primary-dark: {brand['colors']['primary_dark']};
    --bg: #f8fafc;
    --surface: #ffffff;
    --border: #e2e8f0;
    --text: #0f172a;
    --text-muted: #64748b;
    --user-bubble: {brand['colors']['primary']};
    --bot-bubble: #f1f5f9;
  }}
  
  body {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    background: var(--bg);
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
  }}
  
  .chat-container {{
    width: 100%;
    max-width: 680px;
    height: min(700px, 90vh);
    background: var(--surface);
    border-radius: 20px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.12), 0 4px 16px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--border);
  }}
  
  .chat-header {{
    background: linear-gradient(135deg, var(--primary), var(--primary-dark));
    padding: 18px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: white;
    flex-shrink: 0;
  }}
  
  .bot-avatar {{
    width: 44px;
    height: 44px;
    background: rgba(255,255,255,0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    backdrop-filter: blur(4px);
    border: 2px solid rgba(255,255,255,0.3);
  }}
  
  .bot-info h3 {{
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }}
  
  .bot-info p {{
    font-size: 12px;
    opacity: 0.85;
    margin-top: 1px;
    font-weight: 400;
  }}
  
  .status-dot {{
    width: 7px;
    height: 7px;
    background: #4ade80;
    border-radius: 50%;
    display: inline-block;
    margin-right: 5px;
    animation: pulse 2s infinite;
  }}
  
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
  }}
  
  .header-right {{
    margin-left: auto;
    font-size: 11px;
    opacity: 0.7;
    text-align: right;
    line-height: 1.4;
  }}
  
  .messages {{
    flex: 1;
    overflow-y: auto;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    scroll-behavior: smooth;
  }}
  
  .messages::-webkit-scrollbar {{ width: 4px; }}
  .messages::-webkit-scrollbar-track {{ background: transparent; }}
  .messages::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
  
  .message {{
    display: flex;
    gap: 8px;
    max-width: 88%;
    animation: slideIn 0.2s ease;
  }}
  
  @keyframes slideIn {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  
  .message.user {{ flex-direction: row-reverse; margin-left: auto; }}
  
  .msg-avatar {{
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    flex-shrink: 0;
    margin-top: 2px;
  }}
  
  .message.bot .msg-avatar {{
    background: linear-gradient(135deg, var(--primary), var(--primary-dark));
    color: white;
  }}
  
  .message.user .msg-avatar {{
    background: #e2e8f0;
    color: var(--text-muted);
  }}
  
  .bubble {{
    padding: 11px 15px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.55;
    color: var(--text);
    background: var(--bot-bubble);
    max-width: 100%;
    word-wrap: break-word;
  }}
  
  .message.user .bubble {{
    background: var(--user-bubble);
    color: white;
    border-radius: 16px 16px 4px 16px;
  }}
  
  .message.bot .bubble {{
    border-radius: 16px 16px 16px 4px;
  }}
  
  .typing-indicator {{
    display: flex;
    gap: 4px;
    padding: 12px 16px;
    background: var(--bot-bubble);
    border-radius: 16px 16px 16px 4px;
    width: fit-content;
  }}
  
  .typing-indicator span {{
    width: 7px;
    height: 7px;
    background: var(--text-muted);
    border-radius: 50%;
    animation: typing 1.2s infinite;
  }}
  
  .typing-indicator span:nth-child(2) {{ animation-delay: 0.2s; }}
  .typing-indicator span:nth-child(3) {{ animation-delay: 0.4s; }}
  
  @keyframes typing {{
    0%, 60%, 100% {{ transform: translateY(0); opacity: 0.4; }}
    30% {{ transform: translateY(-5px); opacity: 1; }}
  }}
  
  .suggestions {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 0 16px 8px;
  }}
  
  .suggestion-chip {{
    padding: 7px 14px;
    background: transparent;
    border: 1.5px solid var(--primary);
    color: var(--primary);
    border-radius: 20px;
    font-size: 12.5px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }}
  
  .suggestion-chip:hover {{
    background: var(--primary);
    color: white;
    transform: translateY(-1px);
  }}
  
  .input-area {{
    padding: 12px 16px 16px;
    border-top: 1px solid var(--border);
    display: flex;
    gap: 10px;
    align-items: flex-end;
    background: var(--surface);
    flex-shrink: 0;
  }}
  
  .input-area textarea {{
    flex: 1;
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 14px;
    font-family: inherit;
    resize: none;
    outline: none;
    transition: border-color 0.15s;
    line-height: 1.45;
    max-height: 120px;
    color: var(--text);
    background: var(--bg);
  }}
  
  .input-area textarea:focus {{ border-color: var(--primary); background: white; }}
  .input-area textarea::placeholder {{ color: var(--text-muted); }}
  
  .send-btn {{
    width: 42px;
    height: 42px;
    border-radius: 12px;
    background: var(--primary);
    color: white;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
    flex-shrink: 0;
  }}
  
  .send-btn:hover {{ background: var(--primary-dark); transform: scale(1.05); }}
  .send-btn:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
  
  .send-btn svg {{ width: 18px; height: 18px; }}
  
  .powered-by {{
    text-align: center;
    font-size: 11px;
    color: var(--text-muted);
    padding: 6px;
    border-top: 1px solid var(--border);
    background: var(--bg);
  }}
  
  .powered-by a {{ color: var(--primary); text-decoration: none; font-weight: 500; }}
</style>
</head>
<body>
<div class="chat-container">
  <div class="chat-header">
    <div class="bot-avatar">🤖</div>
    <div class="bot-info">
      <h3>{brand['bot_name']}</h3>
      <p><span class="status-dot"></span>Online · Typically replies instantly</p>
    </div>
    <div class="header-right">
      Powered by<br><strong>{brand['name']}</strong>
    </div>
  </div>
  
  <div class="messages" id="messages"></div>
  
  <div class="suggestions" id="suggestions">
    <button class="suggestion-chip" onclick="sendSuggestion(this)">👋 What do you offer?</button>
    <button class="suggestion-chip" onclick="sendSuggestion(this)">📞 Contact info</button>
    <button class="suggestion-chip" onclick="sendSuggestion(this)">📍 Where are you located?</button>
    <button class="suggestion-chip" onclick="sendSuggestion(this)">💬 How can you help me?</button>
  </div>
  
  <div class="input-area">
    <textarea id="userInput" placeholder="Type your message..." rows="1" 
      onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
    <button class="send-btn" id="sendBtn" onclick="sendMessage()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"></line>
        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
      </svg>
    </button>
  </div>
  
  <div class="powered-by">
    Chatbot created by <a href="http://localhost:5000" target="_blank">Web Scraper Chatbot Builder</a>
  </div>
</div>

<script>
const CHATBOT_ID = '{chatbot_id}';
const API_BASE = window.location.origin;
let history = [];
let isLoading = false;

function init() {{
  const welcomeMsg = "Hello! 👋 I'm the {brand['bot_name']} for **{brand['name']}**. I'm here to help you with any questions about our services, products, or how to get in touch. What can I help you with today?";
  addMessage('bot', welcomeMsg);
}}

function addMessage(role, text) {{
  const messages = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = `message ${{role}}`;
  
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = role === 'bot' ? '🤖' : '👤';
  
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = formatMessage(text);
  
  div.appendChild(avatar);
  div.appendChild(bubble);
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}}

function formatMessage(text) {{
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}}

function showTyping() {{
  const messages = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message bot';
  div.id = 'typing';
  
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = '🤖';
  
  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.innerHTML = '<span></span><span></span><span></span>';
  
  div.appendChild(avatar);
  div.appendChild(indicator);
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}}

function hideTyping() {{
  const typing = document.getElementById('typing');
  if (typing) typing.remove();
}}

async function sendMessage() {{
  if (isLoading) return;
  const input = document.getElementById('userInput');
  const text = input.value.trim();
  if (!text) return;
  
  document.getElementById('suggestions').style.display = 'none';
  addMessage('user', text);
  history.push({{ role: 'user', content: text }});
  input.value = '';
  input.style.height = 'auto';
  
  isLoading = true;
  document.getElementById('sendBtn').disabled = true;
  showTyping();
  
  try {{
    const response = await fetch(`${{API_BASE}}/chatbot/${{CHATBOT_ID}}/chat`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ message: text, history: history.slice(-10) }})
    }});
    
    const data = await response.json();
    hideTyping();
    
    if (data.error) {{
      addMessage('bot', '⚠️ Sorry, I encountered an error. Please try again.');
    }} else {{
      addMessage('bot', data.reply);
      history.push({{ role: 'assistant', content: data.reply }});
    }}
  }} catch (e) {{
    hideTyping();
    addMessage('bot', '⚠️ Connection error. Please check your internet and try again.');
  }}
  
  isLoading = false;
  document.getElementById('sendBtn').disabled = false;
  input.focus();
}}

function sendSuggestion(btn) {{
  document.getElementById('userInput').value = btn.textContent.replace(/^[\\u{1F600}-\\u{1F6FF}\\s]*/u, '').trim();
  sendMessage();
}}

function handleKey(e) {{
  if (e.key === 'Enter' && !e.shiftKey) {{
    e.preventDefault();
    sendMessage();
  }}
}}

function autoResize(el) {{
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}}

init();
</script>
</body>
</html>"""

    def _generate_widget_js(self, brand: dict, chatbot_id: str) -> str:
        """Generate the embeddable widget JavaScript."""
        primary = brand['colors']['primary']
        primary_dark = brand['colors']['primary_dark']
        
        return f"""/**
 * {brand['name']} - AI Chatbot Widget
 * Generated by Web Scraper Chatbot Builder
 * Chatbot ID: {chatbot_id}
 * 
 * EMBED INSTRUCTIONS:
 * Add this line to your HTML before </body>:
 * <script src="http://localhost:5000/chatbot/{chatbot_id}/widget.js"><\/script>
 */

(function() {{
  'use strict';
  
  const CHATBOT_ID = '{chatbot_id}';
  const API_BASE = 'http://localhost:5000';
  const PRIMARY_COLOR = '{primary}';
  const PRIMARY_DARK = '{primary_dark}';
  const BOT_NAME = '{brand["bot_name"]}';
  const BRAND_NAME = '{brand["name"]}';
  
  // Inject styles
  const style = document.createElement('style');
  style.textContent = `
    #wcb-toggle {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, ${{PRIMARY_COLOR}}, ${{PRIMARY_DARK}});
      border: none;
      cursor: pointer;
      box-shadow: 0 6px 24px rgba(0,0,0,0.22);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      transition: transform 0.2s, box-shadow 0.2s;
      font-size: 26px;
    }}
    #wcb-toggle:hover {{
      transform: scale(1.08);
      box-shadow: 0 10px 32px rgba(0,0,0,0.28);
    }}
    #wcb-badge {{
      position: absolute;
      top: -2px;
      right: -2px;
      width: 18px;
      height: 18px;
      background: #ef4444;
      border-radius: 50%;
      font-size: 10px;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: sans-serif;
      font-weight: 700;
      border: 2px solid white;
    }}
    #wcb-container {{
      position: fixed;
      bottom: 100px;
      right: 24px;
      width: 380px;
      height: 560px;
      border-radius: 20px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.08);
      z-index: 9998;
      overflow: hidden;
      display: none;
      flex-direction: column;
      font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
      border: 1px solid #e2e8f0;
      animation: wcb-slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      background: #ffffff;
    }}
    @keyframes wcb-slideUp {{
      from {{ opacity: 0; transform: translateY(20px) scale(0.95); }}
      to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    #wcb-container.open {{ display: flex; }}
    #wcb-header {{
      background: linear-gradient(135deg, ${{PRIMARY_COLOR}}, ${{PRIMARY_DARK}});
      padding: 14px 16px;
      display: flex;
      align-items: center;
      gap: 10px;
      color: white;
      flex-shrink: 0;
    }}
    #wcb-header-avatar {{
      width: 38px; height: 38px;
      background: rgba(255,255,255,0.2);
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 18px; flex-shrink: 0;
    }}
    #wcb-header-info h4 {{ font-size: 14px; font-weight: 600; margin: 0; }}
    #wcb-header-info p {{ font-size: 11px; opacity: 0.85; margin: 2px 0 0; }}
    #wcb-close {{
      margin-left: auto;
      background: rgba(255,255,255,0.15);
      border: none; color: white; cursor: pointer;
      width: 28px; height: 28px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 16px; transition: background 0.15s;
    }}
    #wcb-close:hover {{ background: rgba(255,255,255,0.25); }}
    #wcb-messages {{
      flex: 1; overflow-y: auto; padding: 14px 12px;
      display: flex; flex-direction: column; gap: 10px;
      scroll-behavior: smooth;
      background: #f8fafc;
    }}
    #wcb-messages::-webkit-scrollbar {{ width: 3px; }}
    #wcb-messages::-webkit-scrollbar-thumb {{ background: #e2e8f0; border-radius: 4px; }}
    .wcb-msg {{
      display: flex; gap: 7px;
      max-width: 86%; animation: wcb-msgIn 0.2s ease;
    }}
    @keyframes wcb-msgIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .wcb-msg.user {{ flex-direction: row-reverse; margin-left: auto; }}
    .wcb-msg-av {{
      width: 26px; height: 26px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 12px; flex-shrink: 0; margin-top: 2px;
    }}
    .wcb-msg.bot .wcb-msg-av {{ background: ${{PRIMARY_COLOR}}; color: white; }}
    .wcb-msg.user .wcb-msg-av {{ background: #e2e8f0; }}
    .wcb-bubble {{
      padding: 9px 13px; border-radius: 14px;
      font-size: 13px; line-height: 1.5; word-wrap: break-word;
      background: #ffffff; color: #0f172a;
      border: 1px solid #e2e8f0;
    }}
    .wcb-msg.bot .wcb-bubble {{ border-radius: 14px 14px 14px 3px; }}
    .wcb-msg.user .wcb-bubble {{
      background: ${{PRIMARY_COLOR}}; color: white;
      border-color: ${{PRIMARY_COLOR}};
      border-radius: 14px 14px 3px 14px;
    }}
    .wcb-typing {{
      display: flex; gap: 3px; padding: 10px 13px;
      background: white; border-radius: 14px; width: fit-content;
      border: 1px solid #e2e8f0;
    }}
    .wcb-typing span {{
      width: 6px; height: 6px; background: #94a3b8;
      border-radius: 50%; animation: wcb-type 1.2s infinite;
    }}
    .wcb-typing span:nth-child(2) {{ animation-delay: 0.2s; }}
    .wcb-typing span:nth-child(3) {{ animation-delay: 0.4s; }}
    @keyframes wcb-type {{
      0%, 60%, 100% {{ transform: translateY(0); opacity: 0.4; }}
      30% {{ transform: translateY(-4px); opacity: 1; }}
    }}
    #wcb-input-area {{
      padding: 10px 12px 12px;
      border-top: 1px solid #e2e8f0;
      display: flex; gap: 8px; align-items: flex-end;
      background: white; flex-shrink: 0;
    }}
    #wcb-input {{
      flex: 1; border: 1.5px solid #e2e8f0;
      border-radius: 10px; padding: 9px 12px;
      font-size: 13px; font-family: inherit;
      resize: none; outline: none;
      transition: border-color 0.15s;
      background: #f8fafc; color: #0f172a;
      max-height: 90px; line-height: 1.4;
    }}
    #wcb-input:focus {{ border-color: ${{PRIMARY_COLOR}}; background: white; }}
    #wcb-input::placeholder {{ color: #94a3b8; }}
    #wcb-send {{
      width: 36px; height: 36px; border-radius: 10px;
      background: ${{PRIMARY_COLOR}}; color: white; border: none;
      cursor: pointer; display: flex; align-items: center;
      justify-content: center; flex-shrink: 0;
      transition: background 0.15s, transform 0.15s; font-size: 15px;
    }}
    #wcb-send:hover {{ background: ${{PRIMARY_DARK}}; transform: scale(1.05); }}
    #wcb-send:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
    #wcb-footer {{
      text-align: center; font-size: 10px; color: #94a3b8;
      padding: 5px; background: white; border-top: 1px solid #f1f5f9;
    }}
    @media (max-width: 480px) {{
      #wcb-container {{ width: calc(100vw - 16px); right: 8px; bottom: 90px; }}
      #wcb-toggle {{ bottom: 16px; right: 16px; }}
    }}
  `;
  document.head.appendChild(style);
  
  // Load Google Font
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600&display=swap';
  document.head.appendChild(link);
  
  // Create toggle button
  const toggle = document.createElement('button');
  toggle.id = 'wcb-toggle';
  toggle.innerHTML = '💬<div id="wcb-badge">1</div>';
  toggle.title = `Chat with ${{BOT_NAME}}`;
  
  // Create chat container
  const container = document.createElement('div');
  container.id = 'wcb-container';
  container.innerHTML = `
    <div id="wcb-header">
      <div id="wcb-header-avatar">🤖</div>
      <div id="wcb-header-info">
        <h4>${{BOT_NAME}}</h4>
        <p>● Online · Replies instantly</p>
      </div>
      <button id="wcb-close" title="Close">✕</button>
    </div>
    <div id="wcb-messages"></div>
    <div id="wcb-input-area">
      <textarea id="wcb-input" placeholder="Ask me anything..." rows="1"></textarea>
      <button id="wcb-send">➤</button>
    </div>
    <div id="wcb-footer">Powered by ${{BRAND_NAME}} AI Assistant</div>
  `;
  
  document.body.appendChild(toggle);
  document.body.appendChild(container);
  
  // State
  let isOpen = false;
  let isLoading = false;
  let history = [];
  
  function toggleChat() {{
    isOpen = !isOpen;
    container.classList.toggle('open', isOpen);
    toggle.innerHTML = isOpen ? '✕' : '💬';
    if (isOpen) {{
      document.getElementById('wcb-badge')?.remove();
      if (document.getElementById('wcb-messages').children.length === 0) {{
        addMessage('bot', `Hi there! 👋 I'm the AI assistant for ${{BRAND_NAME}}. How can I help you today?`);
      }}
      setTimeout(() => document.getElementById('wcb-input').focus(), 100);
    }}
  }}
  
  function addMessage(role, text) {{
    const msgs = document.getElementById('wcb-messages');
    const div = document.createElement('div');
    div.className = `wcb-msg ${{role}}`;
    div.innerHTML = `
      <div class="wcb-msg-av">${{role === 'bot' ? '🤖' : '👤'}}</div>
      <div class="wcb-bubble">${{text.replace(/\\n/g, '<br>').replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')}}</div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }}
  
  function showTyping() {{
    const msgs = document.getElementById('wcb-messages');
    const div = document.createElement('div');
    div.className = 'wcb-msg bot'; div.id = 'wcb-typing';
    div.innerHTML = `<div class="wcb-msg-av">🤖</div><div class="wcb-typing"><span></span><span></span><span></span></div>`;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }}
  
  async function sendMessage() {{
    if (isLoading) return;
    const input = document.getElementById('wcb-input');
    const text = input.value.trim();
    if (!text) return;
    
    addMessage('user', text);
    history.push({{ role: 'user', content: text }});
    input.value = ''; input.style.height = 'auto';
    isLoading = true;
    document.getElementById('wcb-send').disabled = true;
    showTyping();
    
    try {{
      const res = await fetch(`${{API_BASE}}/chatbot/${{CHATBOT_ID}}/chat`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ message: text, history: history.slice(-8) }})
      }});
      const data = await res.json();
      document.getElementById('wcb-typing')?.remove();
      const reply = data.error ? '⚠️ Sorry, something went wrong. Please try again.' : data.reply;
      addMessage('bot', reply);
      if (!data.error) history.push({{ role: 'assistant', content: reply }});
    }} catch(e) {{
      document.getElementById('wcb-typing')?.remove();
      addMessage('bot', '⚠️ Connection error. Please try again.');
    }}
    
    isLoading = false;
    document.getElementById('wcb-send').disabled = false;
  }}
  
  // Event listeners
  toggle.addEventListener('click', toggleChat);
  document.getElementById('wcb-close').addEventListener('click', toggleChat);
  document.getElementById('wcb-send').addEventListener('click', sendMessage);
  document.getElementById('wcb-input').addEventListener('keydown', (e) => {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMessage(); }}
  }});
  document.getElementById('wcb-input').addEventListener('input', (el) => {{
    el.target.style.height = 'auto';
    el.target.style.height = Math.min(el.target.scrollHeight, 90) + 'px';
  }});
  
}})();
"""

    def _generate_embed_code(self, chatbot_id: str) -> str:
        return f'<script src="http://localhost:5000/chatbot/{chatbot_id}/widget.js"></script>'
