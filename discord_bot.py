import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()


class MyClient(discord.Client):
    def __init__(self):
        # Initialize with all intents since we're using slash commands
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        await self.tree.sync()


client = MyClient()


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")


@client.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000)
    await interaction.response.send_message(f"Pong! 🏓 Latency: {latency}ms")


@client.tree.command(name="hello", description="Get a greeting from the bot")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello {interaction.user.name}! 👋")


@client.tree.command(
    name="roll", description="Roll a dice with specified number of sides"
)
async def roll(interaction: discord.Interaction, sides: int):
    if sides < 1:
        await interaction.response.send_message(
            "Please specify a positive number of sides!", ephemeral=True
        )
        return

    result = random.randint(1, sides)
    await interaction.response.send_message(f"🎲 You rolled a {result} (1-{sides})!")


@client.tree.command(name="random_color", description="Get a random color")
async def random_color(interaction: discord.Interaction):
    color = discord.Color.random()
    embed = discord.Embed(
        title="Random Color",
        description=f"Hex: #{hex(color.value)[2:].zfill(6)}",
        color=color,
    )
    await interaction.response.send_message(embed=embed)


client.run(os.getenv("DISCORD_TOKEN"))
