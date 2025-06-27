🚀 RENDER DEPLOYMENT GUIDE FOR YOUR BOT

1. Create a GitHub repository and upload these files.
2. Go to https://render.com and create an account.
3. Click "New" > "Web Service".
4. Connect your GitHub and select the repo.
5. Fill in:
   - Runtime: Python
   - Build Command: pip install -r requirements.txt
   - Start Command: python bot.py
6. Add your environment variables (from .env.example) in the "Environment" tab.
7. Deploy!

The bot will now run 24/7 and tweet + post on Discord when titles change.