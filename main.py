import discord
from discord.ext import commands
import asyncio
import os
import datetime
# import collections
import aiohttp
import json
from discord import TextStyle

# Define channel IDs
MODLOGS_CHANNEL_ID = 1340864063659573248  # Channel for warnings, automod logs, and moderation actions
welcome_channel_id = None  # Will be set via welcomeset command

# Load welcome channel from file if it exists
def load_welcome_channel():
    try:
        with open('welcome_channel.txt', 'r') as f:
            return int(f.read().strip())
    except:
        return None

# Save welcome channel to file
def save_welcome_channel(channel_id):
    with open('welcome_channel.txt', 'w') as f:
        f.write(str(channel_id))

# Define staff role check function
def has_staff_role(member):
     # Check by role ID first
     staff_role_ids = [1338965114262392852, 1340726272908726433]  # Staff role IDs

     # Also check by role name for redundancy
     staff_role_names = ["Moderator", "Co-Owner", "Owner", "Admin", "Trial Helper", "Helper"]

     # Return True if the member has any of the specified roles (by ID or name)
     for role in member.roles:
          if role.id in staff_role_ids or role.name in staff_role_names:
               return True
     return False

intents = discord.Intents.all()  # Use all intents to ensure everything works

# Function to get prefix
async def get_prefix(bot, message):
    # Default prefix if not set
    if not hasattr(bot, 'custom_prefix'):
        try:
            with open('prefix.txt', 'r') as f:
                bot.custom_prefix = f.read().strip()
        except:
            bot.custom_prefix = "!"
    return commands.when_mentioned_or(bot.custom_prefix)(bot, message)

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

# Load prefix if exists
def load_prefix():
    try:
        with open('prefix.txt', 'r') as f:
            return f.read().strip()
    except:
        return "!"

# Save prefix
def save_prefix(prefix):
    with open('prefix.txt', 'w') as f:
        f.write(prefix)

# Dictionary to store ticket data for the session
ticket_data = {}

# Define the file to store ticket stats

# Set up slash commands
from discord import app_commands

# Track bot start time
bot.start_time = None

# Setup hook to sync commands when the bot starts
@bot.event
async def setup_hook():
    bot.start_time = datetime.datetime.utcnow()
    print("Syncing commands...")
    try:
        # Sync the commands with Discord, but only if needed
        synced = await bot.tree.sync()
        print(f"Commands synced successfully! ({len(synced)} commands)")
    except Exception as e:
        print(f"Error syncing commands: {e}")
        raise e  # Re-raise to see full error

