import nest_asyncio
nest_asyncio.apply()
import builtins
from discord.ext import commands
import discord
from discord_slash.utils.manage_commands import create_option, create_choice
from ahri import utils, backend, hookcord
import time
import importlib

global CLIENT_LOADED
global CM
if not CLIENT_LOADED:
	print("Initializing client!")
	builtins.ext_modules = {}
	builtins.ALLOW_RELOAD = False
	builtins.FRONT_RELOAD_FUNC = None
	builtins.client = hookcord.Bot(intents=discord.Intents.default(), command_prefix="a!")
	builtins.guild_ids = utils.CONFIG["elevated_guilds"]
	builtins.slash = hookcord.SlashCommand(client, sync_commands=True) # Declares slash commands through the client.	

backend.pass_client(client)
backend.pass_context_manager(CM)
	
def get_client():
	return client
	
def pass_module(module):
	builtins.ext_modules[module.__name__] = module
	fdots = module.__name__.find(".") + 1
	builtins.ext_modules[module.__name__[fdots:]] = module
	
def allow_self_reload(bool, func):
	if bool:
		builtins.ALLOW_RELOAD = bool
		builtins.FRONT_RELOAD_FUNC = func

@client.command(name="lookup")
async def lookup(ctx):
	print("Lookup!")
	try:
		await ctx.author.send("Ahri is currently going through a complete rebuild right now, all commands are disabled for an unknown duration.")
	except:
		pass
		
@slash.slash(guild_ids=guild_ids, **utils.cmd_gen("execute"))
async def execute(ctx, subcommand=""):
	if subcommand == "modules":
		print(ext_modules)
	elif subcommand == "modules2":
		print(await backend.get_modules())
		
@slash.slash(guild_ids=guild_ids, name="reboot")
async def reboot(ctx):
	await ctx.send("Rebooting!")
	backend.restart_program()
		
@slash.slash(guild_ids=guild_ids, **utils.cmd_gen("reload"))
async def reload_module(ctx, module):
	await ctx.send("Working!", delete_after=1)
	if module == "backend":
		importlib.reload(backend)
		print("backend reloaded!")
	elif module in ext_modules:
		importlib.reload(ext_modules[module])
		print(f"{module} reloaded!")
	elif module == "cf" or module == "command front":
		if ALLOW_RELOAD: FRONT_RELOAD_FUNC()
	else:
		await backend.reload(module)
	
@slash.slash(guild_ids=guild_ids, **utils.cmd_gen("lookup"))
async def slash_lookup(ctx, name, region="NA1", champion=None, games=20):
	st = time.time()
	await ctx.defer()
	embed = await backend.player_lookup(name, region, champion, games)
	await embed.send(ctx)
	print(time.time() - st)
	
@slash.subcommand(guild_ids=guild_ids, base="embed", **utils.cmd_gen("register_embed"))
async def register_embed(ctx, name, messages):
	counter = 0
	merger = []
	async for message in ctx.channel.history(limit=100):
		if message.author == ctx.author:
			merger.append(message.content)
			counter += 1
		if counter >= messages: break
	merger.reverse()
	response = await backend.register_embed(name, "\n".join(merger), ctx.author)
	await ctx.send(content=response)

@slash.subcommand(guild_ids=guild_ids, base="embed", **utils.cmd_gen("test_embed"))
async def test_embed(ctx, messages, hidden=True):
	counter = 0
	merger = []
	async for message in ctx.channel.history(limit=100):
		if message.author == ctx.author:
			merger.append(message.content)
			counter += 1
		if counter >= messages: break
	merger.reverse()
	response = await backend.test_embed("\n".join(merger), ctx.author)
	try: await response.send(ctx, hidden=hidden)
	except AttributeError: await ctx.send(content=response, hidden=hidden)
		
@slash.subcommand(guild_ids=guild_ids, base="stock", **utils.cmd_gen("stock_buy"))
async def stock_buy(ctx, stock, amount):
	embed = await backend.confirm_stock_purchase(ctx.author, stock, amount)
	try: await embed.send(ctx, hidden=True)
	except AttributeError: await ctx.send(embed, hidden=True)
		
@slash.subcommand(guild_ids=guild_ids, base="stock", **utils.cmd_gen("stock_details"))
async def stock_details(ctx, stock):
	embed = await backend.show_stock_details(stock)
	try: await embed.send(ctx, hidden=True)
	except AttributeError: await ctx.send(embed, hidden=True)
	
@slash.subcommand(guild_ids=guild_ids, base="stock", **utils.cmd_gen("stock_graph"))
async def stock_graph(ctx, stock, type):
	graph = await backend.stock_graph(stock, type)
	await ctx.author.send(file=graph)
	await ctx.send(":white_check_mark: **Sent graph to DMs!**", hidden=True)
	
@slash.subcommand(guild_ids=guild_ids, base="stock", **utils.cmd_gen("stock_quantify"))
async def stock_quantify(ctx, stock, charms):
	amount = await backend.stock_quantify(stock, charms)
	charms = '{:,}'.format(charms)
	amount = '{:,}'.format(round(amount, 4))
	await ctx.send(content=f":white_check_mark: **{charms} C** can purchase **{amount} {stock}**", hidden=True)
	
@slash.subcommand(guild_ids=guild_ids, base="stock", **utils.cmd_gen("stock_signup"))
async def stock_signup(ctx):
	embed = await backend.prepose_stock_agreement(ctx.author)
	try: await embed.send(ctx, hidden=True)
	except AttributeError: await ctx.send(content=embed, hidden=True)
	
	
@slash.slash(guild_ids=guild_ids, **utils.cmd_gen("debug"))
async def debug(ctx, hidden=False):
	await backend.debug(ctx)
	em = discord.Embed(title='Debug Info', description='Debugging Info', colour=0xfc8403)
	em.set_thumbnail(url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRhTGD6HPMFDBhjO8VGL6UH634ksXFcovCCZifQywFcbhAdwFP8Mg')
	em.set_author(name='Blitzcrank', icon_url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRhTGD6HPMFDBhjO8VGL6UH634ksXFcovCCZifQywFcbhAdwFP8Mg')
	em.add_field(name=ctx.author.name, value=ctx.author.id, inline=False)
	em.add_field(name=ctx.channel.name, value=ctx.channel.id, inline=False)
	em.add_field(name=ctx.guild.name, value=ctx.guild.id, inline=False)
	#await ctx.send(embed=em, hidden=hidden)