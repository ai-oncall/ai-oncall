# AI OnCall Bot

A multi-channel, AI-powered assistant for handling support, information, and action requests via Slack, Teams, Discord, Email, and more. Built with a channel-agnostic architecture, OpenAI, and YAML-based workflows.

## 📚 Documentation
See the [docs/](./docs/) folder for:
- Project overview
- Architecture
- Technology stack
- Phase-by-phase implementation

## 🚀 Features
- Pluggable channel adapters (Slack, Teams, etc.)
- AI-powered request classification and response
- YAML workflow automation
- High test coverage and modern Python tooling

## 🏁 Quick Start

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Setup environment:**
   ```bash
   cp env .env
   # Edit .env with your API keys
   ```

3. **Run the application:**
   ```bash
   poetry run python -m src.main
   ```

4. **Test the API:**
   ```bash
   curl -X POST "http://localhost:8000/process-message" \
     -H "Content-Type: application/json" \
     -d '{"message": "Help me with a server issue"}'
   ```

## 🔧 Configuration

The application uses a single `.env` file for all configuration. For production, override environment variables through your CI/CD system.

**Key Variables:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_BASE_URL`: Optional proxy URL for corporate environments
- `DEBUG`: Set to `true` for development, `false` for production

See [docs/phases/phase-1-foundation.md](./docs/phases/phase-1-foundation.md) for detailed documentation. 