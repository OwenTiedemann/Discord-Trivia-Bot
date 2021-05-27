import discord
import pandas as pd
import dataframe_image as dfi
from discord.ext import commands
import pymongo
import os
import random


intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)

os.chdir(r"C:\Users\roman\TriviaBot Dev Version")

client.remove_command('help')
client.database_client = pymongo.MongoClient(client.mongo_url)
client.db = client.database_client['database']
client.user_collection = client.db['default']
client.trivia_collection = client.db['trivia_questions']
client.server_info_collection = client.db['server_info']

@client.event
async def on_guild_join(guild):
    print('worked')
    server_dict = {"_id": 1, 'current_season': 'default', 'message_id': 0}
    client.server_info_collection.insert_one(server_dict)
    print('did this')


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
    embed.add_field(name="!randomtrivia", value="Starts a randomly selected trivia question from the database", inline=False)
    embed.add_field(name="!congrats", value="Closes the question, and awards points", inline=False)
    embed.add_field(name="!leaderboard", value="Shows the current leaderboard", inline=False)
    embed.add_field(name="!seasonleaderboard [season_name]", value="Shows the selected seasons leaderboard", inline=False)
    embed.add_field(name="!startseason [season_name]", value="Starts a new season with selected name", inline=False)

    await ctx.send(embed=embed)

client.triviaMessage = 0
client.triviaAnswer = 0


@client.command()
@commands.has_role(845449055906824213)
async def trivia(ctx, correct_answer, url):
    print('entered function')
    trivia_dict = {"_id": client.trivia_collection.estimated_document_count() + 1, 'answer': correct_answer, 'url': url, 'used_this_season': True}
    client.trivia_collection.insert_one(trivia_dict)
    print('added to db')

    await trivia_setup(ctx, correct_answer, url)


@client.command()
@commands.has_role(845449055906824213)
async def randomtrivia(ctx):
    print('WTF')
    trivia_questions_list = list(client.trivia_collection.find({"used_this_season": False}))
    print('wTF')
    trivia_count = len(trivia_questions_list)
    print('wtF')
    if trivia_count != 0:
        question_id = random.randint(0, trivia_count - 1)
    print('wtf1')
    i = 0
    print('wtf')
    for question in trivia_questions_list:
        if i == question_id:
            correct_answer, url = question['answer'], question['url']
            client.trivia_collection.update_one({"_id": question['_id']}, {"$set": {'used_this_season': True}})
            await trivia_setup(ctx, correct_answer, url)
            return
        i += 1

    print('wtf')

    await ctx.send('No random trivia questions available at the moment!')


@randomtrivia.error
async def randomtrivia_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command")


async def trivia_setup(ctx, correct_answer, url):
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
    client.server_info_collection.update_one({"_id": 1}, {"$set": {'message_id': triviaMessage.id}})
    await triviaMessage.add_reaction('\U0001F1E6')
    await triviaMessage.add_reaction('\U0001F1E7')
    await triviaMessage.add_reaction('\U0001F1E8')
    await triviaMessage.add_reaction('\U0001F1E9')

    client.triviaAnswer = correct_answer

    await ctx.message.delete()


@trivia.error
async def trivia_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command")
    elif isinstance(error, commands.BadArgument):
        await ctx.send('Failed to run command: !trivia [correct option A =1, B = 2, etc] [image url]')


@client.event
async def on_raw_reaction_add(payload):
    msg = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    payload_message_id = payload.message_id
    question = client.server_info_collection.find_one()
    target_message_id = question['message_id']

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
    if client.user_collection.count_documents({"_id": str(user.id)}, limit=1) != 0:
        return
    user_dict = {"_id": str(user.id), 'answer': 0, 'number_correct': 0, 'display_name': user.display_name}
    client.user_collection.insert_one(user_dict)


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
async def congrats_error(ctx, error):
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
@commands.has_role(845449055906824213)
async def startseason(ctx, season):
    client.server_info_collection.find_one()
    client.server_info_collection.update_one({"_id": 1}, {"$set": {'current_season': str(season)}})
    client.user_collection = client.db[season]
    await reset_trivia_database()


@startseason.error
async def congrats_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command")


async def reset_trivia_database():
    trivia_questions = client.trivia_collection.find()

    for question in trivia_questions:
        client.trivia_collection.update_one({"_id": question['_id']}, {"$set": {'used_this_season': False}})


@client.command()
async def leaderboard(ctx):
    x = client.server_info_collection.find_one()
    current_season = x['current_season']
    await leaderboard_setup(ctx, current_season)


@client.command()
async def seasonleaderboard(ctx, season):
    await leaderboard_setup(ctx, season)


async def leaderboard_setup(ctx, season):

    season_user_collection = client.db[str(season)]

    if season_user_collection.estimated_document_count() == 0:
        await ctx.send('The leaderboard is empty, complete a trivia question in the season first!')

    userNames = []
    userScores = []

    users = season_user_collection.find()

    for user in users:
        points, name = user['number_correct'], user['display_name']
        userNames.append(name)
        userScores.append(points)

    embed = discord.Embed(
        title=str(season) + " Trivia Leaderboard",
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


client.run(client.api_key)
