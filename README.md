# Discord Verification Bot for Amazon FBA Community

This Discord bot guides new Amazon FBA community members through a 4-question verification process and sends their responses to a GoHighLevel webhook.

## Features

- **Automatic New Member Detection**: Detects when users join the server
- **Sequential Q&A Process**: Guides users through 4 Amazon FBA-related questions
- **User-Specific Responses**: Ensures only the tagged user can answer their questions
- **Role Assignment**: Automatically assigns "Verified" role upon completion
- **DM Confirmation**: Sends private confirmation message to verified users
- **Webhook Integration**: Sends verification data to GoHighLevel webhook
- **Error Handling**: Robust error handling for API failures and edge cases

## Setup Instructions

### 1. Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Copy the bot token
4. Enable the following bot permissions:
   - Send Messages
   - Manage Roles
   - Read Message History
   - Use Slash Commands
   - Add Reactions
   - Send Messages in Threads

### 2. Server Setup

1. Create a channel named `#✅-verify-access` in your Discord server
2. Ensure the bot has proper permissions in this channel
3. The bot will automatically create a "Verified" role if it doesn't exist

### 3. Environment Configuration

1. Copy `.env.example` to `.env`
2. Fill in your configuration:
   ```env
   DISCORD_BOT_TOKEN=your_actual_bot_token
   GOHIGHLEVEL_WEBHOOK_URL=https://your-webhook-url.com/webhook
   ```

### 4. Installation and Running

1. Install required packages:
   ```bash
   pip install discord.py aiohttp python-dotenv
   ```

2. Run the bot:
   ```bash
   python bot.py
   ```

## Verification Process

When a new user joins the server, the bot will:

1. Post a welcome message in the `#✅-verify-access` channel tagging the new user
2. The message includes a ✅ reaction for them to click
3. When they react with ✅, the bot sends them the first question via DM
4. They answer questions one by one through private DMs (only visible to them):
   - What interests you most about Amazon FBA?
   - Have you tried Amazon FBA before?
   - What's your biggest challenge with FBA right now?
   - Are you currently selling, or just researching?
5. Each answer is submitted privately via DM - no one else can see their responses
6. After all questions are completed, the bot automatically:
   - Assigns the "Verified" role
   - Sends a confirmation DM
   - Submits verification data to the GoHighLevel webhook

## Webhook Payload Format

The bot sends the following JSON structure to your GoHighLevel webhook:

```json
{
  "username": "JohnDoe#1234",
  "user_id": "1234567890123456789",
  "join_date": "2025-07-22T10:00:00Z",
  "answers": {
    "interest": "User's answer to question 1",
    "experience": "User's answer to question 2", 
    "challenge": "User's answer to question 3",
    "status": "User's answer to question 4"
  }
}
