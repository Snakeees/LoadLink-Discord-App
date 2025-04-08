import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import random
from core.database import Discord, Room

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


class RoomSelect(discord.ui.Select):
    def __init__(self, is_guild: bool, page: int = 0):
        self.is_guild = is_guild
        self.rooms = Room.select().order_by(Room.label)
        self.page_size = 25
        
        # Calculate total pages properly
        self.total_pages = max((len(self.rooms) + self.page_size - 1) // self.page_size, 1)
        # Ensure page is within bounds
        self.current_page = max(0, min(page, self.total_pages - 1))
        
        # Get rooms for current page
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_rooms = self.rooms[start_idx:end_idx]
        
        # Create options, handle empty case
        self.room_map = {room.roomId: room.label for room in page_rooms}
        options = [
            discord.SelectOption(
                label=room.label,
                value=room.roomId,
            ) for room in page_rooms
        ] or [discord.SelectOption(label="No rooms available", value="none")]

        super().__init__(
            placeholder=f"Choose a laundry room (Page {self.current_page + 1}/{self.total_pages})...",
            min_values=1,
            max_values=1,
            options=options,
            disabled=not page_rooms,  # Disable if no rooms
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                "No rooms are available to select.", ephemeral=True
            )
            return

        discord_id = str(interaction.guild_id if self.is_guild else interaction.user.id)
        try:
            Discord.replace(discordId=discord_id, roomId=self.values[0]).execute()
            room_label = self.room_map[self.values[0]]
            await interaction.response.send_message(
                f"{'Server' if self.is_guild else 'Your'} default room has been set to: `{room_label}`",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Failed to set room: {str(e)}", ephemeral=True
            )


class RoomView(discord.ui.View):
    def __init__(self, is_guild: bool):
        super().__init__(timeout=180)  # 3 minute timeout
        self.is_guild = is_guild
        self.current_page = 0
        
        # Initialize select menu
        self.room_select = RoomSelect(is_guild, self.current_page)
        self.add_item(self.room_select)
        
        # Add navigation buttons only if multiple pages exist
        if self.room_select.total_pages > 1:
            self.add_item(PaginationButton(is_next=False))
            self.add_item(PaginationButton(is_next=True))

    async def on_timeout(self):
        # Disable all components when the view times out
        for item in self.children:
            item.disabled = True
        # Try to update the message if it still exists
        try:
            await self.message.edit(view=self)
        except:
            pass


class PaginationButton(discord.ui.Button):
    def __init__(self, is_next: bool):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Next ▶" if is_next else "◀ Previous",
            custom_id="next" if is_next else "prev"
        )
        self.is_next = is_next

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        select_menu = view.room_select
        
        # Calculate new page
        if self.is_next:
            new_page = (view.current_page + 1) % select_menu.total_pages
        else:
            new_page = (view.current_page - 1) % select_menu.total_pages
        
        # Update view with new select menu
        view.current_page = new_page
        view.remove_item(select_menu)
        view.room_select = RoomSelect(view.is_guild, new_page)
        view.add_item(view.room_select)
        
        # Move the new select menu to the first position
        view.children.insert(0, view.children.pop())
        
        await interaction.response.edit_message(view=view)


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")


@client.tree.command(
    name="set_server_room", 
    description="Set the default laundry room for this server"
)
@app_commands.checks.has_permissions(administrator=True)
async def set_server_room(interaction: discord.Interaction):
    view = RoomView(is_guild=True)
    await interaction.response.send_message(
        "Select a room for this server:", view=view, ephemeral=True
    )


@client.tree.command(
    name="set_user_room",
    description="Set your personal default laundry room"
)
async def set_room(interaction: discord.Interaction):
    view = RoomView(is_guild=False)
    await interaction.response.send_message(
        "Select your default room:", view=view, ephemeral=True
    )


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
