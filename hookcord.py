from discord.ext.commands import core, bot, errors
import discord_slash

class HookedMixin(core.GroupMixin):
	def __init__(self, *args, **kwargs):
		super(HookedMixin, self).__init__(*args, **kwargs)
		print("Hooked!")
		
	def add_command(self, command):
		try: super().add_command(command)
		except errors.CommandRegistrationError:
			print(f"[Warning] - The command {command} could not be added, this behavior is bypassed in the hooked version of this class.")
			if command.name in self.all_commands:
				self.all_commands.pop(command.name)
				for alias in command.aliases:
					if alias in self.all_commands:
						self.all_commands.pop(alias)
				super().add_command(command)
			

class Bot(bot.Bot):
	def __init__(self, *args, **kwargs):
		bot.BotBase.__bases__ = (HookedMixin,)
		super(Bot, self).__init__(*args, **kwargs)
		
class SlashCommand(discord_slash.SlashCommand):
	def __init__(self, *args, **kwargs):
		super(SlashCommand, self).__init__(*args, **kwargs)
		
	def add_slash_command(self, cmd, name: str=None, *args, **kwargs):
		try: super().add_slash_command(cmd, name, *args, **kwargs)
		except discord_slash.error.DuplicateCommand:
			print(f"[Warning] - The slash command {name} could not be added, this behavior is bypassed in the hooked version of this class.")
			if name in self.commands:
				self.commands.pop(name)
				super().add_slash_command(cmd, name, *args, **kwargs)
		