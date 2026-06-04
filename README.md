# 🕷️ Web Scraper Chatbot Builder

Build AI-powered customer support chatbots from ANY website — automatically.

## ✨ What It Does

1. **Paste a URL** → The tool scrapes up to 8 pages
2. **AI processes data** → Extracts services, products, contact info, location, FAQ
3. **Generates chatbot** → Creates a trained chatbot with custom system prompt
4. **Deploy instantly** → Get an embeddable widget for any webpage

---

## 🚀 Quick Setup (Python 3.13 + VS Code)

### 1. Clone / Extract Project

```
web-scraper-chatbot-builder/
├── app.py                    ← Flask backend
├── scraper.py                ← Web scraping engine
├── chatbot_generator.py      ← Chatbot file generator
├── requirements.txt          ← Python dependencies
├── templates/
│   └── index.html            ← Dashboard UI
├── static/                   ← Static assets
└── generated_chatbots/       ← Auto-created chatbot output
```

### 2. Create Virtual Environment

```bash
# In VS Code terminal (Ctrl + `)
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Get OpenRouter API Key

1. Go to [https://openrouter.ai/keys](https://openrouter.ai/keys)
2. Sign up / log in
3. Create a new API key
4. Copy it (starts with `sk-or-v1-...`)

> 💡 OpenRouter gives free credits. GPT-4o-mini is very cheap (~$0.0001/message).

### 5. Run the Server

```bash
python app.py
```

Open your browser: **http://localhost:5000**

---

## 🎯 How to Use

1. **Enter your OpenRouter API Key** in the dashboard
2. **Paste any website URL** (e.g., `https://acme-company.com`)
3. **Click "Scrape & Build Chatbot"**
4. Wait 20–60 seconds while it:
   - Scrapes the homepage and key pages
   - Extracts all business data
   - Generates AI system prompt
   - Creates chatbot files
5. **Preview your chatbot** — fully functional!
6. **Copy the embed code** and paste into any HTML page

---

## 📦 Generated Files (per chatbot)

Each chatbot gets its own folder in `generated_chatbots/`:

| File | Purpose |
|------|---------|
| `index.html` | Standalone chatbot page |
| `widget.js` | Embeddable widget script |
| `knowledge.json` | Knowledge base + system prompt |
| `meta.json` | Metadata (URL, date, etc.) |

---

## 🔌 Embedding on a Website

After building your chatbot, copy the embed code:

```html
<script src="http://localhost:5000/chatbot/CHATBOT_ID/widget.js"></script>
```

Paste it before `</body>` in any HTML file. The chat button will appear in the bottom-right corner.

### For Production Deployment

Replace `http://localhost:5000` with your actual server URL:
```html
<script src="https://your-server.com/chatbot/CHATBOT_ID/widget.js"></script>
```

---

## 🛠️ VS Code Tips

- Install **Python** extension for IntelliSense
- Install **REST Client** extension to test API endpoints
- Use `Ctrl + \`` to open integrated terminal
- Set breakpoints in `scraper.py` for debugging

---

## ⚙️ Configuration

### Change Scraping Limits

In `scraper.py`:
```python
self.max_pages = 8     # Max pages to scrape (increase for bigger sites)
self.timeout = 15      # Seconds before giving up on a page
```

### Change AI Model

In `chatbot_generator.py`:
```python
"model": "openai/gpt-4o-mini"  # Change to any OpenRouter model
```

Popular alternatives:
- `anthropic/claude-3-haiku`
- `openai/gpt-4o`  
- `mistralai/mistral-7b-instruct` (free tier)

---

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard UI |
| POST | `/api/scrape-and-build` | Main: scrape + generate chatbot |
| POST | `/chatbot/:id/chat` | Chat with generated chatbot |
| GET | `/chatbot/:id/preview` | Preview chatbot |
| GET | `/chatbot/:id/widget.js` | Embeddable widget |
| GET | `/api/list-chatbots` | List all chatbots |
| GET | `/api/download/:id/:file` | Download chatbot file |

---

## 🐛 Troubleshooting

**"Failed to scrape website"**
- Check the URL is correct and publicly accessible
- Some sites block scrapers — try adding `www.` or removing it
- Check if site requires JavaScript (this scraper handles static HTML)

**"LLM error"**
- Verify your OpenRouter API key is correct
- Check you have credits: [openrouter.ai](https://openrouter.ai)

**Port already in use**
```bash
python app.py  # Default is port 5000
# Or change in app.py: app.run(port=5001)
```

---

## 📄 License

MIT — Use freely for personal and commercial projects.
