import discord
from discord.ext import commands
import gacha
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import util
import concurrent.futures
import time
import json
import asyncio
import random

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='ricky ', intents=intents)

user_handle = gacha.UserHandle()
user_handle.load_users()

main_threadpool = concurrent.futures.ThreadPoolExecutor()
song_handle = gacha.SongHandle()
song_processes = []
guilds_song_info = {}

async_loop = util.AsyncHelp()

#song_handle.info_test("https://soundcloud.com/meoxa/tsukinami-meoxa-x-katabatic-bootleg")
COLOURS = {"Common": discord.Colour.light_gray(), "Rare": discord.Colour.blue(), "Epic": discord.Colour.purple(), "Legendary": discord.Colour.gold()}

#async def song_add_give_feedback():
#    while True:
#        time.sleep(1)
#
#        for _ in concurrent.futures.as_completed(song_processes):
#            song_add_feedback = _.result()
#            print(song_add_feedback)
#            try:
#                song_embed = discord.Embed(title="Processing Complete", description="Hey **"+song_add_feedback['ctx'].author.display_name+"**, "+str(song_add_feedback['count'])+" of your songs have been processed successfully and added to your playlist.")
#                song_processes.remove(_)
#                await song_add_feedback['ctx'].send(song_add_feedback['ctx'].author.mention, embed=song_embed)

#            except Exception as e:
#                print(e.__context__, e.__cause__, e)


def song_end(e):
    asyncio.run(check_and_play_song())

async def play_next_song(voice_client, guild_id):
    if len(guilds_song_info[guild_id]["songs"]) > 0:
        to_play_name = guilds_song_info[guild_id]["songs"].pop(0)

        if os.path.exists(os.path.join(os.getcwd(), "song", to_play_name+".m4a")):
            source = await discord.FFmpegOpusAudio.from_probe(os.path.join(os.getcwd(), "song", to_play_name+".m4a"))
            guilds_song_info[guild_id]["current_song"] = to_play_name
            voice_client.play(source, after=song_end)
    else:
        await voice_client.disconnect()

async def check_and_play_song():
    for guild_id in guilds_song_info:
        voice_client = guilds_song_info[guild_id]["vc"]
        if voice_client is not None and voice_client.is_connected() and not voice_client.is_playing():
            await play_next_song(voice_client, guild_id)

async def user_init_and_notify(ctx, user_id):
    compensated = user_handle.user_init(user_id)

    if compensated > 0:
        compensation_embed = discord.Embed(title="Wish Compensation", description=ctx.author.display_name+", because some of your cards have disappeared from existence, you have been awarded **"+str(compensated)+"** wishes for compensation. Good luck on your pulls.")
        await ctx.send(embed=compensation_embed)

    
###
# BOT COMMANDS
###

@bot.command()
async def test(ctx):
    await ctx.send("Test!_")

@bot.command(
    help="Usage: ricky skip. Skips the current playing song."
)
async def skip(ctx):
    guild = ctx.guild

    if guild is None:
        await ctx.send("We can't do this here~")
        return

    if guild.id not in guilds_song_info:
        await ctx.send("No songs are playing.")
        return

    voice_client = guilds_song_info[guild.id]["vc"]
    if voice_client is not None and voice_client.is_connected():
        voice_client.stop()
    
@bot.command(
    help="Usage: ricky shuffle. Shuffles the queue."
)
async def shuffle(ctx):
    guild = ctx.guild

    if guild is None:
        await ctx.send("We can't do this here~")
        return

    if guild.id not in guilds_song_info:
        await ctx.send("No songs are playing.")
        return

    random.shuffle(guilds_song_info[guild.id]["songs"])
    await ctx.send("Shuffled queue.")
    
@bot.command(
    help="Usage: ricky np. Checks what song is currently playing."
)
async def np(ctx):
    guild = ctx.guild

    if guild is None:
        await ctx.send("We can't do this here~")
        return

    if guild.id not in guilds_song_info:
        await ctx.send("No song is playing.")
        return

    song = guilds_song_info[guild.id]["current_song"]

    if song is None:
        await ctx.send("There's no song playing.")
        return
        
    song_info = song_handle.song_info[song]

    now_playing_embed = discord.Embed(title=song_info['title'], description="Is the song that is now playing, and its length is **"+song_info['duration']+"**. I don't know how much of it is left.")
    await ctx.send(embed=now_playing_embed)
    
