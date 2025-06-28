# 🚀 Getting Started

## ⚡ Quick Start (F5 to Launch)

### Prerequisites
- **Python 3.11+** installed
- **Poetry** installed (`pip install poetry`)
- **VS Code** (recommended)

### Setup Steps

1. **Clone and enter the project**
   ```bash
   git clone <your-repo-url>
   cd ai-oncall
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Create environment configuration**
   ```bash
   cp .env.example .env  # or create .env file
   ```

4. **Set required environment variables in `.env`**
   ```bash
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Slack Configuration (optional for API-only testing)
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_SIGNING_SECRET=your_slack_signing_secret
   SLACK_SOCKET_MODE=TRUE
   SLACK_APP_TOKEN=xapp-your-app-token
   
   # Optional: Specify channel to monitor
   SLACK_CHANNEL_ID=C1234567890
   ```

5. **Launch with F5**
   - Open project in VS Code
   - Press **F5** to start debugging
   - Bot will be available at `http://localhost:8000`

## 🎯 Available Launch Configurations

Press **Ctrl+Shift+P** → "Debug: Select and Start Debugging" to choose:

- **Debug AI OnCall Bot** (Default F5) - Full debugging with detailed logs
- **Debug AI OnCall Bot (Production Mode)** - Production-like environment  
- **Run Tests** - Execute test suite
- **Debug Specific Test** - Debug the currently open test file

## 🧪 Quick Test

Once running, test the API endpoint:

```bash
curl -X POST http://localhost:8000/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, can you help me?",
    "channel_type": "api",
    "user_id": "test_user",
    "channel_id": "test_channel"
  }'
```

## 📚 Knowledge Base Setup

Add documents to the `knowledge-base/` folder:
```bash
# Add your .md or .txt files
cp your-docs/*.md knowledge-base/
```

The bot will automatically index them on startup.

## 🔧 Configuration

- **Workflows**: Edit `config/flow.yaml` to customize bot behavior
- **Environment**: All settings in `.env` file
- **Knowledge Base**: Add documents to `knowledge-base/` directory

## ✅ That's It!

Your AI OnCall Bot is now running and ready to help your team. Press **F5** anytime to launch and start debugging!
