#Code by Jaconah - https://github.com/Jaconah
import discord
from discord.ext import commands, tasks #Redundant? 
import requests
import json
import os
import re
from pathlib import Path #needed for data file 
from datetime import datetime, timedelta
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('bot_token')
target_channel_id = int(os.getenv('target_channel_id'))  # Convert to int since Discord needs it as integer


# Unifi
base_url = os.getenv('unifi_url')
username = os.getenv('unifi_username')
password = os.getenv('unifi_password')

# Config
number_of_days = int(os.getenv('number_of_days', 15))  # The 15 is a default if not found
delay_between_runs = int(os.getenv('delay_between_runs', 5))  # The 5 is a default if not found
verify_ssl = False #Since we access it locally this needs to be set to false. 


async def get_unifi_session():
    """Create an authenticated session with UniFi API with CSRF token"""
    session = requests.Session()
    session.verify = False

    initial_response = session.get(f"{base_url}", verify=verify_ssl)
    csrf_token = initial_response.headers.get("x-csrf-token")

    headers = {
        "x-csrf-token": csrf_token
    }

    auth_response = session.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        headers=headers,
        verify=verify_ssl
    )

    if auth_response.status_code != 200:
        print("Authentication failed")
        print("Response:", auth_response.content)
        return None, None

    csrf_token = auth_response.headers.get("x-csrf-token", csrf_token)
    headers["x-csrf-token"] = csrf_token

    return session, headers

async def check_client_list():
    """Connects to the Unifi API and pulls the active client list, loops though the data and determines if a discord ping is necessary."""
    session, headers = await get_unifi_session()
    if not session:
        return

    #Pulls data from the API
    clients_response = session.get(
        f"{base_url}/proxy/network/api/s/default/stat/sta",
        headers=headers,
        verify=verify_ssl
    )

    clients = clients_response.json()
    for client in clients["data"]:
        ping_needed = False

        mac = client["mac"]
        oui = client["oui"]
        name = client.get("name", "")
        ip = client.get("ip", "No IP, (possibly static)")
        network = client.get("network", "?") #Somehow got a "network" not found error.  Addeded a ? for now to prevent it, unsure how to replicate it. 
        client_id = client["_id"]
        hostname = client.get("hostname", "")

        #Attempts to pull a name for the device.
        if len(name) < 1 and len(hostname) > 1:
            name = hostname
        elif len(name) < 1 and len(hostname) < 1:
            name = "No DNS / custom name given"

        #Debug logging

        print("\n" + mac + " " + oui + " " + name + " " + ip + " " + network)
        
        ping_needed, last_seen_date, last_seen_days = await check_mac(mac, client_id)

        if ping_needed == True:
            
            if last_seen_days > number_of_days:
                message = (
                    f"```\n"
                    f"An old client has rejoined your network. It was last seen on {last_seen_date} which was {str(last_seen_days)} days ago\n"
                )
            else:
                message = (
                    f"```\n"
                    f"A new client has joined your network.\n"
                )

            message = message + (                        
                f"Client Name: {name}\n"
                f"MAC: {mac}\n"
                f"Vendor: {oui}\n"
                f"IP: {ip}\n"
                f"VLAN: {network}\n"
                f"```"
            )
            #Logic to send the message
            channel = bot.get_channel(target_channel_id)
            if channel:
                sent_message = await channel.send(message)
                await add_block_reaction(sent_message)


async def check_mac(client_mac, client_id):
    """Cycle though the locally stored JSON file to compare MAC's to see if this client has associted with the network before."""
    today = datetime.today()
    if not os.path.exists(data_file):
        print(f"File {data_file} does not exist.")
        datas = []
    else:
        try:
            with open(data_file, "r") as file:
                datas = json.load(file)
        except json.JSONDecodeError:
            print(f"Error decoding JSON file {data_file}.")
            message = "An error has occurred while decoding the stored JSON data_file, exiting."
            channel = bot.get_channel(target_channel_id)
            if channel:
                await channel.send(message)
            exit()
    #Determine if the client is old and if so when was it last seen.
    for data in datas:

        if data["mac"] == client_mac:
            last_seen_date_str = data["last_seen"]
            last_seen_date = datetime.strptime(last_seen_date_str, "%Y-%m-%d")
            days_difference = (today - last_seen_date).days
            
            # Update last_seen to today if client is seen again
            data["last_seen"] = today.strftime("%Y-%m-%d")
            
            with open(data_file, "w") as file:
                json.dump(datas, file, indent=4)

            # Determine if a ping is needed
            if days_difference > number_of_days:
                print("Client has not been seen recently")
                ping_needed = True
            else:
                print("Client was seen recently")
                ping_needed = False
            return ping_needed, last_seen_date_str, days_difference

    # If client is new, add it to the list
    print("Client is new")
    ping_needed = True
    new_client = {
        "mac": client_mac,
        "last_seen": today.strftime("%Y-%m-%d"),
        "client_id": client_id
    }
    datas.append(new_client)

    with open(data_file, "w") as file:
        json.dump(datas, file, indent=4)

    return ping_needed, today.strftime("%Y-%m-%d"), 0