@bot.command(
    help="Usage: ricky add <url>. Adds the specified song to your personal playlist."
)
async def add(ctx, url):
    add_embed = discord.Embed(title="URL Submitted", description=ctx.author.display_name+", we are now processing your submitted URL. We will **NOT** let you know when your song(s) are ready.")
    await ctx.send(ctx.author.mention, embed=add_embed)

    song_processes.append(main_threadpool.submit(song_handle.download, ctx, url))

@bot.command(
    help="Usage: ricky play. Adds your custom playlist (created using ricky add) to the queue and plays it in vc."
)
async def play(ctx):
    guild = ctx.guild

    if guild is None:
        await ctx.send("We can't do this here~...")
        return

    #print(guild, guild.id)
    #return
    clean_join = False
    voice_client = None
    if guild.id in guilds_song_info:
        voice_client = guilds_song_info[guild.id]["vc"]
    else:
        guilds_song_info[guild.id] = {"vc": None, "songs": [], "current_song": None}

    if voice_client is None or not voice_client.is_connected():
        clean_join = True
        if ctx.author.voice is not None:
            voice_channel = ctx.author.voice.channel
            voice_client = await voice_channel.connect(self_deaf=True)
            await ctx.send(ctx.author.mention + ", now joined call.")
        else:
            await ctx.send(ctx.author.mention + ", you are not in a voice channel.")
            return

    #print("Voice Client Status", guild, voice_client, voice_client.is_paused(), voice_client.is_playing())
    guilds_song_info[guild.id]["vc"] = voice_client

    new_songs = []
    try:
        with open(os.path.join(os.getcwd(), "playlist", str(ctx.author.id)+".json"), 'r') as playlist:
            new_songs = json.loads(playlist.read())["songs"]
    except Exception as e:
        await ctx.send(ctx.author.display_name+"'s playlist was empty, so there were no songs to add."+str(e))

    # More slow code
    for song in new_songs:
        if song not in guilds_song_info[guild.id]["songs"]:
            guilds_song_info[guild.id]["songs"].append(song)
    #print(guilds_song_info[guild.id])
    await check_and_play_song()       

@bot.command(
    help="Usage: ricky gacha. Performs a wish."
)
async def gacha(ctx, *args):
    args = " ".join(args)
    if "legendary" in args:
        legendary_embed = discord.Embed(title="Inventory Successfully Cleared", description=ctx.author.display_name+", your command **ricky gacha "+args+"** has successfully been processed, and your inventory has been wiped. We hope you had fun playing with ricky gacha, and we wish to see you soon.")
        await ctx.send(ctx.author.mention, embed=legendary_embed)
        return

    
    await user_init_and_notify(ctx, ctx.author.id)
    success, item, collection_name, wish_compensated = user_handle.user_gacha(ctx.author.id)
    user_handle.save_by_id(ctx.author.id)
        
    if not success:
        time_left = item - datetime.now()
        await ctx.send(ctx.author.mention + ", you must wait **" + util.timeformat(time_left, " days", " hours", " minutes") + "** to wish again!")
    else:
        image_file = discord.File("img/"+item["id"]+".png", filename=item["id"]+".png")
        wish_embed = discord.Embed(title=ctx.author.display_name+"'s "+item["name"]+"("+item["rarity"]+")", description="*"+item["description"]+"*", colour=COLOURS[item["rarity"]]).set_footer(text=item["source"]).set_image(url="attachment://"+item["id"]+".png").set_thumbnail(url=ctx.author.avatar).add_field(name="Rarity", value=item["rarity"]).add_field(name="Collection", value=collection_name)

        if wish_compensated:
            await ctx.send(ctx.author.mention + ", (You received 0.5 wishes as compensation when acquiring a duplicate.) wishes left: " + str(user_handle.wishes(ctx.author.id)), file=image_file, embed=wish_embed)
        else:
            await ctx.send(ctx.author.mention + ", wishes left: " + str(user_handle.wishes(ctx.author.id)), file=image_file, embed=wish_embed)

