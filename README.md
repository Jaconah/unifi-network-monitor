# Unifi Network Monitor

A Discord bot that monitors your Unifi network for new devices and alerts when previously seen devices return after a specified time.

![Discord Bot](https://img.shields.io/badge/discord-bot-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🔔 **Near Real-time Monitoring**: Notifications when new devices connect to your network (configurable interval, 5 minutes by default)
- 🔄 **Returning Device Detection**: Alerts when known devices rejoin after extended absence
- 📝 **Device Management**: Rename devices directly through Discord replies
- 🚫 **Network Security**: Block unwanted devices with a simple reaction
- 🐳 **Flexible Deployment**: Run as a Docker container or standalone Python application

## Example Notification

```
A new client has joined your network.
Client Name: iPhone
MAC: 00:11:22:33:44:55
Vendor: Apple, Inc.
IP: 192.168.1.100
VLAN: Default
```

### Device Management Actions

| Action | Method | Description |
|--------|--------|-------------|
| Rename Device | Reply to notification with new name | Updates device name in Unifi Controller |
| Block Device | React with 🛑 to notification | Blocks device access to network |

## Prerequisites

- Discord Bot token with appropriate permissions
- Access to a Unifi Controller (local or remote)
- Docker (recommended) or Python 3.11 or higher

## Installation

### Discord Bot Setup

1. Visit the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a "New Application"
3. Navigate to the "Bot" section
4. Click "Add Bot" and copy the token
5. Enable required Privileged Gateway Intents:
   - Message Content Intent
   - Server Members Intent
6. Generate invite URL with these permissions:
   - View Channels
   - Send Messages
   - Add Reactions
   - Read Message History
7. Use the generated URL to invite the bot to your server
8. Enable Developer Mode in Discord:
   - Open Discord Settings
   - Go to App Settings > Advanced
   - Enable Developer Mode
9. Get your channel ID:
   - Right-click the channel you want notifications in
   - Select "Copy ID"
   - Save this ID for the `TARGET_CHANNEL_ID` in your `.env` file

### Unifi Controller API User Setup

For security best practices, create a dedicated local user for API access:

1. Log into your Unifi Controller dashboard
2. Go to Settings > Admins & Users
3. Click "Create New Admin"
4. Configure the account:
   - Set Username to something identifiable (e.g., "API_Monitor")
   - Set a strong password
   - Check "Restrict to Local Access Only"
   - Uncheck "Use a Predefined Role"
   - Under permissions:
     - Network: Set to "Full Management"
     - Protect: Set to "None"
     - Control Plane: Set to "None"
   - Save the credentials for use in the `.env` file

### Environment Configuration

Create a `.env` file with the following variables:

```env
BOT_TOKEN=your_discord_bot_token
TARGET_CHANNEL_ID=your_discord_channel_id
UNIFI_URL=https://YourControllerIP
UNIFI_USERNAME=your_unifi_username
UNIFI_PASSWORD=your_unifi_password
NUMBER_OF_DAYS=15
DELAY_BETWEEN_RUNS=5
```

#### Configuration Details

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BOT_TOKEN` | Discord bot authentication token | - | Yes |
| `TARGET_CHANNEL_ID` | Discord channel for notifications (Enable Developer Mode in Discord Settings > App Settings > Advanced, then right-click channel and "Copy ID") | - | Yes |
| `UNIFI_URL` | IP address of your Unifi Controller with https:// prefix | - | Yes |
| `UNIFI_USERNAME` | Unifi Controller username | - | Yes |
| `UNIFI_PASSWORD` | Unifi Controller password | - | Yes |
| `NUMBER_OF_DAYS` | Days threshold for returning devices | 15 | No |
| `DELAY_BETWEEN_RUNS` | Minutes between network checks | 5 | No |

### Deployment Options

#### Docker (Recommended)

1. Create `docker-compose.yml`:
```yaml
version: '3'
services:
  unifi-network-monitor:
    image: jaconah/unifi-network-monitor:latest
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    restart: unless-stopped
```

2. Deploy:
```bash
docker-compose up -d
```

#### Standalone Python

1. Clone the repository:
```bash
git clone https://github.com/y/unifi-network-monitor.git
cd unifi-network-monitor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the bot:
```bash
python UnifiNetworkMonitorBot.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Created by Ryan (Jaconah)
