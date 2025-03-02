import nextcord
from nextcord.ext import commands, tasks
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import asyncio
import os
import itertools
import aiohttp
import datetime
import io

intents = nextcord.Intents.default()
intents.members = True
intents.messages = True  # Required to track messages
import nextcord
import json
from nextcord.ui import Button, View

intents = nextcord.Intents.default()
intents.message_content = True 
intents.voice_states = True
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Initialize Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

queues = {}

# Define the file to store warnings and ticket stats
warns_file = "warns.json"
ticket_stats_file = "ticket_stats.json"

# Load the saved warns and stats from files, if they exist
def load_json(filename, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return default

def save_json(data, filename):
    try:
        # Create a backup before saving
        if os.path.exists(filename):
            backup_filename = f"{filename}.backup"
            with open(filename, "r") as src, open(backup_filename, "w") as dst:
                dst.write(src.read())

        # Now save the new data
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving to {filename}: {e}")
        return False

# Function to record a user's participation in a ticket
def record_ticket_participation(user_id):
    user_id = str(user_id)  # Ensure it's a string for JSON
    if user_id not in ticket_stats:
        ticket_stats[user_id] = {
            "tickets_claimed": 0,
            "tickets_closed": 0,
            "tickets_participated": 0
        }

    # Increment participation count
    if "tickets_participated" not in ticket_stats[user_id]:
        ticket_stats[user_id]["tickets_participated"] = 0
    ticket_stats[user_id]["tickets_participated"] += 1

    # Save the updated stats
    save_json(ticket_stats, ticket_stats_file)

# Load data using the new function
warns = load_json(warns_file)
ticket_stats = load_json(ticket_stats_file)


status_messages = itertools.cycle([
    "https://discord.gg/mXT9pf5Nh4",
    "BEST AG MACRO",
    "https://discord.gg/mXT9pf5Nh4",
    "BEST AG MACRO"
])

@bot.event
async def on_ready():
    """Starts rotating status when bot is online"""
    change_status.start()
    print(f"Bot is online as {bot.user}")

@tasks.loop(seconds=2)  
async def change_status():
    """Updates bot status in a loop"""
    await bot.change_presence(activity=nextcord.Game(name=next(status_messages)))

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors and provide helpful formatting information."""
    if isinstance(error, commands.MissingRequiredArgument):
        # Command is missing a required argument
        embed = nextcord.Embed(
            title="❌ Missing Required Argument",
            description=f"You're missing a required argument: `{error.param.name}`",
            color=nextcord.Color.red()
        )

        # Provide command-specific help
        command_name = ctx.command.name
        if command_name == "warn":
            embed.add_field(name="Correct Format", value="`!warn @user [reason]`", inline=False)
            embed.add_field(name="Example", value="`!warn @username Breaking server rules`", inline=False)
        elif command_name == "clearwarns":
            embed.add_field(name="Correct Format", value="`!clearwarns @user`", inline=False)
            embed.add_field(name="Example", value="`!clearwarns @username`", inline=False)
        elif command_name == "warnings":
            embed.add_field(name="Correct Format", value="`!warnings [@user]`", inline=False)
            embed.add_field(name="Example", value="`!warnings @username` or just `!warnings`", inline=False)
        else:
            embed.add_field(name="Command Help", value=f"Type `!help {command_name}` for more information.", inline=False)

        await ctx.send(embed=embed)

    elif isinstance(error, commands.MemberNotFound):
        # Member not found
        embed = nextcord.Embed(
            title="❌ Member Not Found",
            description="The specified member could not be found.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Tip", value="Make sure you're mentioning a valid user (@username) or using their correct ID.", inline=False)
        await ctx.send(embed=embed)

    elif isinstance(error, commands.MissingPermissions):
        # User is missing permissions
        embed = nextcord.Embed(
            title="❌ Permission Denied",
            description="You don't have permission to use this command.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Required Permissions", value=", ".join(error.missing_permissions).replace("_", " ").title(), inline=False)
        await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandNotFound):
        # Command doesn't exist
        pass  # Optionally handle unknown commands
    else:
        # Generic error handler
        print(f"Unhandled command error: {error}")

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author.bot:
        return
    # Check if the message is in a ticket channel
    if isinstance(message.channel, nextcord.TextChannel) and "ticket-" in message.channel.name:
        # Define the required role IDs
        required_role_ids = [1338965114262392852, 1340726272908726433]
        # Check if the user has the required roles
        if any(role.id in required_role_ids for role in message.author.roles):
            # Record the user's participation
            record_ticket_participation(message.author.id)
    # Process commands
    await bot.process_commands(message)
# The claim and close functionality is now consolidated in the TicketControlsView class

# Ticket Panel button class
class OpenTicketModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            "Open Ticket",
            timeout=300,
        )

        self.reason = nextcord.ui.TextInput(
            label="Reason for opening",
            placeholder="Please provide a reason for opening this ticket",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.reason)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            # Create a new ticket channel (private)
            category = nextcord.utils.get(interaction.guild.categories, name="Tickets")
            if category is None:
                category = await interaction.guild.create_category("Tickets")

            ticket_name = f"ticket-{interaction.user.name}"
            ticket_channel = await interaction.guild.create_text_channel(ticket_name, category=category)

            # Set permissions for the ticket channel
            await ticket_channel.set_permissions(interaction.guild.default_role, view_channel=False)
            await ticket_channel.set_permissions(interaction.user, view_channel=True)
            mod_role = nextcord.utils.get(interaction.guild.roles, id=1340726272908726433)
            await ticket_channel.set_permissions(mod_role, view_channel=True, send_messages=True)

            # Create embed for the ticket channel
            embed = nextcord.Embed(
                title="Support Ticket",
                description=f"Ticket opened by {interaction.user.mention}",
                color=nextcord.Color.blue()
            )
            embed.add_field(name="Reason", value=self.reason.value, inline=False)

            # Create ticket controls
            ticket_controls = TicketControlsView(ticket_channel, original_name=ticket_name)

            # Send the initial message in the ticket channel
            await ticket_channel.send(
                f"{interaction.user.mention}",
                embed=embed,
                view=ticket_controls
            )

            await interaction.response.send_message(
                f"Ticket created! Please go to {ticket_channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            print(f"Error creating ticket: {e}")
            await interaction.response.send_message("❌ Something went wrong while creating the ticket. Please try again later.", ephemeral=True)

class OpenTicketButton(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="Open Ticket", style=nextcord.ButtonStyle.primary, emoji="🎫")
    async def open_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Check if user already has a ticket
        for channel in interaction.guild.text_channels:
            if interaction.user.name in channel.name and "ticket-" in channel.name:
                await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
                return

        # Open ticket modal
        modal = OpenTicketModal()
        await interaction.response.send_modal(modal)

class TicketPanelView(nextcord.ui.View):
    def __init__(self):
        super().__init__()

    @nextcord.ui.button(label="Open Ticket", style=nextcord.ButtonStyle.primary, emoji="🎫")
    async def create_ticket(self, button: Button, interaction: nextcord.Interaction):
        """Create a new ticket when button is clicked."""
        # Check if the user already has an open ticket
        for channel in interaction.guild.text_channels:
            if interaction.user.name in channel.name and "ticket-" in channel.name:
                await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
                return

        # Open the ticket reason modal
        modal = OpenTicketModal()
        await interaction.response.send_modal(modal)

class CloseTicketModal(nextcord.ui.Modal):
    def __init__(self, ticket_controls):
        super().__init__(
            "Close Ticket",
            timeout=300,
        )
        self.ticket_controls = ticket_controls

        self.reason = nextcord.ui.TextInput(
            label="Reason for closing",
            placeholder="Please provide a reason for closing this ticket",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.reason)

    async def callback(self, interaction: nextcord.Interaction):
        # Get the reason from the form
        reason = self.reason.value

        # Update the stats for the moderator who closed the ticket
        user_id = str(interaction.user.id)
        if user_id not in ticket_stats:
            ticket_stats[user_id] = {
                "tickets_claimed": 0,
                "tickets_closed": 0,
                "tickets_participated": 0
            }
        ticket_stats[user_id]["tickets_closed"] += 1
        save_json(ticket_stats, ticket_stats_file)

        # Send close notification in the ticket channel
        embed = nextcord.Embed(
            title="Ticket Closed",
            description=f"This ticket has been closed by {interaction.user.mention}.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        await self.ticket_controls.ticket_channel.send(embed=embed)

        # Disable all buttons in the original ticket controls
        for child in self.ticket_controls.children:
            child.disabled = True
        await interaction.message.edit(view=self.ticket_controls)

        # Send confirmation to user who closed the ticket
        await interaction.response.send_message("Closing ticket now", ephemeral=True)

        # Delete the channel immediately without delay
        try:
            await self.ticket_controls.ticket_channel.delete()
        except Exception as e:
            print(f"Error deleting channel: {e}")

# Combined ticket controls (claim + close)
class TicketControlsView(View):
    def __init__(self, ticket_channel, original_name):
        super().__init__(timeout=None)  # Make this view persistent
        self.ticket_channel = ticket_channel
        self.original_name = original_name

    @nextcord.ui.button(label="Claim Ticket", style=nextcord.ButtonStyle.success, emoji="✅")
    async def claim_ticket(self, button: Button, interaction: nextcord.Interaction):
        """Claim the ticket for moderators."""
        # Define the required role IDs
        required_role_ids = [1338965114262392852, 1340726272908726433]

        # Check if the user has the required roles
        if not any(role.id in required_role_ids for role in interaction.user.roles):
            await interaction.response.send_message("❌ You need to have the required roles to claim this ticket.", ephemeral=True)
            return

        # Update the stats for the moderator who claimed the ticket
        user_id = str(interaction.user.id)  # Convert to string for JSON compatibility
        if user_id not in ticket_stats:
            ticket_stats[user_id] = {
                "tickets_claimed": 0,
                "tickets_closed": 0,
                "tickets_participated": 0
            }
        ticket_stats[user_id]["tickets_claimed"] += 1
        save_json(ticket_stats, ticket_stats_file)

        # Rename the ticket to include the moderator's name instead of the random number
        new_ticket_name = f"ticket-{interaction.user.name}"
        await self.ticket_channel.edit(name=new_ticket_name)

        # Set permissions for the claimer
        await self.ticket_channel.set_permissions(interaction.user, view_channel=True, send_messages=True)

        # Ensure all moderators can still talk in the ticket
        mod_role = nextcord.utils.get(interaction.guild.roles, name="Moderator")
        if mod_role:
            await self.ticket_channel.set_permissions(mod_role, view_channel=True, send_messages=True)

        # Disable the claim button after claiming
        self.children[0].disabled = True  # Disable the claim button
        await interaction.message.edit(view=self)

        # Send claim notification in the ticket channel
        claim_embed = nextcord.Embed(
            title="Ticket Claimed",
            description=f"{interaction.user.mention} has claimed this ticket and will assist you shortly.",
            color=nextcord.Color.green()
        )
        await self.ticket_channel.send(embed=claim_embed)

        # Send confirmation embed to the claimer
        response_embed = nextcord.Embed(
            title="Ticket Claimed Successfully",
            description=f"You have claimed ticket: {self.ticket_channel.mention}",
            color=nextcord.Color.green()
        )
        response_embed.add_field(name="Status", value="You now have exclusive moderator access to this ticket", inline=False)
        await interaction.response.send_message(embed=response_embed, ephemeral=True)

    @nextcord.ui.button(label="Close Ticket", style=nextcord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, button: Button, interaction: nextcord.Interaction):
        """Open a modal to close the ticket with a reason."""
        # Define the required role IDs
        required_role_ids = [1338965114262392852, 1340726272908726433]

        # Check if the user has the required roles
        if not any(role.id in required_role_ids for role in interaction.user.roles):
            await interaction.response.send_message("❌ You need to have the required roles or be the ticket creator to close this ticket.", ephemeral=True)
            return

        # Open the ticket close modal form
        modal = CloseTicketModal(self)
        await interaction.response.send_modal(modal)

class TicketPanelView(nextcord.ui.View):
    def __init__(self):
        super().__init__()

    @nextcord.ui.button(label="Open Ticket", style=nextcord.ButtonStyle.primary, emoji="🎫")
    async def create_ticket(self, button: Button, interaction: nextcord.Interaction):
        """Create a new ticket when button is clicked."""
        # Check if the user already has an open ticket
        for channel in interaction.guild.text_channels:
            if interaction.user.name in channel.name and "ticket-" in channel.name:
                await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
                return

        # Open the ticket reason modal
        modal = OpenTicketModal()
        await interaction.response.send_modal(modal)
@bot.command()
async def ticket(ctx):
    """Create a ticket panel with a button."""
    # Check if the author has permissions to create ticket panels
    if not ctx.author.guild_permissions.manage_channels:
        embed = nextcord.Embed(
            title="❌ Permission Denied",
            description="You don't have permission to create ticket panels.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Correct Format", value="`!ticket`", inline=False)
        embed.add_field(name="Required Permission", value="Manage Channels", inline=False)
        await ctx.send(embed=embed)
        return

    embed = nextcord.Embed(
        title="🎫 Support Ticket System",
        description="Click the button below to create a support ticket.",
        color=nextcord.Color.blue()
    )
    embed.add_field(name="How it works", value="When you create a ticket, a private channel will be created where you can discuss your issue with our staff.", inline=False)

    # Create the view with the ticket button
    view = TicketPanelView()
    await ctx.send(embed=embed, view=view)
async def close(ctx):
    """Close the ticket."""

    # Check if the user is in a ticket channel
    if "ticket" not in ctx.channel.name:
        embed = nextcord.Embed(
            title="❌ Invalid Channel",
            description="This command can only be used in ticket channels.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Correct Format", value="`!close`", inline=False)
        embed.add_field(name="Note", value="This command must be used inside an active ticket channel.", inline=False)
        await ctx.send(embed=embed)
        return

    if any(role.id in BLACKLISTED_ROLES for role in member.roles):
        return 
    # Update the stats for the moderator who closed the ticket
    user_id = str(ctx.user_id)
    if user_id not in ticket_stats:
        ticket_stats[user_id] = {
            "tickets_claimed": 0,
            "tickets_closed": 0,
            "tickets_participated": 0
        }
        # if they have role then ....
        ticket_stats[member.id]["tickets_closed"] += 1
        save_json(ticket_stats, ticket_stats_file)
        # Store channel name before deleting
        channel_name = ctx.channel.name
        # Send a message to the guild's system channel or first available text channel
        notification_channel = ctx.guild.system_channel or next((c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages), None)
        # Delete the channel
        await ctx.channel.delete()
        # If we found a notification channel, send the closure notification there
        user = await bot.fetch_user(user.id)
        user = await bot.fetch_user(user_id)
        await user.send("Your ticket has been closed. Thank you for contacting support!")
        await ctx.send(f"{ctx.author.mention}, your ticket has been closed. A DM has been sent to you.")
    else:   
        await ctx.send(f"{ctx.author.mention}, you don't have an open ticket.")


# Warn system code (your existing warn, warnings, clearwarns, etc.)

@bot.command()
async def warn(ctx, member: nextcord.Member = None, *, reason=None):
    # Check if no member was specified
    if member is None:
        embed = nextcord.Embed(
            title="❌ Invalid Command Usage",
            description="You need to specify a member to warn.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Correct Format", value="`!warn @user [reason]`", inline=False)
        embed.add_field(name="Example", value="`!warn @username Breaking server rules`", inline=False)
        await ctx.send(embed=embed)
        return

    # Check if the author has 'manage_messages' permission
    if ctx.author.guild_permissions.manage_messages:
        # Initialize the user's warnings if they don't have any
        member_id = str(member.id)  # Convert to string for JSON compatibility
        if member_id not in warns:
            warns[member_id] = []

        # Add the warning, the reason, and who issued it
        warns[member_id].append({
            'reason': reason or "No reason provided.",
            'moderator': ctx.author.mention  # Store who issued the warning
        })

        # Save the warns to the file
        save_json(warns, warns_file)

        # Send a confirmation message
        embed = nextcord.Embed(
            title="⚠️ Warning",
            description=f"{member.mention} has been warned.",
            color=nextcord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason or "No reason provided.", inline=False)
        embed.add_field(name="Issued by", value=ctx.author.mention, inline=False)
        member_id = str(member.id)
        embed.add_field(name="Total Warnings", value=len(warns[member_id]), inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ You do not have permission to use this command.")

@bot.command()
async def warnings(ctx, member: nextcord.Member = None):
    """Show warnings for a user."""
    # If no member is specified, default to the command author
    if member is None:
        member = ctx.author

    member_id = str(member.id)

    # Check if the user has any warnings
    if member_id not in warns or not warns[member_id]:
        embed = nextcord.Embed(
            title="Warnings",
            description=f"{member.mention} has no warnings.",
            color=nextcord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    # Create an embed to display the warnings
    embed = nextcord.Embed(
        title=f"Warnings for {member.name}",
        description=f"{member.mention} has {len(warns[member_id])} warnings.",
        color=nextcord.Color.orange()
    )

    # Add each warning to the embed
    for i, warning in enumerate(warns[member_id], 1):
        embed.add_field(
            name=f"Warning #{i}",
            value=f"**Reason:** {warning['reason']}\n**Warned by:** {warning['moderator']}",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command()
async def stats(ctx):
    """Show ticket stats for all users."""
    # Check if user has admin permission
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to use this command.")
        return

    # Reload the stats from the JSON file to ensure we have the latest data
    global ticket_stats
    ticket_stats = load_json(ticket_stats_file)

    embed = nextcord.Embed(
        title="📊 Ticket Statistics",
        description="This shows how many tickets each member has participated in, claimed, or closed.",
        color=nextcord.Color.blue()
    )

    # Count how many users we've found with stats
    stats_count = 0

    # Process all users in the ticket_stats dictionary
    for user_id, stats in ticket_stats.items():
        # Try to get the member object
        try:
            member = await ctx.guild.fetch_member(int(user_id))
            member_name = member.display_name
        except:
            # If member can't be found, use their ID instead
            member_name = f"User {user_id}"

        # Add field for this user if they have any activity
        if (stats.get('tickets_participated', 0) > 0 or 
            stats.get('tickets_claimed', 0) > 0 or 
            stats.get('tickets_closed', 0) > 0):

            stats_count += 1
            embed.add_field(
                name=f"👤 {member_name}",
                value=(f"🎟 **Participated:** {stats.get('tickets_participated', 0)}\n"
                      f"✅ **Claimed:** {stats.get('tickets_claimed', 0)}\n"
                      f"🔒 **Closed:** {stats.get('tickets_closed', 0)}"),
                inline=True
            )

    if stats_count == 0:
        embed.description = "No users with ticket activity found."
    else:
        embed.description = f"Found {stats_count} users with ticket activity."

    # Add a note about the data source
    embed.set_footer(text=f"Stats are loaded from {ticket_stats_file}")

    await ctx.send(embed=embed)# Warning select menu for clearing specific warnings
class WarningSelect(nextcord.ui.Select):
    def __init__(self, member, warnings_list):
        self.member = member
        self.warnings_list = warnings_list

        # Create options for each warning
        options = []
        for i, warning in enumerate(warnings_list, 1):
            reason = warning['reason']
            # Truncate reason if it's too long
            if len(reason) > 50:
                reason = reason[:47] + "..."

            options.append(nextcord.SelectOption(
                label=f"Warning #{i}",
                description=reason,
                value=str(i-1)  # Store index as value
            ))

        super().__init__(
            placeholder="Select a warning to clear",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: nextcord.Interaction):
        # Check if user has permission
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You don't have permission to clear warnings.", ephemeral=True)
            return

        selected_index = int(self.values[0])
        warning = self.warnings_list[selected_index]

        # Remove the selected warning
        member_id = str(self.member.id)
        warns[member_id].pop(selected_index)

        # If no more warnings, remove the user from the warns dict
        if not warns[member_id]:
            del warns[member_id]

        # Save the updated warns
        save_json(warns, warns_file)

        # Send confirmation
        embed = nextcord.Embed(
            title="Warning Cleared",
            description=f"Removed warning from {self.member.mention}",
            color=nextcord.Color.green()
        )
        embed.add_field(name="Cleared Warning", value=f"**Reason:** {warning['reason']}", inline=False)
        embed.add_field(name="Cleared by", value=interaction.user.mention, inline=False)

        await interaction.response.send_message(embed=embed)

        # Disable the select menu
        self.disabled = True
        await interaction.message.edit(view=self.view)

class ClearWarningsView(nextcord.ui.View):
    def __init__(self, member, warnings_list):
        super().__init__(timeout=60)
        self.add_item(WarningSelect(member, warnings_list))

    @nextcord.ui.button(label="Clear All Warnings", style=nextcord.ButtonStyle.danger)
    async def clear_all(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You don't have permission to clear warnings.", ephemeral=True)
            return

        # Clear all warnings for the member
        member_id = str(self.children[0].member.id)
        if member_id in warns:
            del warns[member_id]
            save_json(warns, warns_file)

        # Disable all components
        for child in self.children:
            child.disabled = True

        # Send confirmation
        embed = nextcord.Embed(
            title="All Warnings Cleared",
            description=f"All warnings have been cleared for {self.children[0].member.mention}",
            color=nextcord.Color.green()
        )
        embed.add_field(name="Cleared by", value=interaction.user.mention, inline=False)

        await interaction.response.send_message(embed=embed)
        await interaction.message.edit(view=self)

@bot.command()
async def purge(ctx, amount: int = None, member: nextcord.Member = None):
    """Purge messages from the channel, optionally filtering by user."""
    # Check if the author has manage_messages permission
    if not ctx.author.guild_permissions.manage_messages:
        embed = nextcord.Embed(
            title="❌ Permission Denied",
            description="You don't have permission to purge messages.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Required Permission", value="Manage Messages", inline=False)
        await ctx.send(embed=embed)
        return

    # Check if amount is provided
    if amount is None:
        embed = nextcord.Embed(
            title="❌ Invalid Command Usage",
            description="You need to specify the number of messages to purge.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Correct Format", value="`!purge [amount] [@user]`", inline=False)
        embed.add_field(name="Examples", value="`!purge 10` - Purge 10 messages\n`!purge 20 @username` - Purge up to 20 messages from a specific user", inline=False)
        await ctx.send(embed=embed)
        return

    # Delete the command message first
    await ctx.message.delete()

    # Define a check function if member is specified
    def check_user(message):
        return member is None or message.author.id == member.id

    # Purge the messages
    try:
        # Delete messages with the check
        deleted = await ctx.channel.purge(limit=amount, check=check_user)

        # Create a success embed
        embed = nextcord.Embed(
            title="🧹 Messages Purged",
            description=f"Successfully deleted {len(deleted)} messages.",
            color=nextcord.Color.green()
        )

        if member:
            embed.description = f"Successfully deleted {len(deleted)} messages from {member.mention}."

        # Send a temporary confirmation message that auto-deletes after 5 seconds
        conf_msg = await ctx.send(embed=embed)
        await conf_msg.delete(delay=5)

    except nextcord.Forbidden:
        await ctx.send("I don't have permission to delete messages here.", delete_after=5)
    except nextcord.HTTPException as e:
        await ctx.send(f"Error: {e}\nCannot delete messages older than 14 days.", delete_after=5)

@bot.command()
async def clearwarns(ctx, member: nextcord.Member = None):
    """Clear warnings for a user using a dropdown menu."""
    # Check if no member was specified
    if member is None:
        embed = nextcord.Embed(
            title="❌ Invalid Command Usage",
            description="You need to specify a member to clear warnings for.",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Correct Format", value="`!clearwarns @user`", inline=False)
        embed.add_field(name="Example", value="`!clearwarns @username`", inline=False)
        await ctx.send(embed=embed)
        return

    # Check if the author has permission
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You do not have permission to use this command.")
        return

    member_id = str(member.id)

    # Check if the user has any warnings
    if member_id not in warns or not warns[member_id]:
        embed = nextcord.Embed(
            title="No Warnings",
            description=f"{member.mention} has no warnings to clear.",
            color=nextcord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    # Create an embed to display the warnings
    embed = nextcord.Embed(
        title=f"Clear Warnings for {member.name}",
        description=f"Select a warning to clear or use the button to clear all warnings.\n\n{member.mention} has {len(warns[member_id])} warnings.",
        color=nextcord.Color.orange()
    )

    # Add each warning to the embed
    for i, warning in enumerate(warns[member_id], 1):
        embed.add_field(
            name=f"Warning #{i}",
            value=f"**Reason:** {warning['reason']}\n**Warned by:** {warning['moderator']}",
            inline=False
        )

    # Create the view with the dropdown menu
    view = ClearWarningsView(member, warns[member_id])

    await ctx.send(embed=embed, view=view)

WHITELISTED_ROLES = ["Moderator", "Co-Owner", "Owner","Admin"]

@bot.command()
async def repeat(ctx, title: str = None, *, message: str = None):  
    """Repeats the message in an embed, including images. Only whitelisted roles can use it."""
    if not any(role.name in WHITELISTED_ROLES for role in ctx.author.roles):
        await ctx.send(":x: You are not allowed to use this command!")
        return
    # If no message and no attachments are provided
    if message is None and not ctx.message.attachments:
        await ctx.send(":x: Please provide a message or attach an image! Example: `!repeat Hello`")
        return
    try:
        # Create the embed
        embed = nextcord.Embed(
            title=title or "",  
            description=message or "No message provided.",  
            color=nextcord.Color.blue()
        )
        embed.set_footer(
            text=f"Requested by {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://example.com/default-avatar.png"
        )
        # Check for attachments and add an image to the embed if applicable
        for attachment in ctx.message.attachments:
            if attachment.url.lower().endswith(('png', 'jpg', 'jpeg', 'gif')):
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            file_data = await resp.read()
                            # Set the first image as the embed's image
                            embed.set_image(url=attachment.url)
                        else:
                            await ctx.send(":x: Failed to download the image.")
        # Send the embed
        await ctx.send(embed=embed)
        print(f"Embed created: {embed.to_dict()}")
        print("Embed sent successfully!")
    except Exception as e:
        print(f"Error creating or sending embed: {e}")
        await ctx.send(":x: Something went wrong while creating the embed. Check the console for details.")
async def search_youtube(query):
    """Search YouTube for a video matching the given query."""
    ydl_opts = {
        "format": "bestaudio/best",
        "default_search": "ytsearch",
        "quiet": True,
        "noplaylist": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(query, download=False)
        if result and "entries" in result:
            return result["entries"][0]["url"]
        return None

@bot.command()
async def play(ctx, spotify_url: str):
    """Plays a song from a Spotify track link."""
    if "spotify.com/track/" not in spotify_url:
        return
        

    
    track_id = spotify_url.split("/")[-1].split("?")[0]

    # Fetch track details from Spotify
    track_info = sp.track(track_id)
    track_name = track_info["name"]
    artist_name = track_info["artists"][0]["name"]
    album_cover = track_info["album"]["images"][0]["url"]

    query = f"{track_name} {artist_name} audio"
    youtube_url = await search_youtube(query)

    if not youtube_url:
        return await ctx.send(":x: Couldn't find a YouTube version of this song.")

    
    voice_channel = ctx.author.voice.channel
    vc = await voice_channel.connect() if not ctx.voice_client else ctx.voice_client

    
    vc.stop()
    ffmpeg_opts = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }
    vc.play(nextcord.FFmpegPCMAudio(youtube_url, **ffmpeg_opts))

    # Send embed message
    embed = nextcord.Embed(
        title="Now Playing 🎶",
        description=f"**[{track_name}](https://open.spotify.com/track/{track_id})** by {artist_name}",
        color=nextcord.Color.green()
    )
    embed.set_thumbnail(url=album_cover)
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def stop(ctx):
    """Stops music and disconnects the bot."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("✅ Disconnected from voice channel!")



def get_audio_url(query):
    ydl_opts = {"format": "bestaudio", "noplaylist": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        return info["entries"][0]["url"] if info["entries"] else None


async def play_next(ctx):
    vc = ctx.voice_client
    if vc and vc.is_connected() and queues.get(ctx.guild.id):
        next_song = queues[ctx.guild.id].pop(0)
        vc.play(nextcord.FFmpegPCMAudio(next_song), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(embed=create_embed(ctx, next_song))


def create_embed(ctx, song_url):
    embed = nextcord.Embed(title="🎶 Now Playing", description=f"[Click to Listen]({song_url})", color=nextcord.Color.blue())
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)

    view = MusicView()
    return embed, view

class MusicView(View):
    @nextcord.ui.button(label="⏭ Skip", style=nextcord.ButtonStyle.primary)
    async def skip(self, button: Button, interaction: nextcord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await play_next(interaction)

@nextcord.ui.button(label="📜 Queue", style=nextcord.ButtonStyle.secondary)
async def show_queue(self, button: Button, interaction: nextcord.Interaction):
    queue_list = queues.get(interaction.guild.id, [])
    if not queue_list:
        await interaction.response.send_message("📭 The queue is empty!", ephemeral=True)
        return
        queue_text = "\n".join([f"{i+1}. {song}" for i, song in enumerate(queue_list)])
        embed = nextcord.Embed(title=":notes: Queue", description=queue_text, color=nextcord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.ui.button(label="⏹ Stop", style=nextcord.ButtonStyle.danger)
    async def stop(self, button: Button, interaction: nextcord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
        await interaction.response.send_message(":octagonal_sign: Music stopped and bot left the voice channel.")

@bot.command()
async def skip(ctx):
    """Skips the current song"""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await play_next(ctx)
    else:
        await ctx.send("❌ No music is currently playing!")



    @bot.command(name="help", help="Shows the help menu")
    async def help_command(ctx):
        embed = nextcord.Embed
        title="Help Menu",
        description="Here are the available commands:",
        color=nextcord.Color.blue()

    

    for command in bot.commands:
        if command.hidden:
            continue
        embed.add_field(name=f"!{command.name}", value=command.help or "No description", inline=False)

    embed.set_footer(text="Use !command_name to execute a command.")
    await ctx.send(embed=embed)
    
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def transcript(ctx, channel: nextcord.TextChannel = None):
    """Generates a transcript of a specified channel."""
    if channel is None:
        channel = ctx.channel  # Default to the channel the command was used in

    messages = await channel.history(limit=1000).flatten()
    transcript_content = ""

    for message in reversed(messages):
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        transcript_content += f"[{timestamp}] {message.author}: {message.content}\n"

    file_name = f"transcript-{channel.name}-{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(transcript_content)

    await ctx.send(file=nextcord.File(file_name))


@bot.command()
async def claim(ctx):
    """Marks a ticket as claimed by the user."""
    if ctx.channel.id not in ticket_data:
        ticket_data[ctx.channel.id] = {}
    ticket_data[ctx.channel.id]['claimed_by'] = ctx.author
    await ctx.send(f"{ctx.author.mention} has claimed this ticket.")

@bot.command()
async def close(ctx, *, reason: str = "No reason provided"):
    """Closes a ticket and generates a transcript."""
    if ctx.channel.id not in ticket_data:
        await ctx.send("This is not a valid ticket channel.")
        return

    claimed_by = ticket_data[ctx.channel.id].get('claimed_by', 'Not claimed')
    messages = await ctx.channel.history(limit=1000).flatten()
    transcript_content = ""

    for message in reversed(messages):
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        transcript_content += f"[{timestamp}] {message.author}: {message.content}\n"

    file_name = f"transcript-{ctx.channel.name}-{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(transcript_content)

    embed = nextcord.Embed(title="Ticket Closed", color=nextcord.Color.red())
    embed.add_field(name="Closed by", value=ctx.author.mention, inline=True)
    embed.add_field(name="Claimed by", value=claimed_by.mention if isinstance(claimed_by, nextcord.Member) else claimed_by, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"Ticket ID: {ctx.channel.id}")

        
    
    log_channel = await bot.fetch_channel(1345810536457179136)
    if log_channel is None:
        await ctx.send("Log channel not found. Please check the channel ID.")
        return

    await log_channel.send(embed=embed)
    transcript_file = nextcord.File(file_name)
    await log_channel.send(file=transcript_file)
    os.remove(file_name)  # Delete the transcript file after sending it

    

# Run the bot with the provided token
bot_token = os.getenv("BOT_TOKEN")
bot.run(bot_token)