async def rename_client(client_mac, new_name):
    """Looks up the client_mac in the data file to pull the unique Client ID in Unifi and post to the API to rename the client."""

    try:
        with open(data_file, "r") as file:
            stored_data = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading data file: {e}")
        return False

    # Find the client ID from stored data
    client_id = None
    for entry in stored_data:
        if entry["mac"] == client_mac:
            client_id = entry["client_id"]
            break

    if not client_id:
        print(f"Could not find stored Client ID for MAC: {client_mac}")
        return False

    # Create session and rename client
    session, headers = await get_unifi_session()
    if not session:
        return False

    rename_url = f"{base_url}/proxy/network/api/s/default/rest/user/{client_id}"
    rename_data = {
        "name": new_name,
        "client_id": client_id,
        "mac": client_mac
    }
    
    response = session.put(rename_url, json=rename_data, headers=headers)
    
    if response.status_code == 200:
        print(f"Client {client_mac} renamed successfully to {new_name}")
        return True
    else:
        print(f"Failed to rename client: {response.status_code}")
        print("Response content:", response.content)
        return False
    
async def block_client(client_mac):
    """Post to the Unfi API the MAC address and blocks the client"""
    session, headers = await get_unifi_session()
    if not session:
        return 401

    block_url = f"{base_url}/proxy/network/api/s/default/cmd/stamgr"
    block_data = {
        "cmd": "block-sta",
        "mac": client_mac
    }

    block_response = session.post(
        block_url,
        json=block_data,
        headers=headers,
        verify=verify_ssl
    )

    if block_response.status_code == 200:
        print("Client blocked successfully")
        message = "Client with MAC Adress " + client_mac + " was blocked sucessfully"

    else:
        print(f"Failed to block client: {block_response.status_code}")
        print("Response content:", block_response.content)
        message = "Failed to block client with MAC Adress " + client_mac

    #Logic to send the message
    channel = bot.get_channel(target_channel_id)
    if channel:
        sent_message = await channel.send(message)

    return block_response.status_code

# Create a bot instance with a command prefix and intents
intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
# Background task to check for new clients
@tasks.loop(minutes=delay_between_runs)
async def check_network():
    """Periodically checks UniFi network for new or returning clients."""
    await check_client_list()

# Bot event handlers
@bot.event
async def on_ready():
    """Called when bot successfully connects to Discord."""
    print(f"Bot is ready! Logged in as {bot.user.name}")
    check_network.start()

async def add_block_reaction(message):
    """Adds the block (stop sign) reaction to a message."""
    try:
        await message.add_reaction("🛑")
    except discord.HTTPException as e:
        print(f"Failed to add block reaction: {e}")

def get_mac_from_message(message):
    """Extracts MAC address from a message."""
    pattern = re.compile(r"(?:[0-9a-fA-F]:?){12}")
    matches = re.findall(pattern, message)
    return matches[0] if matches else None

@bot.event
async def on_reaction_add(reaction, user):
    """Handles when users add reactions - used for blocking clients."""
    # Ignore bot reactions
    if user.bot:
        return 
    
    # Only process reactions in target channel
    if reaction.message.channel.id == target_channel_id:
        print(f"{user.name} reacted with {reaction.emoji}")
        
        # Try to block client if MAC found
        if mac_address := get_mac_from_message(reaction.message.content):
            await block_client(mac_address)

@bot.event
async def on_message(message):
    """Handles message replies - used for renaming clients."""
    # Only process replies to bot messages in target channel
    if (message.channel.id == target_channel_id and 
        message.reference and 
        not message.author.bot):
        
        # Get the message being replied to
        original_message = await message.channel.fetch_message(message.reference.message_id)
        
        # If replying to bot's message, try to rename client
        if original_message.author == bot.user:
            if mac_address := get_mac_from_message(original_message.content):
                new_name = message.content.strip()
                if await rename_client(mac_address, new_name):
                    await message.add_reaction("✅")

#Startup Code

# Setup data file path
data_file = "data/stored_macs.json"

# Create data directory if it doesn't exist
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Create the JSON file with empty array if it doesn't exist
if not Path(data_file).exists():
    with open(data_file, "w") as file:
        json.dump([], file)

# Start the bot
bot.run(bot_token)