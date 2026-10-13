# Contributing to NotifAI Enterprise 🎃

First off — thank you for taking the time to contribute! NotifAI is an **open-source AI agent** and every contribution helps. This project was built for **Hacktoberfest 2026** with the theme *"AI belongs to everyone"*.

---

## 🚀 How to Get Started

### 1. Fork & Clone
```bash
git clone https://github.com/<YOUR_USERNAME>/NotifAI-Agent.git
cd NotifAI-Agent/NotifAI_Enterprise
```

### 2. Set Up Environment
```bash
# Python engine
cd engine_python
cp .env.example .env
# Fill in your SARVAM_API_KEY in .env

# Node.js broker
cd ../broker_nodejs
cp .env.example .env
npm install
```

### 3. Run Locally with Docker
```bash
docker compose up -d
```

Open `http://localhost:3000`, scan the QR with WhatsApp, and you're live!

---

## 🛠️ What Can You Contribute?

Check open issues labeled:
- 🟢 `good first issue` — perfect for beginners
- 🆘 `help wanted` — maintainer is actively waiting for help
- 🎃 `hacktoberfest` — specifically highlighted for Hacktoberfest 2026

### Ideas for Contributions
| Area | Examples |
|------|---------|
| **New Features** | Add Telegram bot support, SMS/email notifications |
| **UI** | Build a web dashboard to view extracted notices |
| **Testing** | Add pytest tests for `agent.py` LLM pipeline |
| **Documentation** | Windows Docker setup guide, Hindi README |
| **AI** | Support more Sarvam STT languages, add entity extraction |
| **Integration** | Connect to Microsoft Teams, Slack, or Notion |

---

## 📐 Code Style Guidelines

- **Python**: Follow PEP8, use type hints where possible
- **JavaScript**: Use `const`/`let`, async/await, ES6+
- **Commits**: Write clear, descriptive commit messages
  - ✅ `feat: add Telegram bot webhook support`
  - ✅ `fix: handle voice note download retry on EAI_AGAIN`
  - ❌ `update stuff`

---

## 🔒 Security Rules (Critical!)

**Never commit:**
- `.env` files or API keys
- `token.json` or `langcredentials.json`
- `.wwebjs_auth/` session folders
- Any personal WhatsApp data

All secrets are in `.gitignore`. Use `.env.example` as the template.

---

## 📬 Pull Request Process

1. Create a branch: `git checkout -b feat/your-feature-name`
2. Make your changes
3. Test locally with Docker
4. Open a PR with a clear description of what you changed and why
5. Link the related issue in your PR description

We review all PRs within 48 hours. Thank you! 🙏
