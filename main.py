import discord
from discord.ext import commands
import gacha
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import util

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='ricky ', intents=intents)

user_handle = gacha.UserHandle()
user_handle.load_users()

COLOURS = {"Common": discord.Colour.light_gray(), "Rare": discord.Colour.blue(), "Epic": discord.Colour.purple(), "Legendary": discord.Colour.gold()}

@bot.command()
async def test(ctx):
    await ctx.send("Test!_")

@bot.command(
    help="Usage: ricky gacha. Performs a wish."
)
async def gacha(ctx):
    user_handle.user_init(ctx.author.id)
    success, item = user_handle.user_gacha(ctx.author.id)

    user_handle.save_users()
    if not success:
        time_left = item - datetime.now()
        await ctx.send(ctx.author.mention + ", you must wait **" + util.timeformat(time_left, " days", " hours", " minutes") + "** to wish again!")
    else:
        image_file = discord.File("img/"+item["id"]+".png", filename=item["id"]+".png")
        wish_embed = discord.Embed(title=ctx.author.display_name+"'s "+item["name"], description="*"+item["description"]+"*", colour=COLOURS[item["rarity"]]).set_footer(text=item["source"]).set_image(url="attachment://"+item["id"]+".png").set_thumbnail(url=ctx.author.avatar).add_field(name="Rarity", value=item["rarity"]).add_field(name="Collection", value=item["collection"])
                                                                                                                                                                                                                                                                                                                                                                   

        await ctx.send(ctx.author.mention + ", wishes left: " + user_handle.wishes(ctx.author.id), file=image_file, embed=wish_embed)

@bot.command(
    help="Usage: ricky progress. Checks collection progress."
)
async def progress(ctx):
    user_handle.user_init(ctx.author.id)

    info = user_handle.collections(ctx.author.id)

    collections_embed = discord.Embed(title=ctx.author.display_name+"'s Collection Progress", description="Here's "+ctx.author.display_name+"'s progress to completing each collection.").set_thumbnail(url=ctx.author.avatar)
    for collection_name in info:
        collections_embed.add_field(name=collection_name, value=str(info[collection_name][0])+"/"+str(info[collection_name][1]))

    await ctx.send(embed=collections_embed)

@bot.command(
    help="Usage: ricky attack <username>. Attacks the specified person."
)
async def attack(ctx, *args):
    args = " ".join(args)
    
    user_handle.user_init(ctx.author.id)

    guild = ctx.guild

    if guild is None:
        await ctx.send("We can't do this here~")
        return
        
    targets = await guild.query_members(args)
    target = None
    if len(targets) > 0:
        target = targets[0]

    if target is not None:
        user_handle.user_init(target.id)

        body, win, loot = user_handle.attack(ctx.author.id, ctx.author.display_name, target.id, target.display_name)
        user_handle.save_users()
        
        attack_embed = discord.Embed(title=ctx.author.display_name+"'s onslaught against "+target.display_name, description=body).set_thumbnail(url=ctx.author.avatar).add_field(name="Conclusion", value=win)
        loot_embed = discord.Embed(title="Loot Received", description="*Nice attack. Here's the loot we received from the enemy:*")

        # Create loot embed and populate with details
        if len(loot) > 0:
            for item in loot:
                loot_embed.add_field(name=item, value=loot[item])
        else:
            loot_embed.description = "No loot gained from this attack."
            
        await ctx.send(embeds=[attack_embed, loot_embed])
    else:
        await ctx.send("Target doesn't exist.")

@bot.command(
    help="Usage: ricky items. Lists items owned and status."
)
async def items(ctx):
    user_handle.user_init(ctx.author.id)

    info = user_handle.itemslist(ctx.author.id)
    user_handle.save_users()
    
    items_embed = discord.Embed(title=ctx.author.display_name+"'s Items", description=info).set_thumbnail(url=ctx.author.avatar).add_field(name="Showing", value="Items Owned")
    await ctx.send(embed=items_embed)
    
load_dotenv()

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
