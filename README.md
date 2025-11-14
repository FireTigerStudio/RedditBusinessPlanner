# Reddit Pain Point Planner

> AI-powered tool to discover business opportunities from Reddit pain points and generate actionable execution plans.

## Features

- **Search Reddit Posts**: Enter a subreddit and keyword to find top-voted posts from the past year
- **AI-Generated Plans**: Click "Generate Execution Plan" to create structured business plans using Mistral AI
- **Structured Output**: Get pain point analysis, target users, 3 validation experiments, and a 10-step checklist
- **Export Options**: Copy Markdown or download as PDF
- **Token Quota Management**: 100,000 daily AI tokens (resets at UTC midnight)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/FireTigerStudio/RedditBusinessPlanner.git
cd RedditBusinessPlanner
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your Mistral API key:

```env
MISTRAL_API_KEY=your-mistral-api-key-here
FLASK_SECRET_KEY=your-random-secret-key
MISTRAL_MODEL=mistral-large-latest
DAILY_TOKEN_LIMIT=100000
```

### 4. Run the Application

```bash
python app.py
```

Visit http://localhost:5001

## How It Works

1. **Search**: Enter a subreddit (e.g., "Entrepreneur") and keyword (e.g., "problem")
2. **Browse**: View the top 10 highest-upvoted posts from the past year
3. **Select**: Click on a post to view its full content
4. **Generate**: Click "Generate Execution Plan" to create an AI-powered business plan
5. **Export**: Copy the Markdown or download as PDF

## Tech Stack

- **Backend**: Python Flask
- **AI**: Mistral AI API (mistral-large-latest)
- **Reddit API**: Public RSS + JSON endpoints (no authentication required)
- **Frontend**: HTML, CSS, JavaScript with modern UI design

## Privacy & Security

- Your Mistral API key is stored in `.env` (never committed to Git)
- `.gitignore` protects sensitive files
- API key is only used server-side
- No user data is stored

## Token Management

- Daily limit: 100,000 tokens
- Resets at UTC midnight (00:00)
- Token estimation: ~4 characters = 1 token
- Shared across all users

## Deployment

### Cloudflare Pages

1. Push code to GitHub
2. Connect repository in Cloudflare Pages
3. Add environment variables in Cloudflare dashboard
4. Deploy automatically on push to `main`

### Environment Variables for Production

```
MISTRAL_API_KEY=your-api-key
FLASK_SECRET_KEY=random-secret-key
DAILY_TOKEN_LIMIT=100000
MISTRAL_MODEL=mistral-large-latest
```

## Notes

- Reddit data fetched via public RSS feed and JSON API
- No Reddit authentication required
- 2-second delay between requests to avoid rate limiting
- Token counting is approximate (characters ÷ 4)

## License

MIT License - feel free to use and modify!

## Contributing

Contributions welcome! Feel free to open issues or submit pull requests.

---

Built with ❤️ by [FireTigerStudio](https://github.com/FireTigerStudio)