@bot.command(
    help="Usage: ricky progress. Checks collection progress."
)
async def progress(ctx):
    await user_init_and_notify(ctx, ctx.author.id)

    info = user_handle.collections(ctx.author.id)

    collections_embed = discord.Embed(title=ctx.author.display_name+"'s Collection Progress", description="Here's "+ctx.author.display_name+"'s progress to completing each collection.").set_thumbnail(url=ctx.author.avatar)
    for collection_name in info:
        collections_embed.add_field(name=collection_name, value=str(info[collection_name][0])+"/"+str(info[collection_name][1]))

    await ctx.send(embed=collections_embed)

@bot.command(
    help="Usage: ricky ability <character name>. Activates the ability of the given item."
)
async def ability(ctx, *args):
    args = " ".join(args)

    await user_init_and_notify(ctx, ctx.author.id)
    ability_info, ability_success = user_handle.ability(ctx.author.id, args)
    user_handle.save_by_id(ctx.author.id)

    ability_embed = discord.Embed(title="Ability Used", description=ctx.author.display_name + ", " + ability_info).set_thumbnail(url=ctx.author.avatar).add_field(name="Success", value=ability_success)
    
    await ctx.send(embed=ability_embed)
    
@bot.command(
    help="Usage: ricky attack <username>. Attacks the specified person."
)
async def attack(ctx, *args):
    args = " ".join(args)

    await user_init_and_notify(ctx, ctx.author.id)
        
    guild = ctx.guild

    if guild is None:
        await ctx.send("We can't do this here~")
        return
        
    targets = await guild.query_members(args)
    target = None
    if len(targets) > 0:
        target = targets[0]

    if target is not None:
        await user_init_and_notify(ctx, target.id)

        if target.id == ctx.author.id:
            await ctx.send("Can't target yourself with an attack.")
            return

        body, win, loot = user_handle.attack(ctx.author.id, ctx.author.display_name, target.id, target.display_name)
        user_handle.save_by_id(ctx.author.id)
        user_handle.save_by_id(target.id)
        
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
    await user_init_and_notify(ctx, ctx.author.id)
    info = user_handle.itemslist(ctx.author.id)
    stability = user_handle.calculate_stability(ctx.author.id)
    user_handle.save_by_id(ctx.author.id)
    
    items_embed = discord.Embed(title=ctx.author.display_name+"'s Items", description=info).set_thumbnail(url=ctx.author.avatar).add_field(name="Showing", value="Items Owned").add_field(name="Team Stability", value=str(stability*100)+"%")
    await ctx.send(embed=items_embed)

@bot.command(
    help="Usage: ricky show <itemname>. Shows the item."
)
async def show(ctx, *args):
    args = " ".join(args)
    
    await user_init_and_notify(ctx, ctx.author.id)
    selected_item = user_handle.select(ctx.author.id, args)
    user_handle.save_by_id(ctx.author.id)

    if selected_item == None:
        await ctx.send("Can't show the item: it doesn't exist or you don't own it.")
        return

    #print(selected_item)

    image_file = discord.File("img/"+selected_item["id"]+".png", filename=selected_item["id"]+".png")
    #print("img/"+selected_item["id"]+".png", selected_item["id"]+".png", "attachement://"+selected_item["id"]+".png")
    selection_embed = discord.Embed(title=ctx.author.display_name+"'s Item", description="**"+selected_item["name"]+"** is now being displayed.\n\n*"+selected_item["description"]+"*\n\n"+"Ability: **"+selected_item["ability"]+"**").set_thumbnail(url=ctx.author.avatar).set_image(url="attachment://"+selected_item["id"]+".png")
    await ctx.send(embed=selection_embed, file=image_file)

@bot.command(
    help="Usage: ricky claim. Creates a new land claim (and shows an existing one)"
)
async def claim(ctx):
    await user_init_and_notify(ctx, ctx.author.id)
    claim_info = user_handle.create_land_claim(ctx.author.id)
    user_handle.save_by_id(ctx.author.id)

    claim_embed = discord.Embed(title=ctx.author.display_name+"'s Land Claim", description=claim_info)
    await ctx.send(embed=claim_embed)

load_dotenv()

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
