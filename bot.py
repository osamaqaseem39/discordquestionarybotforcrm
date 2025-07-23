import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()

# Bot configuration
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GOHIGHLEVEL_WEBHOOK_URL = os.getenv('GOHIGHLEVEL_WEBHOOK_URL')
VERIFY_CHANNEL_NAME = '✅-vérification-accès'
VERIFIED_ROLE_NAME = 'Verified'

# Verification questions (in French)
VERIFICATION_QUESTIONS = [
    "Qu'est-ce qui vous intéresse le plus dans Amazon FBA ?",
    "Avez-vous déjà essayé Amazon FBA ?",
    "Quel est votre plus grand défi avec FBA en ce moment ?",
    "Vendez-vous actuellement ou êtes-vous en phase de recherche ?"
]

# Question keys for JSON payload
QUESTION_KEYS = ['interest', 'experience', 'challenge', 'status']

class VerificationModal(discord.ui.Modal):
    def __init__(self, bot, step: int):
        self.bot = bot
        self.step = step
        super().__init__(title=f"Question {step + 1} of {len(VERIFICATION_QUESTIONS)}")
        
        # Add the question as a text input
        self.question_input = discord.ui.TextInput(
            label=VERIFICATION_QUESTIONS[step],
            style=discord.TextStyle.paragraph,
            placeholder="Please provide a detailed answer...",
            required=True,
            max_length=1000
        )
        self.add_item(self.question_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        try:
            user_id = interaction.user.id
            
            # Get user session
            if user_id not in self.bot.verification_sessions:
                await interaction.response.send_message(
                    "❌ Session de vérification introuvable. Veuillez contacter un administrateur.",
                    ephemeral=True
                )
                return
            
            session = self.bot.verification_sessions[user_id]
            
            # Store the answer
            answer = self.question_input.value.strip()
            session['answers'].append(answer)
            session['step'] += 1
            
            # Check if more questions remain
            if session['step'] < len(VERIFICATION_QUESTIONS):
                embed = discord.Embed(
                    title="✅ Réponse enregistrée!",
                    description=f"Question {self.step + 1} répondu avec succès.\n\nUtilisez `/verify` à nouveau pour continuer avec la question {session['step'] + 1}.",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # All questions completed
                await interaction.response.send_message(
                    "✅ Toutes les questions répondues! Traitement de votre vérification...",
                    ephemeral=True
                )
                # Complete verification
                guild = interaction.guild
                await self.bot.complete_verification(interaction.user, guild)
            
        except Exception as e:
            print(f"Error in modal submission: {e}")
            await interaction.response.send_message(
                "❌ Une erreur est survenue lors de l'enregistrement de votre réponse. Veuillez réessayer.",
                ephemeral=True
            )

class VerificationBot(commands.Bot):
    def __init__(self):
        # Set up bot intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Dictionary to store active verification sessions
        # Format: {user_id: {'step': int, 'answers': [], 'guild_id': int, 'join_date': datetime}}
        self.verification_sessions = {}
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        print("Bot is starting up...")
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guild(s)')
        
        # Print guild information for debugging
        for guild in self.guilds:
            print(f'- {guild.name} (ID: {guild.id})')
        
        # Generate proper bot invite URL with correct permissions
        permissions = discord.Permissions(
            manage_roles=True,
            send_messages=True,
            add_reactions=True,
            read_message_history=True,
            send_messages_in_threads=True,
            manage_messages=True
        )
        
        invite_url = discord.utils.oauth_url(self.user.id, permissions=permissions, scopes=['bot', 'applications.commands'])
        print(f"\n=== BOT INVITE URL WITH CORRECT PERMISSIONS ===")
        print(f"If role assignment keeps failing, use this URL to re-invite the bot:")
        print(f"{invite_url}")
        print("=== END INVITE URL ===\n")
    
    async def on_member_join(self, member):
        """Called when a new member joins the server"""
        try:
            print(f"New member joined: {member.name} (ID: {member.id})")
            
            # Clear any existing verification session for this user
            if member.id in self.verification_sessions:
                print(f"Clearing existing verification session for {member}")
                del self.verification_sessions[member.id]
            
            # Initialize verification session
            self.verification_sessions[member.id] = {
                'step': 0,
                'answers': [],
                'guild_id': member.guild.id,
                'join_date': member.joined_at or datetime.now(timezone.utc)
            }
            
            # Find the verification channel
            verify_channel = discord.utils.get(member.guild.channels, name=VERIFY_CHANNEL_NAME)
            if not verify_channel:
                print(f"Error: #{VERIFY_CHANNEL_NAME} channel not found in {member.guild.name}")
                return
            
            # Send verification message in the designated channel
            embed = discord.Embed(
                title="🎉 Bienvenue dans la communauté Amazon FBA!",
                description=f"Hey {member.mention}! Pour obtenir la vérification et accéder à tous les canaux, veuillez réagir avec ✅ à ce message pour démarrer le processus de vérification.",
                color=0x00ff00
            )
            embed.add_field(
                name="📝 Ce qui se passe ensuite:",
                value="• Réagissez avec ✅ ci-dessous pour démarrer\n• Répondez à 4 questions Amazon FBA en privé\n• Obtenez votre rôle Vérifié automatiquement",
                inline=False
            )
            embed.set_footer(text=f"Bienvenue {member.display_name}!")
            
            # Send the message and add reaction
            verification_msg = await verify_channel.send(f"{member.mention}", embed=embed)
            await verification_msg.add_reaction('✅')
            print(f"Sent welcome message to {member} in {verify_channel.name}")
            
            # Store the message ID for this user's verification
            self.verification_sessions[member.id]['message_id'] = verification_msg.id
            
        except Exception as e:
            print(f"Error in on_member_join: {e}")
    
    async def on_reaction_add(self, reaction, user):
        """Handle reaction-based verification trigger"""
        try:
            # Ignore bot reactions
            if user.bot:
                return
            
            # Check if reaction is in verification channel
            if reaction.message.channel.name != VERIFY_CHANNEL_NAME:
                return
            
            # Check if it's the correct reaction
            if str(reaction.emoji) != '✅':
                return
            
            # Check if user has an active verification session
            if user.id not in self.verification_sessions:
                return
            
            session = self.verification_sessions[user.id]
            
            # Check if this is their verification message
            if reaction.message.id != session.get('message_id'):
                return
            
            # Start the verification process with first question
            current_step = session['step']
            if current_step < len(VERIFICATION_QUESTIONS):
                modal = VerificationModal(self, current_step)
                
                # Create a temporary interaction-like object for the modal
                # Since we can't send modals from reaction events, we'll send a DM instead
                try:
                    embed = discord.Embed(
                        title=f"Question {current_step + 1} of {len(VERIFICATION_QUESTIONS)}",
                        description=f"**{VERIFICATION_QUESTIONS[current_step]}**",
                        color=0x3498db
                    )
                    embed.add_field(
                        name="📝 Comment répondre:",
                        value="Veuillez répondre à ce DM avec votre réponse. Votre réponse sera privée.",
                        inline=False
                    )
                    await user.send(embed=embed)
                    
                    # Update session to indicate we're waiting for DM response
                    session['awaiting_dm'] = True
                    
                except discord.Forbidden:
                    # If DM fails, send ephemeral message in channel
                    embed = discord.Embed(
                        title="⚠️ DM requis",
                        description=f"{user.mention} Veuillez activer les DM des membres du serveur pour compléter la vérification, ou contactez un administrateur pour de l'aide.",
                        color=0xff9900
                    )
                    await reaction.message.channel.send(embed=embed, delete_after=10)
            
        except Exception as e:
            print(f"Error in reaction handler: {e}")
    
    async def on_message(self, message):
        """Handle DM responses for verification"""
        try:
            # Ignore bot messages
            if message.author.bot:
                return
            
            # Only process DMs
            if not isinstance(message.channel, discord.DMChannel):
                return
            
            user_id = message.author.id
            
            # Check if user has an active verification session
            if user_id not in self.verification_sessions:
                return
            
            session = self.verification_sessions[user_id]
            
            # Check if we're waiting for a DM response
            if not session.get('awaiting_dm'):
                return
            
            # Store the answer
            answer = message.content.strip()
            session['answers'].append(answer)
            session['step'] += 1
            session['awaiting_dm'] = False
            
            # Send confirmation
            await message.add_reaction('✅')
            
            # Check if more questions remain
            if session['step'] < len(VERIFICATION_QUESTIONS):
                # Send next question
                embed = discord.Embed(
                    title=f"Question {session['step'] + 1} of {len(VERIFICATION_QUESTIONS)}",
                    description=f"**{VERIFICATION_QUESTIONS[session['step']]}**",
                    color=0x3498db
                )
                embed.add_field(
                    name="📝 Comment répondre:",
                    value="Veuillez répondre à ce DM avec votre réponse. Votre réponse sera privée.",
                    inline=False
                )
                await message.author.send(embed=embed)
                session['awaiting_dm'] = True
            else:
                # All questions completed
                completion_embed = discord.Embed(
                    title="✅ Toutes les questions répondues!",
                    description="Traitement de votre vérification...",
                    color=0x00ff00
                )
                await message.author.send(embed=completion_embed)
                
                # Complete verification
                guild = self.get_guild(session['guild_id'])
                if guild:
                    member = guild.get_member(message.author.id)
                    if member:
                        await self.complete_verification(member, guild)
                    else:
                        print(f"Could not find member {message.author} in guild {guild.name}")
            
        except Exception as e:
            print(f"Error processing DM: {e}")

    @app_commands.command(name="verify", description="Start the Amazon FBA verification process")
    async def verify_command(self, interaction: discord.Interaction):
        """Slash command to start verification process"""
        try:
            user_id = interaction.user.id
            
            # Check if user has an active verification session
            if user_id not in self.verification_sessions:
                await interaction.response.send_message(
                    "❌ Vous n'avez pas de session de vérification active. Cela peut être dû à:\n"
                    "• Vous avez déjà complété la vérification\n"
                    "• Votre session a expiré\n"
                    "• Vous avez rejoint le serveur avant que le bot ne soit en ligne\n\n"
                    "Veuillez contacter un administrateur pour de l'aide.",
                    ephemeral=True
                )
                return
            
            session = self.verification_sessions[user_id]
            current_step = session['step']
            
            if current_step >= len(VERIFICATION_QUESTIONS):
                await interaction.response.send_message(
                    "✅ Vous avez déjà complété toutes les questions de vérification!",
                    ephemeral=True
                )
                return
            
            # Create and send the modal for the current question
            modal = VerificationModal(self, current_step)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            print(f"Error in verify command: {e}")
            await interaction.response.send_message(
                "❌ Une erreur est survenue. Veuillez réessayer plus tard.",
                ephemeral=True
            )
    
    async def complete_verification(self, member, guild):
        """Complete the verification process"""
        try:
            session = self.verification_sessions.get(member.id)
            if not session:
                return
            
            # Debug: Print bot permissions and role info
            bot_member = guild.get_member(self.user.id)
            if bot_member:
                print(f"Bot permissions: manage_roles={bot_member.guild_permissions.manage_roles}, administrator={bot_member.guild_permissions.administrator}")
                print(f"Bot top role: {bot_member.top_role.name} (position: {bot_member.top_role.position})")
            
            # Find and assign the verified role
            verified_role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
            
            if not verified_role:
                print(f"Error: '{VERIFIED_ROLE_NAME}' role not found in {guild.name}")
                # Create the role if it doesn't exist - place it at the bottom
                try:
                    verified_role = await guild.create_role(
                        name=VERIFIED_ROLE_NAME,
                        color=discord.Color.green(),
                        reason="Verification bot role creation"
                    )
                    print(f"Created '{VERIFIED_ROLE_NAME}' role in {guild.name} at position {verified_role.position}")
                    
                    # Try to move the verified role below the bot role
                    bot_member = guild.get_member(self.user.id)
                    if bot_member and bot_member.top_role.position > 1:
                        try:
                            await verified_role.edit(position=bot_member.top_role.position - 1)
                            print(f"Moved Verified role to position {verified_role.position}")
                        except Exception as e:
                            print(f"Failed to move verified role position: {e}")
                            
                except Exception as e:
                    print(f"Failed to create verified role: {e}")
                    return
            else:
                print(f"Found '{VERIFIED_ROLE_NAME}' role at position {verified_role.position}")
            
            # Debug: Check role hierarchy (lower position number = higher in hierarchy)
            if bot_member and verified_role.position >= bot_member.top_role.position:
                print(f"Role hierarchy issue: Bot role position {bot_member.top_role.position} needs to be LOWER than Verified role position {verified_role.position}")
                print("The bot role needs to be moved HIGHER in the Discord server role list")
            
            print(f"Attempting to assign '{VERIFIED_ROLE_NAME}' role to {member.name}")
            print(f"Member current roles: {[role.name for role in member.roles]}")
            
            # Check if user already has the role
            if verified_role in member.roles:
                print(f"{member} already has the {VERIFIED_ROLE_NAME} role")
            else:
                # Try multiple methods to assign the role
                role_assigned = False
                
                # Method 1: Direct role assignment
                try:
                    await member.add_roles(verified_role, reason="Completed verification process")
                    print(f"Successfully assigned {VERIFIED_ROLE_NAME} role to {member}")
                    role_assigned = True
                except discord.Forbidden as e:
                    print(f"Method 1 failed - Missing permissions: {e}")
                except Exception as e:
                    print(f"Method 1 failed - Error: {e}")
                
                # Method 2: Try editing member roles directly
                if not role_assigned:
                    try:
                        new_roles = list(member.roles) + [verified_role]
                        await member.edit(roles=new_roles, reason="Completed verification process")
                        print(f"Successfully assigned {VERIFIED_ROLE_NAME} role to {member} via edit method")
                        role_assigned = True
                    except discord.Forbidden as e:
                        print(f"Method 2 failed - Missing permissions: {e}")
                    except Exception as e:
                        print(f"Method 2 failed - Error: {e}")
                
                if not role_assigned:
                    # Send admin notification in verification channel
                    verify_channel = discord.utils.get(guild.channels, name=VERIFY_CHANNEL_NAME)
                    if verify_channel:
                        admin_embed = discord.Embed(
                            title="🔧 Attribution de rôle manuelle nécessaire",
                            description=f"**{member.mention} a complété la vérification** mais je ne peux pas attribuer les rôles automatiquement.\n\n**Action requise par l'administrateur:**\nVeuillez attribuer manuellement le rôle `{VERIFIED_ROLE_NAME}` à {member.mention}",
                            color=0xffa500
                        )
                        await verify_channel.send(embed=admin_embed)
                    
                    # Also send DM to user
                    try:
                        user_embed = discord.Embed(
                            title="✅ Vérification complète - Revue requise par l'administrateur",
                            description=f"Vous avez répondu avec succès à toutes les questions de vérification! Un administrateur a été notifié pour attribuer manuellement votre rôle `{VERIFIED_ROLE_NAME}`.",
                            color=0x00ff00
                        )
                        await member.send(embed=user_embed)
                    except:
                        pass
                    
                    print(f"Role assignment failed for {member} - admin notification sent")
                    # Continue with webhook submission even if role assignment fails
                else:
                    print("Role assignment successful!")
            
            # Send DM confirmation
            try:
                dm_embed = discord.Embed(
                    title="🎉 Vous êtes maintenant vérifié! Bienvenue à bord!",
                    description="Merci d'avoir complété le processus de vérification. Vous avez maintenant accès à tous les canaux de la communauté Amazon FBA!",
                    color=0x00ff00
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                print(f"Could not send DM to {member} (DMs might be disabled)")
            
            # Send data to GoHighLevel webhook
            await self.send_to_webhook(member, session)
            
            # Clean up the session
            del self.verification_sessions[member.id]
            
        except Exception as e:
            print(f"Error completing verification: {e}")
    
    async def send_to_webhook(self, member, session):
        """Send verification data to GoHighLevel webhook"""
        try:
            if not GOHIGHLEVEL_WEBHOOK_URL:
                print("Warning: GOHIGHLEVEL_WEBHOOK_URL not set")
                return
            
            # Prepare the payload
            sanitized_username = re.sub(r'[^a-zA-Z0-9._]', '_', member.name)
            payload = {
                "username": f"{member.name}#{member.discriminator}" if member.discriminator != "0" else member.name,
                "user_id": str(member.id),
                "join_date": session['join_date'].isoformat(),
                "email": f"{sanitized_username}@discord.com",
                "phone": "+1111111111",
                "answers": {}
            }
            
            # Map answers to question keys
            for i, answer in enumerate(session['answers']):
                if i < len(QUESTION_KEYS):
                    payload["answers"][QUESTION_KEYS[i]] = answer
            
            # Send the webhook request
            async with aiohttp.ClientSession() as session_http:
                async with session_http.post(
                    GOHIGHLEVEL_WEBHOOK_URL,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        print(f"Successfully sent webhook data for {member}")
                    else:
                        response_text = await response.text()
                        print(f"Webhook request failed with status {response.status}: {response_text}")
        
        except Exception as e:
            print(f"Error sending webhook: {e}")

# Create and run the bot
def main():
    if not DISCORD_TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables")
        print("Please check your .env file or environment configuration")
        return
    
    if not GOHIGHLEVEL_WEBHOOK_URL:
        print("Warning: GOHIGHLEVEL_WEBHOOK_URL not found in environment variables")
        print("Webhook functionality will be disabled")
    
    bot = VerificationBot()
    
    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("Error: Invalid Discord bot token")
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    main()
