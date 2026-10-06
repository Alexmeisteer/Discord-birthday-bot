import json
import os
import discord
from datetime import datetime 
from pathlib import Path 
from zoneinfo import ZoneInfo
from discord import app_commands
from discord.ext import tasks 
from dotenv import load_dotenv

# Config
load_dotenv()

TOKEN=os.getenv("DISCORD_TOKEN")
GUILD_ID=int(os.getenv("GUILD_ID"))
BIRTHDAY_CHANNEL_ID=int(os.getenv("BIRTHDAY_CHANNEL_ID"))
BIRTHDAY_GIF_URL=os.getenv("BIRTHDAY_GIF_URL", "").strip()
TIMEZONE = ZoneInfo("Europe/Berlin")

# Birthday message will be sent at 8am CEST
SEND_FROM_HOUR = 8
BIRTHDAYS_FILE=Path("birthdays.json")
SENT_FILE=Path("sent_birthdays.json")
GUILD = discord.Object(id=GUILD_ID)


# JSON functions
def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

def save_json(path: Path, data: dict):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, enscure_ascii=False, indent=4)

def parse_birthday(date_string: str):
    """
    Expected format:
    20.01
    or 
    20.01.
    """
    date_string = date_string.strip().rstrip(".")

    # 29.02 is also viable then -> thanks Reddit
    try:
        date = datetime.strptime(f"{date_string}.2000", "%d.%m.%Y")
    except ValueError:
        return None

    return date.day, date.month

# Discord client



class BirthdayBot(discord.Client):
    async def setup_hook(self):
        await tree.sync(guild=GUILD)
        birthday_check.start() # start bday check automatically
        print("Slash commands are synced.")


intents = discord.Intents.default()
client = BirthdayBot(intents=intents)
tree = app_commands.CommandTree(client)
client = BirthdayBot(intents=intents)

#
# Events 
#

# Check for birthday
@tasks.loop(minutes=30)
async def birthday_check():
    now = datetime.now(TIMEZONE)
    if now.hour < SEND_FROM_HOUR: # no birthday messages before 8am CEST
        return
    birthdays = load_json(BIRTHDAYS_FILE)

    if not birthdays:
        return
    today_key = now.date().isoformat()
    sent_data = load_json(SENT_FILE)

    # current day entries
    already_sent = set(sent_data.get(today_key, []))
    channel = client.get_channel(BIRTHDAY_CHANNEL_ID)
    if channel is None:
        try:
            channel = await client.fetch_channel(BIRTHDAY_CHANNEL_ID)
        except discord.DiscordException as error:
            print(f"Channel could not be loaded: {error}")
            return
    for user_id, birthday in birthdays.items():
        is_birthday = (
            birthday["day"] == now.day
            and birthday["month"] == now.month # AND != and
        )
        if not is_birthday: continue
        if user_id in already_sent: continue

        message = (
            f"🎊🎊🎉🎉**HAPPY BIRTHDAY <@{user_id}>🎉🎉🎊🎊\n"
            f"🍰 We wish you an amazing day! 🎂"
        )
        # it looks very ugly otherwise, but you can add the GIF below the wishes
        if BIRTHDAY_GIF_URL:
            message += f"\n{BIRTHDAY_GIF_URL}"

        await channel.send(message, allowed_mentions=discord.AllowedMentions(users=True))
        already_sent.add(user_id)
        print(f"Birthday wishes for {birthday['name']} was sent.")

        # keep current day
        sent_data = {today_key: list(already_sent)}
        save_json(SENT_FILE, sent_data)

@birthday_check.before_loop
async def before_birthday_check():
    await client.await_until_ready()
    


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    print(f"Bot-ID: {client.user.id}")
    print("Birthdays are ready.")

# Add birthdays
@tree.command(
    name="add_birthday",
    description="Saves birthday of a person.",
    guild=GUILD
)

@app_commands.describe(
    person="Person, whose birthday shall be saved.",
    date="Birthdays have the format: DD.MM., for example: 27.02."
)
@app_commands.default_permissions(manage_guild=True)
async def add_birthday(
    interaction: discord.Interaction,
    person: discord.Member,
    date: str
):
    birthday=parse_birthday(date)

    # date error
    if birthday is None:
        await interaction.response.send_message(
            "Date is not valid. Try something like '30.06.'",
            ephemeral=True
        )
        return

    day, month = birthday
    birthdays = load_json(BIRTHDAYS_FILE)
    birthdays[str(person.id)] = {
        "name": person.display_name,
        "day": day,
        "month": month
    }

    save_json(BIRTHDAYS_FILE, birthdays)
    await interaction.response.send_message(
        f"Birthday of {person.mention} was set to "
        f"**{day:02d}.{month:02d}.**",
        ephemeral=True
    )

# remove birthday

@tree.command(
    name="remove_birthday",
    description="Removes a saved birthday.",
    guild=GUILD
)
@app_commands.describe(
    person="The person, whose birthday shall be removed."
)
@app_commands.default_permissions(manage_guild=True)
async def remove_birthday(
    interaction: discord.Interaction,
    person: discord.Member
):
    birthdays = load_json(BIRTHDAYS_FILE)
    user_id = str(person.id)
    # is person in list?
    if user_id not in birthdays:
        await interaction.response.send_message(
            f"There is no birthday entry for {person.mention}.",
            ephemeral=True
        )
        return
    # delete user
    del birthdays[user_id]
    save_json(BIRTHDAYS_FILE, birthdays)
    await interaction.response.send_message(
        f"{person.mention}'s birthday was removed.",
        ephemeral=True
    )

    # Show birthday list



    # Start bot 
    if not TOKEN:
        raise RuntimeError("Discord_TOKEN was not found in .env!")
    client.run(TOKEN)