import os
from discord.errors import GatewayNotFound
from dotenv import load_dotenv
from helper import *
from discord.ext.commands import Bot
from youtube_dl import YoutubeDL
from discord.utils import get
from discord import FFmpegPCMAudio
from discord import VoiceClient
import asyncio

load_dotenv()

YDL_OPTIONS = {'noplaylist':'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

bot = Bot(command_prefix=os.getenv('COMMAND_SIGN'))

musicQueue = {}

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.command(name='play', help="Play YouTube audio by providing a link")
async def on_message(ctx):
    await ctx.channel.send(await play(ctx))

@bot.command(name='skip', help="Skip the current Jam")
async def on_message(ctx):
    await ctx.channel.send(await skip(ctx))

@bot.command(name='pause', help="Pause the current Jam")
async def on_message(ctx):
    await ctx.channel.send(await pause(ctx))

@bot.command(name='resume', help="Resume the current Jam")
async def on_message(ctx):
    await ctx.channel.send(await resume(ctx))

@bot.command(name='leave', help="Say by to JamNet")
async def on_message(ctx):
    await ctx.channel.send(await leave(ctx))

@bot.event
async def on_voice_state_update(mem, before, after):

    if before.channel is None and after.channel is not None:
        vc: VoiceClient = after.channel.guild.voice_client
        guildId = vc.guild.id

        wait_time = 15 # s

        afk_count = 0
        afk_max = 2 # => wait_time*afk_max = 7.5 mins right now
        keep_connected = True
        while keep_connected:
            await asyncio.sleep(wait_time)

            if afk_count == afk_max:
                # print("Audio not playing for 10 minutes. Leaving.")
                await vc.disconnect()
                keep_connected = False


            if not vc.is_playing() and len(musicQueue[guildId]) == 0:
                # print("Detected no music playing... leaving in 10 seconds")
                await vc.disconnect()
                keep_connected = False

            elif not vc.is_playing():
                afk_count += 1
            else:
                afk_count = 0

async def resume(ctx):
    voiceStatus = ctx.author.voice
    channel = voiceStatus.channel

    if(voiceStatus):
        voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
        if(is_in_same_voice(channel.id, voice_client.channel.id)):
            voice_client.resume()
            return "Resuming jam!"
        else:
            "You are not even in the same voice call! You're trollig homie, stop it!"
    else:
        return "You are not even listening to music! Stop trolling."

async def pause(ctx):
    voiceStatus = ctx.author.voice
    channel = voiceStatus.channel

    if(voiceStatus):
        voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
        if(is_in_same_voice(channel.id, voice_client.channel.id)):
            voice_client.pause()
            return "Pausing jam!"
        else:
            "You are not even in the same voice call! You're trollig homie, stop it!"
    else:
        return "You are not even listening to music! Stop trolling."


async def leave(ctx):
    voiceStatus = ctx.author.voice
    channel = voiceStatus.channel

    if(voiceStatus):
        voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
        if(is_in_same_voice(channel.id, voice_client.channel.id)):
            await voice_client.disconnect()
            return "Bye bye!"
        else:
            "You are not even in the same voice call! You're trollig homie, stop it!"
    else:
        return "You are not even listening to music! Stop trolling."

async def skip(ctx):
    
    voiceStatus = ctx.author.voice
    channel = voiceStatus.channel
    guildId = ctx.guild.id
    if(voiceStatus):
        voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
        if(voice_client.is_playing()):
            if(is_in_same_voice(channel.id, voice_client.channel.id)):
                voice_client.stop()
                return "Skipping song!"
            else:
                "You are not even in the same voice call! You're trollig homie, stop it!"
        else:
            return "JamNet is not even playing a song dummy!"
    else:
        return "You are not even listening to music! Stop trolling."



async def play(ctx):

    # print(Intents.voice_states)
    guild = ctx.guild
    guildId = guild.id
    member = ctx.author
    memberId = member.id

    voiceStatus = ctx.author.voice

    textMessage = ctx.message.content.split(" ")
    if(len(textMessage) != 2):
         return "Please enter the command properly!"
    
    if(not ("www.youtube.com" in textMessage[1] or "youtu.be" in textMessage[1])):
        return "JamNet can only play YouTube links right now!"


    if voiceStatus:
      channel = voiceStatus.channel
      voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
      if(is_connected(ctx) and voice_client is not None):
        if(not is_in_same_voice(channel.id, voice_client.channel.id)):
            return "Theres only one JamBot to go around and it's already being used!"
      else:
        try:
            await channel.connect()
            voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
            musicQueue[guildId] = []
        except GatewayNotFound:
            print(GatewayNotFound)
            return "Discord's API is down."

    
      musicQueue[guildId].append(textMessage[1])

      if not voice_client.is_playing():
          with YoutubeDL(YDL_OPTIONS) as ydl:
              info = ydl.extract_info(musicQueue[guildId][0], download=False)
          URL = info['formats'][0]['url']
          voice_client.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: play_next(guildId, voice_client, ctx))
          return "Playing your song!"
      else:
        return "Adding your song to the queue!"
    else: 
      return "{0} before using this command join a voice channel!".format(at_user(memberId))

def play_next(id, vc, ctx):
    if(len(musicQueue[id]) >= 1):
        musicQueue[id].pop(0) # Pop the just played song off the queue

    if(len(musicQueue[id]) >= 1):
          with YoutubeDL(YDL_OPTIONS) as ydl:
              info = ydl.extract_info(musicQueue[id].pop(0), download=False)
          URL = info['formats'][0]['url']
          vc.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after= lambda e: play_next(id, vc, ctx))
    else:
        vc.stop() # Dont think I need this... but what ev



def is_connected(ctx):
    voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
    return voice_client and voice_client.is_connected()

def is_in_same_voice(id1, id2):
    return id1 == id2
    


bot.run(os.getenv('BOT_API'))