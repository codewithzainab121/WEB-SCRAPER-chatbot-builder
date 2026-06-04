"""
Web Scraper Chatbot Builder
Backend: Python 3.13 + Flask
LLM: OpenRouter API
"""

import os
import json
import re
import time
import uuid
import requests
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from scraper import WebScraper
from chatbot_generator import ChatbotGenerator

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated_chatbots")
os.makedirs(GENERATED_DIR, exist_ok=True)


@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/api/set-key", methods=["POST"])
def set_key():
    """Save OpenRouter API key for session."""
    data = request.json
    key = data.get("api_key", "").strip()
    if not key:
        return jsonify({"error": "API key is required"}), 400
    # Store in environment for this process
    os.environ["OPENROUTER_API_KEY"] = key
    return jsonify({"message": "API key saved successfully"})


@app.route("/api/scrape-and-build", methods=["POST"])
def scrape_and_build():
    """Main endpoint: scrape website and generate chatbot."""
    data = request.json
    url = data.get("url", "").strip()
    api_key = data.get("api_key", os.environ.get("OPENROUTER_API_KEY", "")).strip()
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    if not api_key:
        return jsonify({"error": "OpenRouter API key is required"}), 400
    
    # Add http if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        # Step 1: Scrape website
        scraper = WebScraper()
        scraped_data = scraper.scrape(url)
        
        if not scraped_data:
            return jsonify({"error": "Failed to scrape website. Check URL and try again."}), 400

        # Step 2: Generate chatbot files
        generator = ChatbotGenerator(api_key)
        chatbot_id = str(uuid.uuid4())[:8]
        result = generator.generate(scraped_data, chatbot_id, url)
        
        return jsonify({
            "success": True,
            "chatbot_id": chatbot_id,
            "scraped_summary": {
                "title": scraped_data.get("title", ""),
                "pages_scraped": scraped_data.get("pages_scraped", 1),
                "data_points": scraped_data.get("data_points", 0),
            },
            "files": result["files"],
            "embed_code": result["embed_code"],
            "preview_url": f"/chatbot/{chatbot_id}/preview",
            "widget_url": f"/chatbot/{chatbot_id}/widget.js"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chatbot/<chatbot_id>/preview")
def preview_chatbot(chatbot_id):
    """Serve chatbot preview page."""
    chatbot_dir = os.path.join(GENERATED_DIR, chatbot_id)
    if not os.path.exists(chatbot_dir):
        return "Chatbot not found", 404
    return send_from_directory(chatbot_dir, "index.html")


@app.route("/chatbot/<chatbot_id>/widget.js")
def serve_widget(chatbot_id):
    """Serve embeddable widget JS."""
    chatbot_dir = os.path.join(GENERATED_DIR, chatbot_id)
    if not os.path.exists(chatbot_dir):
        return "Widget not found", 404
    return send_from_directory(chatbot_dir, "widget.js", mimetype="application/javascript")


@app.route("/chatbot/<chatbot_id>/chat", methods=["POST"])
def chat(chatbot_id):
    """Chat endpoint for generated chatbots."""
    chatbot_dir = os.path.join(GENERATED_DIR, chatbot_id)
    knowledge_file = os.path.join(chatbot_dir, "knowledge.json")
    
    if not os.path.exists(knowledge_file):
        return jsonify({"error": "Chatbot not found"}), 404
    
    with open(knowledge_file, "r", encoding="utf-8") as f:
        knowledge = json.load(f)
    
    data = request.json
    user_message = data.get("message", "")
    history = data.get("history", [])
    api_key = knowledge.get("api_key", os.environ.get("OPENROUTER_API_KEY", ""))
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    # Build messages for LLM
    system_prompt = knowledge.get("system_prompt", "You are a helpful assistant.")
    messages = [{"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]} 
                for m in history[-10:]]  # last 10 messages
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Web Scraper Chatbot Builder"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30
        )
        
        resp_data = response.json()
        if "error" in resp_data:
            return jsonify({"error": resp_data["error"].get("message", "LLM error")}), 500
        
        reply = resp_data["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<chatbot_id>/<filename>")
def download_file(chatbot_id, filename):
    """Download generated files."""
    chatbot_dir = os.path.join(GENERATED_DIR, chatbot_id)
    return send_from_directory(chatbot_dir, filename, as_attachment=True)


@app.route("/api/list-chatbots")
def list_chatbots():
    """List all generated chatbots."""
    chatbots = []
    for cid in os.listdir(GENERATED_DIR):
        meta_file = os.path.join(GENERATED_DIR, cid, "meta.json")
        if os.path.exists(meta_file):
            with open(meta_file, "r") as f:
                meta = json.load(f)
            chatbots.append(meta)
    return jsonify({"chatbots": sorted(chatbots, key=lambda x: x.get("created_at", ""), reverse=True)})


if __name__ == "__main__":
    print("🚀 Web Scraper Chatbot Builder running at http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
