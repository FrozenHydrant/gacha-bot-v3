import discord
from discord.ext import commands
import gacha
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='ricky ', intents=intents)

user_handle = gacha.UserHandle()
user_handle.load_users()

COLOURS = {"Common": discord.Colour.light_gray(), "Rare": discord.Colour.blue(), "Epic": discord.Colour.purple(), "Legendary": discord.Colour.gold()}

@bot.command()
async def test(ctx):
    await ctx.send("Test!_")

@bot.command()
async def gacha(ctx):
    user_handle.user_init(ctx.author.id)
    success, item = user_handle.user_gacha(ctx.author.id)

    user_handle.save_users()
    if not success:
        time_left = item - datetime.now()
        await ctx.send(ctx.author.mention + ", you must wait **" + str(time_left.days) + " days, " + str(time_left.seconds // 3600) + " hours and " + str(time_left.seconds % 3600 // 60) + " minutes** to wish again!")
    else:
        image_file = discord.File("img/"+item["id"]+".png", filename=item["id"]+".png")
        wish_embed = discord.Embed(title=ctx.author.display_name+"'s "+item["name"], description="*"+item["description"]+"*", colour=COLOURS[item["rarity"]]).set_footer(text=item["source"]).set_image(url="attachment://"+item["id"]+".png").set_thumbnail(url=ctx.author.avatar).add_field(name="Rarity", value=item["rarity"]).add_field(name="Collection", value=item["collection"])
                                                                                                                                                                                                                                                                                                                                                                   

        await ctx.send(ctx.author.mention + ", wishes left: " + user_handle.wishes(ctx.author.id), file=image_file, embed=wish_embed)

@bot.command()
async def progress(ctx):
    user_handle.user_init(ctx.author.id)

    info = user_handle.collections(ctx.author.id)

    collections_embed = discord.Embed(title=ctx.author.display_name+"'s Collection Progress", description="Here's "+ctx.author.display_name+"'s progress to completing each collection.").set_thumbnail(url=ctx.author.avatar)
    for collection_name in info:
        collections_embed.add_field(name=collection_name, value=str(info[collection_name][0])+"/"+str(info[collection_name][1]))

    await ctx.send(embed=collections_embed)

@bot.command()
async def attack(ctx, *args):
    args = " ".join(args)
    
    user_handle.user_init(ctx.author.id)

    guild = ctx.guild
    targets = await guild.query_members(args)
    target = None
    if len(targets) > 0:
        target = targets[0]

    if target is not None:
        user_handle.user_init(target.id)

        body, win = user_handle.attack(ctx.author.id, ctx.author.display_name, target.id, target.display_name)

        attack_embed = discord.Embed(title=ctx.author.display_name+"'s onslaught against "+target.display_name, description=body).set_thumbnail(url=ctx.author.avatar).add_field(name="Conclusion", value=win)
        await ctx.send(embed=attack_embed)
    else:
        await ctx.send("Target doesn't exist.")

load_dotenv()

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