# Basic slash command examples
@bot.command(name="ping")
async def ping(ctx):
    """Check if the bot is alive (prefix command)"""
    await ctx.send(f"Pong! Bot latency: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping_command(interaction: discord.Interaction):
    """Check if the bot is alive (slash command)"""
    await interaction.response.send_message(f"Pong! Bot latency: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="ticket", description="Create a ticket support panel")
async def ticket_slash(interaction: discord.Interaction):
    # Check if user has staff role or manage channels permission
    if not (has_staff_role(interaction.user) or interaction.user.guild_permissions.manage_channels):
        await interaction.response.send_message("❌ You don't have permission to create ticket panels.", ephemeral=True)
        return
    embed = discord.Embed(
        title="🎫 Support Ticket System",
        description="Click the button below to create a support ticket.",
        color=discord.Color.blue()
    )
    embed.add_field(name="How it works", value="When you create a ticket, a private channel will be created where you can discuss your issue with our staff.", inline=False)

    # Create the view with the ticket button
    view = TicketPanelView()
    await interaction.response.send_message(embed=embed, view=view)

ticket_stats_file = "ticket_stats.json"

# Load the saved stats from file, if it exists
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

# Load ticket stats
ticket_stats = load_json(ticket_stats_file)

@bot.event
async def on_member_join(member):
    """Sends welcome message when a new member joins"""
    global welcome_channel_id

    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            embed = discord.Embed(
                title="👋 Welcome!",
                description=f"Welcome {member.mention} to {member.guild.name}!",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_footer(text=f"Member #{len(member.guild.members)}")
            await channel.send(embed=embed)

@bot.tree.command(name="welcomeset", description="Set the welcome message channel")
async def welcomeset(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the channel for welcome messages"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return

    global welcome_channel_id
    welcome_channel_id = channel.id
    save_welcome_channel(channel.id)

    await interaction.response.send_message(f"✅ Welcome channel set to {channel.mention}", ephemeral=True)

@bot.event
async def on_ready():
     """Starts when bot is online and registers persistent views for ticket system"""
     global welcome_channel_id
     welcome_channel_id = load_welcome_channel()
     bot.custom_prefix = load_prefix()
     print(f"Bot is online as {bot.user}")

     # Register persistent views for ticket system
     print("Registering persistent views for ticket system...")
     try:
          # Add the ticket panel view for the open ticket button
          bot.add_view(TicketPanelView())

          # Add the ticket controls view for claim and close buttons
          bot.add_view(TicketControlsView())

          print("✅ Persistent views registered successfully!")

          # Try to sync commands again just to be safe
          print("Syncing slash commands...")
          await bot.tree.sync()
          print("✅ Slash commands synced!")
     except Exception as e:
          print(f"Error registering persistent views or commands: {e}")

@bot.event
async def on_message(message):
     # Process commands first
     await bot.process_commands(message)

     # Ignore messages from the bot itself
     if message.author.bot:
          return

     # Check if the message is in a ticket channel
     if isinstance(message.channel, discord.TextChannel) and "ticket-" in message.channel.name:
          # Record message count for user
          user_id = str(message.author.id)
          if user_id not in ticket_stats:
               ticket_stats[user_id] = {
                    "tickets_claimed": 0,
                    "tickets_closed": 0,
                    "tickets_participated": 0,
                    "messages_sent": 0
               }

          # Increment message count
          if "messages_sent" not in ticket_stats[user_id]:
               ticket_stats[user_id]["messages_sent"] = 0
          ticket_stats[user_id]["messages_sent"] += 1

          # Save the updated stats
          save_json(ticket_stats, ticket_stats_file)

          # Check if the user has the required roles and hasn't been recorded as participating yet
          if has_staff_role(message.author):
               # Record the user's participation (only once per ticket)
               record_ticket_participation(message.author.id)

@bot.event
async def on_message_edit(before, after):
     # Ignore messages from the bot itself
     if after.author.bot:
          return

     # Check if the message is in a ticket channel
     if isinstance(after.channel, discord.TextChannel) and "ticket-" in after.channel.name:
          # Check if the user has the required roles
          if has_staff_role(after.author):
               # Record the user's participation
               record_ticket_participation(after.author.id)

# Ticket Panel button class
class OpenTicketModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Open Ticket", timeout=300)

        self.reason = discord.ui.TextInput(
            label="Reason for opening",
            placeholder="Please provide a reason for opening this ticket",
            style=TextStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        """Process the submitted ticket form"""
        try:
            # First, acknowledge the interaction to prevent timeouts
            await interaction.response.defer(ephemeral=True)

            # Find or create Tickets category
            category = discord.utils.get(interaction.guild.categories, name="Tickets")
            if category is None:
                try:
                    category = await interaction.guild.create_category("Tickets")
                except Exception as e:
                    print(f"Failed to create category: {e}")
                    await interaction.followup.send(f"Error creating ticket category: {str(e)}", ephemeral=True)
                    return

            # Create ticket channel
            ticket_name = f"ticket-{interaction.user.name}"
            try:
                ticket_channel = await interaction.guild.create_text_channel(
                    name=ticket_name,
                    category=category
                )
            except Exception as e:
                print(f"Failed to create channel: {e}")
                await interaction.followup.send(f"Error creating ticket channel: {str(e)}", ephemeral=True)
                return

            # Set permissions for the ticket channel
            try:
                # Make channel private by default
                await ticket_channel.set_permissions(interaction.guild.default_role, view_channel=False)

                # Let ticket creator see the channel
                await ticket_channel.set_permissions(interaction.user, 
                    view_channel=True,
                    send_messages=True,
                    read_messages=True
                )

                # Give access to moderator role
                mod_role = discord.utils.get(interaction.guild.roles, id=1340726272908726433)
                if mod_role:
                    await ticket_channel.set_permissions(mod_role, 
                        view_channel=True,
                        send_messages=True,
                        read_messages=True
                    )
            except Exception as e:
                print(f"Failed to set permissions: {e}")

            # Create embed and controls for the ticket
            embed = discord.Embed(
                title="Support Ticket",
                description=f"Ticket opened by {interaction.user.mention}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Reason", value=self.reason.value, inline=False)
            embed.set_footer(text=f"Ticket ID: {ticket_channel.id}")

            # Create ticket controls with claim/close buttons
            ticket_controls = TicketControlsView(ticket_channel, original_name=ticket_name)

            # Send welcome message in the ticket channel
            try:
                await ticket_channel.send(
                    content=f"{interaction.user.mention} Staff will assist you shortly. <@&1350626942063218728>",
                    embed=embed,
                    view=ticket_controls
                )
            except Exception as e:
                print(f"Failed to send welcome message: {e}")

            # Tell the user their ticket was created
            await interaction.followup.send(
                f"✅ Ticket created successfully! Please go to {ticket_channel.mention}",
                ephemeral=True
            )

            # Log ticket creation to mod logs
            try:
                if MODLOGS_CHANNEL_ID:
                    log_channel = interaction.client.get_channel(MODLOGS_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="Ticket Created",
                            description=f"New ticket opened: {ticket_channel.mention}",
                            color=discord.Color.green(),
                            timestamp=datetime.datetime.now()
                        )
                        log_embed.add_field(name="Created by", value=interaction.user.mention, inline=True)
                        log_embed.add_field(name="Reason", value=self.reason.value[:100] + "..." if len(self.reason.value) > 100 else self.reason.value, inline=True)
                        await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"Failed to log ticket creation: {e}")

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"Error creating ticket: {e}\n{error_traceback}")

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"❌ Error creating your ticket: {str(e)}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Error creating your ticket: {str(e)}",
                        ephemeral=True
                    )
            except Exception:
                print("Failed to send error message to user")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle errors in the modal"""
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Modal error: {error}\n{error_traceback}")

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Error processing ticket: {str(error)}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Error processing ticket: {str(error)}",
                    ephemeral=True
                )
        except Exception:
            print("Failed to send error message to user")

class OpenTicketButton(discord.ui.View):
     def __init__(self):
          super().__init__(timeout=None)

     @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="open_ticket_button")
     async def open_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
          # Check if user already has a ticket (including both ticket-user and claimed-user formats)
          for channel in interaction.guild.text_channels:
               if interaction.user.name in channel.name:
                    # Check if it's a ticket channel (either "ticket-user" or "claimer-user" format)
                    if "ticket-" in channel.name or "-" in channel.name:
                         await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
                         return

          # Open ticket modal
          try:
               modal = OpenTicketModal()
               await interaction.response.send_modal(modal)
          except Exception as e:
               print(f"Error opening modal: {e}")
               await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

class TicketPanelView(discord.ui.View):
     def __init__(self):
          super().__init__(timeout=None)

     @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="persistent_open_ticket_button")
     async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
          """Create a new ticket when button is clicked."""
          try:
               # Check if the user already has an open ticket (including both ticket-user and claimed-user formats)
               for channel in interaction.guild.text_channels:
                    if interaction.user.name in channel.name:
                         # Check if it's a ticket channel (either "ticket-user" or "claimer-user" format)
                         if "ticket-" in channel.name or "-" in channel.name:
                              await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
                              return

               # Open the ticket reason modal
               modal = OpenTicketModal()
               await interaction.response.send_modal(modal)
          except Exception as e:
               print(f"Error in ticket panel view: {e}")
               await interaction.response.send_message(f"Error creating ticket: {str(e)}", ephemeral=True)

class CloseTicketModal(discord.ui.Modal):
    def __init__(self, ticket_controls):
        super().__init__(title="Close Ticket", timeout=300)
        self.ticket_controls = ticket_controls

        self.reason = discord.ui.TextInput(
            label="Reason for closing",
            placeholder="Please provide a reason for closing this ticket",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Immediately defer the response to prevent timeouts
            await interaction.response.defer(ephemeral=True)

            # Get reason from form
            reason = self.reason.value
            print(f"Closing ticket: Reason: {reason[:30]}...")

            # Ensure we have a valid channel reference
            if self.ticket_controls.ticket_channel is None:
                self.ticket_controls.ticket_channel = interaction.channel
                self.ticket_controls.original_name = interaction.channel.name

            # Validate the channel exists and is a ticket
            ticket_channel = self.ticket_controls.ticket_channel
            if not ticket_channel or not isinstance(ticket_channel, discord.TextChannel):
                await interaction.followup.send("❌ Invalid ticket channel.", ephemeral=True)
                return

            # 1. Update stats for the moderator
            user_id = str(interaction.user.id)
            if user_id not in ticket_stats:
                ticket_stats[user_id] = {
                    "tickets_claimed": 0,
                    "tickets_closed": 0,
                    "tickets_participated": 0
                }
            ticket_stats[user_id]["tickets_closed"] += 1
            save_json(ticket_stats, ticket_stats_file)

            # 2. Generate transcript
            file_name = None
            try:
                messages = []
                async for message in ticket_channel.history(limit=1000):
                    messages.append(message)

                transcript_content = f"Ticket: {ticket_channel.name}\n"
                transcript_content += f"Closed by: {interaction.user} ({interaction.user.id})\n"
                transcript_content += f"Reason: {reason}\n"
                transcript_content += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                transcript_content += "=" * 50 + "\n\n"

                for message in reversed(messages):
                    timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    author = f"{message.author} ({message.author.id})"
                    content = message.content or "[No text content]"

                    # Add attachments if any
                    attachments = ""
                    if message.attachments:
                        attachments = f" [Attachments: {', '.join([a.url for a in message.attachments])}]"

                    # Add embeds if any
                    embeds = ""
                    if message.embeds:
                        embeds = f" [Contains {len(message.embeds)} embeds]"

                    transcript_content += f"[{timestamp}] {author}: {content}{attachments}{embeds}\n"

                file_name = f"transcript-{ticket_channel.name}-{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write(transcript_content)
            except Exception as e:
                print(f"Error generating transcript: {e}")
                file_name = None

            # 3. Send close notification to the ticket channel
            try:
                close_embed = discord.Embed(
                    title="Ticket Closed",
                    description=f"This ticket has been closed by {interaction.user.mention}.",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.now()
                )
                close_embed.add_field(name="Reason", value=reason, inline=False)
                close_embed.set_footer(text="This ticket will be deleted shortly.")

                await ticket_channel.send(embed=close_embed)
            except Exception as e:
                print(f"Error sending close notification: {e}")

            # 4. Disable the ticket control buttons
            try:
                for child in self.ticket_controls.children:
                    child.disabled = True
                if interaction.message:
                    await interaction.message.edit(view=self.ticket_controls)
            except Exception as e:
                print(f"Error disabling buttons: {e}")

            # 5. Send log to the ticket logs channel
            try:
                log_channel = interaction.client.get_channel(1345810536457179136)  # Ticket logs channel
                if not log_channel:
                    log_channel = await interaction.client.fetch_channel(1345810536457179136)

                if log_channel:
                    log_embed = discord.Embed(
                        title="Ticket Closed",
                        description=f"Ticket {ticket_channel.name} was closed",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now()
                    )
                    log_embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
                    log_embed.add_field(name="Reason", value=reason, inline=True)

                    await log_channel.send(embed=log_embed)

                    if file_name:
                        transcript_file = discord.File(file_name)
                        await log_channel.send(file=transcript_file)
            except Exception as e:
                print(f"Error sending to log channel: {e}")

            # 6. Send confirmation to the moderator
            await interaction.followup.send("✅ Ticket is being closed...", ephemeral=True)

            # 7. Wait a moment for people to read the close message
            await asyncio.sleep(3)

            # 8. Delete the channel
            try:
                await ticket_channel.delete(reason=f"Ticket closed by {interaction.user.name}: {reason}")
                print(f"Deleted ticket channel: {ticket_channel.name}")
            except Exception as e:
                print(f"Error deleting channel: {e}")
                await interaction.followup.send(
                    "❌ Failed to delete the channel. It may need to be deleted manually.",
                    ephemeral=True
                )

            # 9. Clean up the transcript file
            if file_name:
                try:
                    os.remove(file_name)
                except Exception as e:
                    print(f"Error removing transcript file: {e}")

        except Exception as e:
            import traceback
            print(f"Unhandled error closing ticket: {e}")
            print(traceback.format_exc())

            try:
                await interaction.followup.send(
                    "❌ An error occurred while processing the ticket closure. Please try again.",
                    ephemeral=True
                )
            except:
                print("Failed to send error response")

# Combined ticket controls (claim + close)
class TicketControlsView(discord.ui.View):
    def __init__(self, ticket_channel=None, original_name=None, ticket_id=None):
        super().__init__(timeout=None)  # Make this view persistent
        self.ticket_channel = ticket_channel
        self.original_name = original_name
        self.ticket_id = ticket_id

    @discord.ui.button(
        label="Claim Ticket", 
        style=discord.ButtonStyle.success, 
        emoji="✅", 
        custom_id="persistent_claim_ticket_button"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim the ticket for staff members"""
        try:
            # Acknowledge the interaction first to prevent timeouts
            await interaction.response.defer(ephemeral=True)

            # Get the channel if it's not set yet (after bot restart)
            if self.ticket_channel is None:
                self.ticket_channel = interaction.channel
                self.original_name = interaction.channel.name

            # Check if the user has the required staff roles
            if not has_staff_role(interaction.user):
                await interaction.followup.send(
                    "❌ You need to have staff permissions to claim this ticket.", 
                    ephemeral=True
                )
                return

            print(f"Claiming ticket: {self.ticket_channel.name} by {interaction.user.name}")

            # Update the stats for the moderator who claimed the ticket
            user_id = str(interaction.user.id)
            if user_id not in ticket_stats:
                ticket_stats[user_id] = {
                    "tickets_claimed": 0,
                    "tickets_closed": 0,
                    "tickets_participated": 0
                }
            ticket_stats[user_id]["tickets_claimed"] += 1
            save_json(ticket_stats, ticket_stats_file)

            # Extract the ticket creator's name from the original channel name
            ticket_creator = self.original_name.replace("ticket-", "") if self.original_name else "unknown"

            # Rename the ticket to include both the claimed user and ticket creator
            new_ticket_name = f"{interaction.user.name}-{ticket_creator}"
            await self.ticket_channel.edit(name=new_ticket_name)

            # Set permissions for the claimer and ensure mod access
            await self.ticket_channel.set_permissions(
                interaction.user, 
                view_channel=True, 
                send_messages=True,
                read_messages=True
            )

            # Make sure other mods still have access
            mod_role = discord.utils.get(interaction.guild.roles, id=1340726272908726433)
            if mod_role:
                await self.ticket_channel.set_permissions(
                    mod_role, 
                    view_channel=True, 
                    send_messages=True,
                    read_messages=True
                )

            # Disable the claim button
            button.disabled = True
            await interaction.message.edit(view=self)

            # Send notification in the ticket channel
            claim_embed = discord.Embed(
                title="Ticket Claimed",
                description=f"{interaction.user.mention} has claimed this ticket and will assist you shortly.",
                color=discord.Color.green()
            )
            await self.ticket_channel.send(embed=claim_embed)

            # Confirm to the staff member
            await interaction.followup.send(
                f"✅ You have successfully claimed ticket: {self.ticket_channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            print(f"Error claiming ticket: {e}")
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        "❌ An error occurred while claiming the ticket. Please try again.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "❌ An error occurred while claiming the ticket. Please try again.",
                        ephemeral=True
                    )
            except Exception as inner_e:
                print(f"Failed to send error message: {inner_e}")
                await self.ticket_channel.send("❌ An error occurred while claiming the ticket.")

    @discord.ui.button(
        label="Close with Reason", 
        style=discord.ButtonStyle.danger, 
        emoji="🔒", 
        custom_id="persistent_close_ticket_button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open a modal to close the ticket with a reason"""
        try:
            # Get the channel if it's not set (after bot restart)
            if self.ticket_channel is None:
                self.ticket_channel = interaction.channel
                self.original_name = interaction.channel.name

            # Check if user has staff role
            if not has_staff_role(interaction.user):
                await interaction.response.send_message(
                    "❌ You need to have staff permissions to close this ticket.",
                    ephemeral=True
                )
                return

            # Open the modal for closing the ticket
            modal = CloseTicketModal(self)
            await interaction.response.send_modal(modal)

        except Exception as e:
            print(f"Error opening close ticket modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )

    @discord.ui.button(
        label="Quick Close", 
        style=discord.ButtonStyle.secondary, 
        emoji="⚡", 
        custom_id="persistent_quick_close_ticket_button"
    )
    async def quick_close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the ticket without asking for a reason"""
        try:
            # Get the channel if it's not set (after bot restart)
            if self.ticket_channel is None:
                self.ticket_channel = interaction.channel
                self.original_name = interaction.channel.name

            # Check if user has staff role
            if not has_staff_role(interaction.user):
                await interaction.response.send_message(
                    "❌ You need to have staff permissions to close this ticket.",
                    ephemeral=True
                )
                return

            # Acknowledge the interaction first
            await interaction.response.defer(ephemeral=True)

            # Update stats for the moderator
            user_id = str(interaction.user.id)
            if user_id not in ticket_stats:
                ticket_stats[user_id] = {
                    "tickets_claimed": 0,
                    "tickets_closed": 0,
                    "tickets_participated": 0
                }
            ticket_stats[user_id]["tickets_closed"] += 1
            save_json(ticket_stats, ticket_stats_file)

            # Create close notification embed
            close_embed = discord.Embed(
                title="Ticket Closed",
                description=f"This ticket has been closed by {interaction.user.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            close_embed.set_footer(text="This ticket will be deleted shortly.")

            await self.ticket_channel.send(embed=close_embed)

            # Disable the buttons
            for child in self.children:
                child.disabled = True
            if interaction.message:
                await interaction.message.edit(view=self)

            # Generate transcript
            file_name = None
            try:
                messages = []
                async for message in self.ticket_channel.history(limit=1000):
                    messages.append(message)

                transcript_content = f"Ticket: {self.ticket_channel.name}\n"
                transcript_content += f"Closed by: {interaction.user} ({interaction.user.id})\n"
                transcript_content += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                transcript_content += "=" * 50 + "\n\n"

                for message in reversed(messages):
                    timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    author = f"{message.author} ({message.author.id})"
                    content = message.content or "[No text content]"

                    # Add attachments if any
                    attachments = ""
                    if message.attachments:
                        attachments = f" [Attachments: {', '.join([a.url for a in message.attachments])}]"

                    # Add embeds if any
                    embeds = ""
                    if message.embeds:
                        embeds = f" [Contains {len(message.embeds)} embeds]"

                    transcript_content += f"[{timestamp}] {author}: {content}{attachments}{embeds}\n"

                file_name = f"transcript-{self.ticket_channel.name}-{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write(transcript_content)
            except Exception as e:
                print(f"Error generating transcript: {e}")
                file_name = None

            # Send log to the ticket logs channel
            try:
                log_channel = interaction.client.get_channel(1345810536457179136)  # Ticket logs channel
                if not log_channel:
                    log_channel = await interaction.client.fetch_channel(1345810536457179136)

                if log_channel:
                    log_embed = discord.Embed(
                        title="Ticket Closed",
                        description=f"Ticket {self.ticket_channel.name} was closed",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now()
                    )
                    log_embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
                    log_embed.add_field(name="Reason", value="Quick close (no reason provided)", inline=True)

                    await log_channel.send(embed=log_embed)

                    if file_name:
                        transcript_file = discord.File(file_name)
                        await log_channel.send(file=transcript_file)
            except Exception as e:
                print(f"Error sending to log channel: {e}")

            # Send confirmation to the moderator
            await interaction.followup.send("✅ Ticket is being closed...", ephemeral=True)

            # 7. Wait a moment for people to read the close message
            await asyncio.sleep(3)

            # 8. Delete the channel
            try:
                await self.ticket_channel.delete(reason=f"Ticket quick-closed by {interaction.user.name}")
                print(f"Deleted ticket channel: {self.ticket_channel.name}")
            except Exception as e:
                print(f"Error deleting channel: {e}")
                await interaction.followup.send(
                    "❌ Failed to delete the channel. It may need to be deleted manually.",
                    ephemeral=True
                )

            # 9. Clean up the transcript file
            if file_name:
                try:
                    os.remove(file_name)
                except Exception as e:
                    print(f"Error removing transcript file: {e}")

        except Exception as e:
            import traceback
            print(f"Unhandled error closing ticket: {e}")
            print(traceback.format_exc())

            try:
                await interaction.followup.send(
                    "❌ An error occurred while processing the ticket closure. Please try again.",
                    ephemeral=True
                )
            except:
                print("Failed to send error response")

@bot.command(name="ticket")
async def ticket_command(ctx):
     """Create a ticket panel with a button."""
     # Check if the author has permissions to create ticket panels
     if not (has_staff_role(ctx.author) or ctx.author.guild_permissions.manage_channels):
          embed = discord.Embed(
               title="❌ Permission Denied",
               description="You don't have permission to create ticket panels.",
               color=discord.Color.red()
          )
          embed.add_field(name="Correct Format", value="`!ticket`", inline=False)
          embed.add_field(name="Required Permission", value="Staff Role or Manage Channels", inline=False)
          await ctx.send(embed=embed)
          return

     embed = discord.Embed(
          title="🎫 Support Ticket System",
          description="Click the button below to create a support ticket.",
          color=discord.Color.blue()
     )
     embed.add_field(name="How it works", value="When you create a ticket, a private channel will be created where you can discuss your issue with our staff.", inline=False)

     # Create the view with the ticket button
     view = TicketPanelView()
     await ctx.send(embed=embed, view=view)

@bot.command()
async def simpleclose(ctx):
     """Close the ticket."""
     # Check if the user is in a ticket channel
     if "ticket" not in ctx.channel.name:
          embed = discord.Embed(
               title="❌ Invalid Channel",
               description="This command can only be used in ticket channels.",
               color=discord.Color.red()
          )
          embed.add_field(name="Correct Format", value="`!simpleclose`", inline=False)
          embed.add_field(name="Note", value="This command must be used inside an active ticket channel.", inline=False)
          await ctx.send(embed=embed)
          return

     # Check if user has staff role
     if not has_staff_role(ctx.author):
          await ctx.send("❌ You don't have permission to close tickets.")
          return

     # Update the stats for the moderator who closed the ticket
     user_id = str(ctx.author.id)
     if user_id not in ticket_stats:
          ticket_stats[user_id] = {
               "tickets_claimed": 0,
               "tickets_closed": 0,
               "tickets_participated": 0
          }

     ticket_stats[user_id]["tickets_closed"] += 1
     save_json(ticket_stats, ticket_stats_file)

     # Send closure message
     await ctx.send("🔒 Closing ticket now...")

     try:
          # Try to DM the ticket creator (channel name format is ticket-username)
          ticket_creator_name = ctx.channel.name.replace("ticket-", "")
          ticket_creator = None

          for member in ctx.guild.members:
               if member.name.lower() == ticket_creator_name.lower():
                    ticket_creator = member
                    break

          if ticket_creator:
               try:
                    await ticket_creator.send("Your ticket has been closed. Thank you for contacting support!")
               except:
                    print(f"Could not DM {ticket_creator.name}")

          # Delete the channel
          await ctx.channel.delete()
     except Exception as e:
          await ctx.send(f"❌ Error closing ticket: {e}")
          print(f"Error closing ticket: {e}")

# Ticket-related slash commands
@bot.tree.command(name="close", description="Close the current ticket")
async def close_ticket_slash(interaction: discord.Interaction, *, reason: str = "No reason provided"):
    # Check if in a ticket channel
    if "ticket-" not in interaction.channel.name:
        await interaction.response.send_message("❌ This command can only be used in ticket channels.", ephemeral=True)
        return

    # Check if user has staff role
    if not has_staff_role(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to close tickets.", ephemeral=True)
        return

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

    # Create the control view and directly close the ticket using the reason provided
    controls = TicketControlsView(interaction.channel, original_name=interaction.channel.name)

    try:
        # Acknowledge the interaction first
        await interaction.response.send_message("🔒 Closing ticket now...")

        # Create embed for closing notification
        close_embed = discord.Embed(
            title="Ticket Closed",
            description=f"This ticket has been closed by {interaction.user.mention}.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        close_embed.add_field(name="Reason", value=reason, inline=False)
        close_embed.set_footer(text="This ticket will be deleted shortly.")

        await interaction.channel.send(embed=close_embed)

        # Generate transcript
        file_name = None
        try:
            messages = []
            async for message in interaction.channel.history(limit=1000):
                messages.append(message)
            transcript_content = f"Ticket: {interaction.channel.name}\n"
            transcript_content += f"Closed by: {interaction.user} ({interaction.user.id})\n"
            transcript_content += f"Reason: {reason}\n"
            transcript_content += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            transcript_content += "=" * 50 + "\n\n"

            for message in reversed(messages):
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                author = f"{message.author} ({message.author.id})"
                content = message.content or "[No text content]"

                # Add attachments if any
                attachments = ""
                if message.attachments:
                    attachments = f" [Attachments: {', '.join([a.url for a in message.attachments])}]"

                # Add embeds if any
                embeds = ""
                if message.embeds:
                    embeds = f" [Contains {len(message.embeds)} embeds]"

                transcript_content += f"[{timestamp}] {author}: {content}{attachments}{embeds}\n"

            file_name = f"transcript-{interaction.channel.name}-{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(transcript_content)
        except Exception as e:
            print(f"Error generating transcript: {e}")
            file_name = None

        # Send log to the ticket logs channel
        try:
            log_channel = interaction.client.get_channel(1345810536457179136)  # Ticket logs channel
            if not log_channel:
                log_channel = await interaction.client.fetch_channel(1345810536457179136)

            if log_channel:
                log_embed = discord.Embed(
                    title="Ticket Closed",
                    description=f"Ticket {interaction.channel.name} was closed",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.now()
                )
                log_embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="Reason", value=reason, inline=True)

                await log_channel.send(embed=log_embed)

                if file_name:
                    transcript_file = discord.File(file_name)
                    await log_channel.send(file=transcript_file)
        except Exception as e:
            print(f"Error sending to log channel: {e}")

        # Wait a moment for people to read the close message
        await asyncio.sleep(3)

        # Delete the channel
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user.name}: {reason}")
            print(f"Deleted ticket channel: {interaction.channel.name}")
        except Exception as e:
            print(f"Error deleting channel: {e}")

        # Clean up the transcript file
        if file_name:
            try:
                os.remove(file_name)
            except Exception as e:
                print(f"Error removing transcript file: {e}")
    except Exception as e:
        import traceback
        print(f"Unhandled error closing ticket: {e}")
        print(traceback.format_exc())

@bot.tree.command(name="claim", description="Claim a ticket")
async def claim_ticket_slash(interaction: discord.Interaction):
    # Check if in a ticket channel
    if "ticket-" not in interaction.channel.name:
        await interaction.response.send_message("❌ This command can only be used in ticket channels.", ephemeral=True)
        return

    # Check if user has staff role
    if not has_staff_role(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to claim tickets.", ephemeral=True)
        return

    # Update the stats for the moderator who claimed the ticket
    user_id = str(interaction.user.id)
    if user_id not in ticket_stats:
        ticket_stats[user_id] = {
            "tickets_claimed": 0,
            "tickets_closed": 0,
            "tickets_participated": 0
        }
    ticket_stats[user_id]["tickets_claimed"] += 1
    save_json(ticket_stats, ticket_stats_file)

    # Extract the ticket creator's name from the original channel name
    original_name = interaction.channel.name
    ticket_creator = original_name.replace("ticket-", "") if "ticket-" in original_name else "unknown"

    # Rename the ticket to include both the claimed user and ticket creator
    new_ticket_name = f"{interaction.user.name}-{ticket_creator}"
    await interaction.channel.edit(name=new_ticket_name)

    # Set permissions for the claimer
    await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True)

    # Ensure all moderators can still talk in the ticket
    mod_role = discord.utils.get(interaction.guild.roles, id=1340726272908726433)
    if mod_role:
        await interaction.channel.set_permissions(mod_role, view_channel=True, send_messages=True)

    # Send claim notification in the ticket channel
    claim_embed = discord.Embed(
        title="Ticket Claimed",
        description=f"{interaction.user.mention} has claimed this ticket and will assist you shortly.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=claim_embed)

@bot.tree.command(name="rename", description="Rename a ticket channel")
async def rename_ticket_slash(interaction: discord.Interaction, new_name: str):
    # Check if in a ticket channel (both unclaimed and claimed formats)
    if not (interaction.channel.name.startswith("ticket-") or "-" in interaction.channel.name):
        await interaction.response.send_message("❌ This command can only be used in ticket channels.", ephemeral=True)
        return

    # Check if user has staff role
    if not has_staff_role(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to rename tickets.", ephemeral=True)
        return

    # Format the new name to ensure it still has ticket- prefix if it doesn't already
    if not new_name.startswith("ticket-"):
        new_name = f"ticket-{new_name}"

    # Rename the channel
    old_name = interaction.channel.name
    try:
        await interaction.channel.edit(name=new_name)

        # Send success message
        embed = discord.Embed(
            title="✅ Ticket Renamed",
            description=f"Ticket renamed from `{old_name}` to `{new_name}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error renaming ticket: {e}", ephemeral=True)

        @bot.tree.command(name="upload_release", description="Upload a new release file to GitHub")
        async def upload_release(interaction: discord.Interaction, version: str, file: discord.Attachment):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                return
            try:
                await interaction.response.defer(ephemeral=True)

                release_name = f"Cys Anime Guardians V{version}"
                headers = {
                    "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
                    "Accept": "application/vnd.github.v3+json"
                }

                repo_owner = "Cyszx"  # GitHub username
                repo_name = "AGMacro.github.io"  # Repository name
                file_content = await file.read()

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            releases = await response.json()
                            for release in releases:
                                async with session.delete(
                                    release['url'],
                                    headers=headers
                                ) as del_response:
                                    if del_response.status != 204:
                                        await interaction.followup.send(f"Error deleting release: {await del_response.text()}", ephemeral=True)
                                        return

                    release_data = {
                        "tag_name": f"v{version}",
                        "name": release_name,
                        "body": f"Release {version}",
                        "draft": False,
                        "prerelease": False
                    }

                    async with session.post(
                        f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases",
                        headers=headers,
                        json=release_data
                    ) as response:
                        if response.status == 201:
                            release_data = await response.json()
                            upload_url = release_data['upload_url'].replace('{?name,label}', '')
                            upload_headers = {
                                **headers,
                                'Content-Type': 'application/octet-stream'
                            }

                            params = {'name': f"Cys Anime Guardians V{version}.zip"}
                            async with session.post(
                                upload_url,
                                headers=upload_headers,
                                params=params,
                                data=file_content
                            ) as upload_response:
                                if upload_response.status == 201:
                                    await interaction.followup.send(f"✅ Successfully uploaded {file.filename} to release: {release_name}", ephemeral=True)
                                else:
                                    await interaction.followup.send(f"❌ Error uploading file: {await upload_response.text()}", ephemeral=True)
                        else:
                            await interaction.followup.send(f"❌ Error creating release: {await response.text()}", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="upload_files", description="Upload files to GitHub releases")
@app_commands.choices(game=[
    app_commands.Choice(name="Anime Guardians", value="Anime Guardians"),
    app_commands.Choice(name="Anime Royale", value="Anime Royale"),
    app_commands.Choice(name="Anime Last Stand", value="Anime Last Stand")
])
async def upload_files(interaction: discord.Interaction, game: str, version: str, update_log: str, file: discord.Attachment, ping: bool = True):
    # Check if the user is the specific user ID
    if interaction.user.id != 1141849395902554202:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    try:
        # Check if user has admin permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Your existing code for handling the file upload would go here

        # Set repo and name based on game selection
        if game.lower() == "anime guardians":
            repo_name = "AGMacro.github.io"
            game_name = "Cys Anime Guardians"
            website_url = "https://cyszx.github.io/AGMacro.github.io/"
        elif game.lower() == "anime royale":
            repo_name = "Anime-Royale-Macro"
            game_name = "Cys Anime Royale"
            website_url = "https://cyszx.github.io/AGMacro.github.io/"
        elif game.lower() == "anime last stand":
            repo_name = "ALS-Macro" # Added repo name for Anime Last Stand
            game_name = "Cys Anime Last Stand" # Added game name for Anime Last Stand
            website_url = "https://cyszx.github.io/ALS-Macro/" # Added website URL for Anime Last Stand
        else:
            await interaction.followup.send("❌ Invalid game selection. Please choose 'Anime Guardians' or 'Anime Royale' or 'Anime Last Stand'", ephemeral=True)
            return

        release_name = f"{game_name} V{version}"
        headers = {
            "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github.v3+json"
        }

        repo_owner = "Cyszx"
        file_content = await file.read()

        async with aiohttp.ClientSession() as session:
            # Delete existing releases first
            async with session.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases",
                headers=headers
            ) as response:
                # Handle case where repository doesn't exist yet
                if response.status == 404:
                    print(f"Repository {repo_name} not found - continuing with release creation")
                    # Continue with creating the first release
                elif response.status == 200:
                    releases = await response.json()
                    for release in releases:
                        async with session.delete(
                            release['url'],
                            headers=headers
                        ) as del_response:
                            if del_response.status != 204:
                                await interaction.followup.send(f"Error deleting release: {await del_response.text()}", ephemeral=True)
                                return

            # Create new release
            release_data = {
                "tag_name": f"v{version}",
                "name": release_name,
                "body": update_log,
                "draft": False,
                "prerelease": False
            }

            async with session.post(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases",
                headers=headers,
                json=release_data
            ) as response:
                if response.status == 201:
                    release_data = await response.json()
                    upload_url = release_data['upload_url'].replace('{?name,label}', '')
                    upload_headers = {
                        **headers,
                        'Content-Type': 'application/octet-stream'
                    }

                    params = {'name': file.filename}
                    async with session.post(
                        upload_url,
                        headers=upload_headers,
                        params=params,
                        data=file_content
                    ) as upload_response:
                        if upload_response.status == 201:
                            # Send success message visible to everyone
                            await interaction.channel.send(f"✅ Successfully uploaded {file.filename} to release: {release_name}")
                            await interaction.followup.send("✅ Upload completed successfully!", ephemeral=True)

                            # Send website link only
                            embed = discord.Embed(
                                title="📥 Download",
                                description=f"[{game_name}]({website_url})",
                                color=discord.Color.blue()
                            )
                            await interaction.channel.send(embed=embed)

                            # Send notification about new upload
                            notification_embed = discord.Embed(
                                title="🆕 New Update Available!",
                                description=f"A new version of {game_name} has been released!\n\n**Version:** v{version}\n\n**Changelog:**\n{update_log}",
                                color=discord.Color.green()
                            )
                            notification_embed.add_field(
                                name="Download",
                                value=f"[Click here to download]({website_url})",
                                inline=False
                            )
                            # Only send with content if ping is True
                            if ping:
                                await interaction.channel.send(content="<@&1338968714338504755>", embed=notification_embed)
                            else:
                                await interaction.channel.send(embed=notification_embed)
                        else:
                            await interaction.followup.send(f"❌ Error uploading file: {await upload_response.text()}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error creating release: {await response.text()}", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="links", description="Get download links")
@app_commands.choices(game=[
    app_commands.Choice(name="Anime Guardians", value="Anime Guardians"),
    app_commands.Choice(name="Anime Royale", value="Anime Royale"),
    app_commands.Choice(name="Anime Last Stand", value="Anime Last Stand")
])
async def links_slash(interaction: discord.Interaction, game: str):
    """Send download links to the chat"""
    game = game.lower()
    if game not in ["anime guardians", "anime royale", "anime last stand"]:
        await interaction.response.send_message("❌ Please specify either 'Anime Guardians', 'Anime Royale', or 'Anime Last Stand'", ephemeral=True)
        return

    game_info = {
        "anime guardians": {
            "name": "Cys Anime Guardians",
            "website": "https://cyszx.github.io/AGMacro.github.io/",
            "github": "https://github.com/Cyszx/AGMacro.github.io/releases/latest"
        },
        "anime royale": {
            "name": "Cys Anime Royale",
            "website": "https://cyszx.github.io/ARMacro.github.io/",
            "github": "https://github.com/Cyszx/ARMacro.github.io/releases/latest"
        },
        "anime last stand": { # Added info for Anime Last Stand
            "name": "Cys Anime Last Stand",
            "website": "https://cyszx.github.io/ALS-Macro/", # Added website URL for Anime Last Stand
            "github": "https://github.com/Cyszx/ALS-Macro/releases/latest" # Added GitHub URL for Anime Last Stand
        }
    }

    info = game_info[game]
    embed = discord.Embed(
        title=f"📥 {info['name']} Download Links",
        description="Latest version and files can be found here:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Download",
        value=f"[{info['name']}]({info['website']})",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="prefixset", description="Set the bot's command prefix")
async def prefixset_slash(interaction: discord.Interaction, prefix: str):
    """Set a new prefix for text commands"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to change the prefix.", ephemeral=True)
        return

    if len(prefix) > 1:
        await interaction.response.send_message("❌ Prefix must be a single character.", ephemeral=True)
        return

    bot.custom_prefix = prefix
    save_prefix(prefix)
    await interaction.response.send_message(f"✅ Command prefix set to: `{prefix}`")

@bot.tree.command(name="uptime", description="Show bot uptime")
async def uptime_slash(interaction: discord.Interaction):
    """Show the bot's uptime"""
    if not bot.start_time:
        await interaction.response.send_message("Bot start time not available.", ephemeral=True)
        return

    current_time = datetime.datetime.utcnow()
    delta = current_time - bot.start_time

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

    embed = discord.Embed(
        title="🕒 Bot Uptime",
        description=f"Bot has been online for: **{uptime_str}**",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Started at: {bot.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stats", description="Show ticket statistics")
async def stats_slash(interaction: discord.Interaction):
    # Check if user has admin permission or is staff
    if not (interaction.user.guild_permissions.administrator or has_staff_role(interaction.user)):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    # Reload the stats from the JSON file to ensure we have the latest data
    global ticket_stats
    ticket_stats = load_json(ticket_stats_file)

    # Create member map for easy lookup
    member_map = {}
    for member in interaction.guild.members:
        member_map[str(member.id)] = member

    # Try to fetch additional users that aren't in the member cache
    for user_id in ticket_stats.keys():
        if user_id not in member_map and user_id != "level_notification_channel":
            try:
                # Attempt to fetch the user from Discord API
                user = await bot.fetch_user(int(user_id))
                if user:
                    member_map[user_id] = user
            except Exception as e:
                print(f"Could not fetch user {user_id}: {e}")

    # Prepare data for all users first
    all_users_data = []

    # First add users who have stats in the ticket_stats file
    for user_id, stats in ticket_stats.items():
        # Skip non-user entries like level_notification_channel
        if not user_id.isdigit():
            continue

        # Format user ID as a mention
        mention = f"<@{user_id}>"

        # Get display name if possible
        if user_id in member_map:
            user = member_map[user_id]
            display_name = user.display_name if hasattr(user, 'display_name') else user.name
        else:
            display_name = f"User-{user_id}"

        all_users_data.append({
            "id": user_id,
            "display_name": display_name,
            "mention": mention,
            "participated": stats.get('tickets_participated', 0),
            "claimed": stats.get('tickets_claimed', 0),
            "closed": stats.get('tickets_closed', 0)
        })

    # Then add staff members who don't have stats
    shown_members = set(user_id for user_id in ticket_stats.keys() if user_id.isdigit())

    for member_id, member in member_map.items():
        if member_id not in shown_members and has_staff_role(member):
            all_users_data.append({
                "id": member_id,
                "display_name": member.display_name,
                "mention": f"<@{member_id}>",
                "participated": 0,
                "claimed": 0,
                "closed": 0
            })

    # Create embeds with stats
    embeds = []
    current_embed = discord.Embed(
        title="📊 Ticket Statistics for ALL Members",
        description="This shows how many tickets each member has participated in, claimed, or closed.",
        color=discord.Color.blue()
    )
    embeds.append(current_embed)

    field_count = 0

    for user_data in all_users_data:
        # If we've hit 24 fields, create a new embed
        if field_count >= 24:
            current_embed = discord.Embed(
                title="📊 Ticket Statistics (Continued)",
                color=discord.Color.blue()
            )
            embeds.append(current_embed)
            field_count = 0

        # Add field to current embed
        current_embed.add_field(
            name=f"👤 {user_data['display_name']}",
            value=(f"{user_data['mention']}\n"
                    f"🎟 **Participated:** {user_data['participated']}\n"
                    f"✅ **Claimed:** {user_data['claimed']}\n"
                    f"🔒 **Closed:** {user_data['closed']}\n"
                    f"💬 **Messages:** {user_data.get('messages_sent', 0)}\n"
                    f"📊 **Avg/Participation:** {user_data.get('messages_sent', 0) / user_data['participated'] if user_data['participated'] > 0 else 0:.2f}"),
            inline=True
        )
        field_count += 1

    # Add footer to the last embed
    embeds[-1].set_footer(text=f"Showing stats for {len(all_users_data)} members")

    # Send the first embed
    await interaction.response.send_message(embed=embeds[0])

    # Send any additional embeds
    if len(embeds) > 1:
        for embed in embeds[1:]:
            await interaction.followup.send(embed=embed)


@bot.command()
async def transcript(ctx, channel: discord.TextChannel = None):
     """Generates a transcript of a specified channel."""
     if channel is None:
          channel = ctx.channel  

     messages = await channel.history(limit=1000).flatten()
     transcript_content = ""

     for message in reversed(messages):
          timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
          transcript_content += f"[{timestamp}] {message.author}: {message.content}\n"

     file_name = f"transcript-{channel.name}-{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
     with open(file_name, "w", encoding="utf-8") as file:
          file.write(transcript_content)

     await ctx.send(file=discord.File(file_name))

@bot.command()
async def claim(ctx):
     """Marks a ticket as claimed by the user."""
     if ctx.channel.id not in ticket_data:
          ticket_data[ctx.channel.id] = {}
     ticket_data[ctx.channel.id]['claimedby'] = ctx.author
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

     embed = discord.Embed(title="Ticket Closed", color=discord.Color.red())
     embed.add_field(name="Closed by", value=ctx.author.mention, inline=True)
     embed.add_field(name="Claimed by", value=claimed_by.mention if isinstance(claimed_by, discord.Member) else claimed_by, inline=True)
     embed.add_field(name="Reason", value=reason, inline=False)
     embed.set_footer(text=f"Ticket ID: {ctx.channel.id}")

     log_channel = await bot.fetch_channel(1345810536457179136)
     if log_channel is None:
          await ctx.send("Log channel not found. Please check the channel ID.")
          return

     await log_channel.send(embed=embed)
     transcript_file = discord.File(file_name)
     await log_channel.send(file=transcript_file)
     os.remove(file_name)  # Delete the transcript file after sending it

@bot.command()
async def stats(ctx):
     """Show ticket stats for all staff members, including those with no activity."""
     # Check if user has admin permission or is staff
     if not (ctx.author.guild_permissions.administrator or has_staff_role(ctx.author)):
          await ctx.send("❌ You don't have permission to use this command.")
          return

     # Reload the stats from the JSON file to ensure we have the latest data
     global ticket_stats
     ticket_stats = load_json(ticket_stats_file)

     # Debug - print ticket stats for verification
     print(f"Loaded ticket stats: {ticket_stats}")

     # Create member map for easy lookup and to fetch missing users
     member_map = {}
     for member in ctx.guild.members:
          member_map[str(member.id)] = member

     # Try to fetch additional users that aren't in the member cache
     for user_id in ticket_stats.keys():
          if user_id not in member_map and user_id != "level_notification_channel":
               try:
                    # Attempt to fetch the user from Discord API
                    user = await bot.fetch_user(int(user_id))
                    if user:
                         member_map[user_id] = user
               except Exception as e:
                    print(f"Could not fetch user {user_id}: {e}")

     # Prepare data for all users first
     all_users_data = []

     # First add users who have stats in the ticket_stats file
     for user_id, stats in ticket_stats.items():
          # Skip non-user entries like level_notification_channel
          if not user_id.isdigit():
               continue

          # Format user ID as a mention
          mention = f"<@{user_id}>"

          # Get display name if possible
          if user_id in member_map:
               user = member_map[user_id]
               display_name = user.display_name if hasattr(user, 'display_name') else user.name
          else:
               display_name = f"User-{user_id}"

          all_users_data.append({
               "id": user_id,
               "display_name": display_name,
               "mention": mention,
               "participated": stats.get('tickets_participated', 0),
               "claimed": stats.get('tickets_claimed', 0),
               "closed": stats.get('tickets_closed', 0),
               "messages_sent": stats.get('messages_sent', 0)
          })

     # Then add staff members who don't have stats
     shown_members = set(user_id for user_id in ticket_stats.keys() if user_id.isdigit())

     for member_id, member in member_map.items():
          if member_id not in shown_members and has_staff_role(member):
               all_users_data.append({
                    "id": member_id,
                    "display_name": member.display_name,
                    "mention": f"<@{member_id}>",
                    "participated": 0,
                    "claimed": 0,
                    "closed": 0,
                    "messages_sent": 0
               })

     # Now create and send embeds with 24 fields max each
     if not all_users_data:
          await ctx.send("No ticket statistics to display.")
          return

     # Create embeds with 24 fields each (leaving room for title/description)
     embeds = []
     current_embed = discord.Embed(
          title="📊 Ticket Statistics for ALL Members",
          description="This shows how many tickets each member has participated in, claimed, or closed.",
          color=discord.Color.blue()
     )
     embeds.append(current_embed)

     field_count = 0

     for user_data in all_users_data:
          # If we've hit 24 fields, create a new embed
          if field_count >= 24:
               current_embed = discord.Embed(
                    title="📊 Ticket Statistics (Continued)",
                    color=discord.Color.blue()
               )
               embeds.append(current_embed)
               field_count = 0

          # Add field to current embed
          current_embed.add_field(
               name=f"👤 {user_data['display_name']}",
               value=(f"{user_data['mention']}\n"
                      f"🎟 **Participated:** {user_data['participated']}\n"
                      f"✅ **Claimed:** {user_data['claimed']}\n"
                      f"🔒 **Closed:** {user_data['closed']}"),
               inline=True
          )
          field_count += 1

     # Add footer to the last embed
     embeds[-1].set_footer(text=f"Showing stats for {len(all_users_data)} members")

     # Send all embeds
     for embed in embeds:
          await ctx.send(embed=embed)

# Run the bot with the provided token
bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
     error_msg = "ERROR: BOT_TOKEN environment variable is not set! Please add it in the Secrets tab."
     print(error_msg)
else:
     try:
          # Connect to Discord
          print("Attempting to connect to Discord...")
          bot.run(bot_token)
     except Exception as e:
          error_message = f"Failed to start the bot: {str(e)}"
          print("\n⚠️ ERROR DETAILS ⚠️")
          print(error_message)
