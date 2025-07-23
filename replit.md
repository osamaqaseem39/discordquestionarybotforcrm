# Discord FBA Verification Bot

## Overview

This is a Discord bot designed for Amazon FBA communities that automates the member verification process. The bot guides new members through a 4-question verification sequence and integrates with GoHighLevel via webhooks to store verification data. Upon successful completion, members receive the "Verified" role and can access the community.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Architecture
- **Single-file Python application** (`bot.py`) using the discord.py library
- **Event-driven architecture** responding to Discord events (member joins, messages)
- **Session-based verification system** tracking individual user progress
- **Webhook integration** for external data submission to GoHighLevel

### Technology Stack
- **Python 3.x** as the primary runtime
- **discord.py** for Discord API integration
- **aiohttp** for HTTP requests to webhooks
- **python-dotenv** for environment variable management
- **asyncio** for asynchronous operations

## Key Components

### 1. VerificationBot Class
- Extends `commands.Bot` from discord.py
- Manages bot lifecycle and event handling
- Maintains in-memory verification sessions dictionary
- Configures Discord intents for message content and member events
- Uses slash commands with private modal popups for user interaction

### 2. VerificationModal Class  
- **Private UI Component**: Discord modal popup that only the user can see
- **Question Display**: Shows one question at a time in a popup form
- **Answer Collection**: Collects responses privately without public visibility
- **Sequential Flow**: Users must use `/verify` command for each question

### 3. Verification Session Management
- **Session Storage**: In-memory dictionary tracking user verification state
- **Session Data**: Stores current step, collected answers, guild ID, and join date
- **User-specific Responses**: Ensures only the intended user can respond to their questions
- **Private Processing**: All interactions happen through private modals

### 4. Question Flow System
- **Private Q&A Process**: 4 predefined Amazon FBA-related questions via popups
- **Step-by-step Progression**: Users must complete each question before proceeding
- **Hidden Responses**: No answers are visible in public channels
- **Command-based Interaction**: Users type `/verify` to continue to next question

### 5. Role Management
- **Automatic Role Creation**: Creates "Verified" role if it doesn't exist with proper positioning
- **Multiple Assignment Methods**: Tries direct role assignment and member editing approaches
- **Admin Notification System**: Automatically notifies admins if role assignment fails
- **Permission Handling**: Enhanced error handling with fallback to manual assignment
- **Graceful Failures**: Continues verification process even if role assignment fails

## Data Flow

### Verification Process Flow
1. **Member Join Detection**: Bot detects new member joining the server
2. **Session Initialization**: Creates verification session in memory
3. **Channel Welcome Message**: Posts welcome message in #✅-verify-access channel with user mention
4. **Reaction Trigger**: User clicks ✅ reaction to start verification process
5. **Private DM Questions**: Bot sends questions one by one via private DMs
6. **Sequential DM Responses**: User replies to DMs, responses invisible to others
7. **Answer Collection**: Responses stored privately, never shown in public channels
8. **Data Submission**: Sends collected data to GoHighLevel webhook
9. **Role Assignment**: Grants "Verified" role and sends confirmation DM

### Data Structure
```
Verification Session: {
    user_id: {
        'step': int,           # Current question (0-3)
        'answers': [],         # Collected responses
        'channel_id': int,     # Verification channel ID
        'join_date': datetime  # When user joined
    }
}
```

### Webhook Payload
- User information (username, ID, join date)
- Question responses mapped to specific keys
- Formatted JSON structure for GoHighLevel consumption

## External Dependencies

### Discord API Integration
- **Bot Permissions Required**:
  - Send Messages
  - Manage Roles
  - Read Message History
  - Use Slash Commands
  - Add Reactions
  - Send Messages in Threads

### GoHighLevel Webhook
- **HTTP POST Integration**: Sends verification data upon completion
- **Error Handling**: Manages webhook failures gracefully
- **Data Format**: JSON payload with user and response data

### Environment Variables
- `DISCORD_BOT_TOKEN`: Discord bot authentication token
- `GOHIGHLEVEL_WEBHOOK_URL`: Target webhook endpoint

## Deployment Strategy

### Local Development
- Environment configuration via `.env` file
- Manual dependency installation with pip
- Direct Python execution for testing

### Production Considerations
- **In-memory Session Storage**: Sessions lost on bot restart
- **Single Instance Deployment**: No clustering or horizontal scaling
- **Error Recovery**: Basic error handling for API failures
- **Logging**: Console-based logging for debugging

### Scalability Limitations
- Sessions stored in memory (not persistent)
- Single-threaded verification processing
- No database persistence layer
- Limited to single Discord server deployment

### Security Features
- Environment variable isolation for sensitive data
- User-specific response validation
- Permission-based channel access control
- Bot token security through environment variables

## Key Architectural Decisions

### In-Memory Session Management
- **Problem**: Need to track individual user verification progress
- **Solution**: Dictionary-based session storage in bot memory
- **Pros**: Simple implementation, fast access
- **Cons**: Data lost on restart, not scalable across instances

### Sequential Question Flow
- **Problem**: Need structured verification process
- **Solution**: Step-by-step progression through predefined questions
- **Pros**: Clear user experience, easy to modify questions
- **Cons**: Inflexible flow, requires completion in order

### Webhook Integration Pattern
- **Problem**: Need to send verification data to external CRM
- **Solution**: HTTP webhook POST on verification completion
- **Pros**: Loose coupling, standard integration method
- **Cons**: No built-in retry mechanism, potential data loss on failure

### Single-File Architecture
- **Problem**: Need simple, maintainable codebase
- **Solution**: All logic contained in single `bot.py` file
- **Pros**: Easy to understand and deploy
- **Cons**: Limited modularity, harder to test individual components