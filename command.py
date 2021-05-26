import discord
import pandas as pd
import dataframe_image as dfi
from discord.ext import commands
import pymongo
import os
import asyncio


intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)

os.chdir(r"C:\Users\roman\TriviaBot Dev Version")

client.remove_command('help')
client.database_client = pymongo.MongoClient("")
client.user_collection = client.db['users']


@client.command()
async def help(ctx):
    embed = discord.Embed(
        title="Trivia Bot Commands",
        description="List of all bot commands",
        color=discord.Colour.blue(),
        author="Roman Princ",
    )
    embed.add_field(name="!help", value="Lists all bot commands", inline=False)
    embed.add_field(name="!trivia [correct option A =1, B = 2, etc] [image url]", value="Starts a trivia question", inline=False)
    embed.add_field(name="!congrats", value="Closes the question, and awards points", inline=False)
    embed.add_field(name="!leaderboard", value="Shows the current leaderboard", inline=False)

    await ctx.send(embed=embed)

client.triviaMessage = 0
client.triviaAnswer = 0


@client.command()
@commands.has_role(845449055906824213)
async def trivia(ctx, correct_answer, url):

    if client.triviaMessage != 0:
        await ctx.send('There is already a trivia message running, end it before starting a new one!')
        return

    channel = client.get_channel(844048934157418516)

    embed = discord.Embed(
        title="Trivia Question",
        description="Get it right for a point!",
        color=discord.Colour.blue(),

    )
    embed.set_image(url=str(url))
    triviaMessage = await channel.send(embed=embed)
    client.triviaMessage = triviaMessage.id
    await triviaMessage.add_reaction('\U0001F1E6')
    await triviaMessage.add_reaction('\U0001F1E7')
    await triviaMessage.add_reaction('\U0001F1E8')
    await triviaMessage.add_reaction('\U0001F1E9')

    client.triviaAnswer = correct_answer

    await ctx.message.delete()


@trivia.error
async def _error(ctx, error):
    if isinstance(error, commands.CommandError):
        await ctx.send('Failed to run command: !trivia [correct option A =1, B = 2, etc] [image url]')


@trivia.error
async def clear_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command")
    elif isinstance(error, commands.CommandError):
        await ctx.send('Failed to run command: !trivia [correct option A =1, B = 2, etc] [image url]')


@client.event
async def on_raw_reaction_add(payload):
    msg = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    payload_message_id = payload.message_id
    target_message_id = client.triviaMessage

    if payload_message_id == target_message_id:
        if msg.author.id != payload.user_id:
            user = client.get_user(payload.user_id)
            await msg.remove_reaction(payload.emoji, user)

            if payload.emoji.name == "🇦":
                answer = 1
            elif payload.emoji.name == '🇧':
                answer = 2
            elif payload.emoji.name == '🇨':
                answer = 3
            elif payload.emoji.name == '🇩':
                answer = 4
            else:
                return

            await add_user(user)
            await update_answer(user, answer)


async def add_user(user):
    if client.user_collection.count_documents({"_id":str(user.id)}, limit=1) != 0:
        print('hey this worked')
        return
    print('new users only print this')
    user_dict = {"_id": str(user.id), 'answer': 0, 'number_correct': 0, 'display_name': user.display_name}
    x = client.user_collection.insert_one(user_dict)


async def update_answer(user, answer):
    client.user_collection.update_one({"_id": str(user.id)}, {"$set": {'answer': answer}})


@client.command()
@commands.has_role(845449055906824213)
async def congrats(ctx):

    await ctx.send('Ending the current trivia question!')

    client.triviaMessage = 0

    embed = discord.Embed(
        title="These users answered correctly!",
        color=discord.Colour.blue(),
    )

    name_list = []

    await give_points(name_list)

    dataframe_columns = {'Name': name_list}

    dataframe = pd.DataFrame(dataframe_columns)
    dataframe = dataframe.style.set_properties(**{'text-align': 'left'})
    dataframe = dataframe.hide_index()

    dfi.export(dataframe, 'correct_players.png')
    file = discord.File("correct_players.png")

    embed.set_image(url='attachment://correct_players.png')

    await ctx.send(file=file, embed=embed)


@congrats.error
async def clear_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command")


async def give_points(name_list):
    users = client.user_collection.find()
    for user in users:
        id, answer, points, name = user['_id'], user['answer'], user['number_correct'], user['display_name']
        if str(answer) == str(client.triviaAnswer):
            client.user_collection.update_one({"_id": str(id)}, {"$set": {'number_correct': points + 1}})
            name_list.append(name)
        client.user_collection.update_one({"_id": str(id)}, {"$set": {'answer': 0}})


@client.command()
async def leaderboard(ctx):

    userNames = []
    userScores = []

    users = client.user_collection.find()

    for user in users:
        points, name = user['number_correct'], user['display_name']
        userNames.append(name)
        userScores.append(points)

    embed = discord.Embed(
        title="Trivia Leaderboard",
        color=discord.Colour.blue(),
    )

    zipped_lists = zip(userScores, userNames)
    sorted_pairs = sorted(zipped_lists)

    tuples = zip(*sorted_pairs)
    userScores, userNames = [list(tuple) for tuple in tuples]

    userScores.reverse()
    userNames.reverse()
    ranks = []
    for rank in range(len(userScores)):

        ranks.append(rank + 1)

    dataframe_columns = {'Rank': ranks, 'Name': userNames, 'Points': userScores}

    dataframe = pd.DataFrame(dataframe_columns)
    dataframe = dataframe.head(10)
    dataframe = dataframe.style.set_properties(**{'text-align': 'left'})
    dataframe = dataframe.hide_index()

    dfi.export(dataframe, 'leaderboard.png')
    file = discord.File("leaderboard.png")
    embed.set_image(url='attachment://leaderboard.png')

    await ctx.send(file=file, embed=embed)


client.run('')
