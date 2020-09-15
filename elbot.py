# elbot.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
import fantasymanager as fm

load_dotenv()  # get .env file
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix='$')  # Bot is like discord.Client
default_league = 'XFL'

# OPEN JSON OF USER DATA
with open('./json/temp.json') as j_file:  # get user data from local json file
    j_dat = json.load(j_file)
    strikes = j_dat["strikes"]  # user strikes as list of dicts
    data = j_dat["data"]


# SAVE TO TEMP.JSON
def save_dat():  # for writing j_dat to local json file
    with open('./json/temp.json', 'w') as outfile:
        json.dump(j_dat, outfile, indent=4)


def get_owners(league_name=default_league):
    league = fm.League(league_name)

    for oid in league.league_dat['teams']:
        owner = bot.get_user(int(oid))
        yield owner, oid


# CALCULATE "STRIKES"
def strike(user_name, category):  # add strike to 'strikes' in temp.json
    culprit = next((item for item in strikes if item["name"] == user_name), None)  # get user vector

    # ADD TO EXISTING CATEGORY
    if culprit is not None:  # if previous offender add one to correct strike category
        culprit[category] += 1
        print('CULPRIT: \n ', culprit)
        j_dat['strikes'] = strikes  # i have no idea how strikes is updated tbh
        save_dat()

    # OR ADD USER TO TEMP.JSON
    else:  # new offender
        culprit = strikes.append({'name': user_name, 'xds': 0, '@everyones': 0})  # makes new entry in j_dat
        culprit[category] += 1
        print('CULPRIT (new): \n ', culprit)
        save_dat()
    return culprit


##########################################################################################################


@bot.event  # readyuup
async def on_ready():
    fm.sq_clean_games()
    await bot.change_presence(activity=discord.Game(name=f'read #documentation in XFL to start'))
    print('- R E A D Y -')


@bot.command()
async def start(ctx, league=default_league):
    league = fm.League(league)
    lock_date = league.start_friday()

    await ctx.send(f'**LEAGUE STARTED**\n`{league.name} LOCKS MIDNIGHT OF {lock_date}`\n`royale: {league.is_royale} | '
                   f'budget: {league.league_dat["budget"]}\nwhitelist: {league.league_dat["whitelisted"]} | '
                   f'commissioner: {league.league_dat["commissioner"]}`')


@bot.command()
async def gto(ctx, league=default_league):
    for owner, oid in get_owners(league):
        await ctx.send(f'{owner} | {oid}')


# DELETE MESSAGES IN A CHANNEL
@bot.command()  # clean channel
async def clean(ctx):  # UOP
    channel = discord.utils.get(ctx.guild.channels, name=ctx.message.channel.name)  # get channel (default UOP)
    delete_count = 0
    async for message in channel.history(limit=100):  # delete elbert's messages for 100 messages
        if message.author.name == 'elbert' or message.content[0] == '$':  # also delete commands ($)
            await message.delete()
            delete_count += 1
    await ctx.message.channel.send(f'deleted {delete_count} messages')

################################################################################################################

# DRAFT ROYALE!
@bot.command()
async def standings(ctx, leauge_name=default_league):
    await ctx.send('***STANDINGS***')
    league = fm.League(leauge_name)

    for player, pts in league.ordered_players:
        if league.whitelisted(player):
            await ctx.send(f'{player}: {round(pts)}')


@bot.command()
async def profile(ctx, ign, leauge_name=default_league):
    league = fm.League(leauge_name)

    await ctx.send(f'**{ign}**\n-------------')
    for p in league.player_dat[ign]:
        await ctx.send(f'{p}: {league.player_dat[ign][p]}')


@bot.command()
async def history(ctx, ign):
    player = fm.Player(ign)
    await ctx.send('*GETTING GAMES...*')
    stats, gavg, role = player.weekly_soloq_stats()
    await ctx.send(f'\n***AVERAGE: {round(gavg, 2)} | ROLE: {role}***')  # this is legit so fucking bugged
    t = 0

    for stat in stats:
        t += stat
        s = stats[stat]
        await ctx.send(
            f'-----\n**{s["score"]} POINTS**\n *{s["duration"]}*   **{s["kda"]}** on {s["champ"]}\n {s["csm"]} *cs/m*'
            f'     {round(s["kp"]*100, 2)} *%kp*     {s["vision"]} *vision*')


@bot.command()
async def avg(ctx, ign):
    player = fm.Player(ign)
    await ctx.send("*GETTING GAMES...*")
    stats = player.avg_stats

    await ctx.send(f'**games:** {stats["games"]}  |  **role:** {stats["role"]}\n'
                   f'**ppg:** {round(stats["ppg"], 2)}   |  **kda:** {stats["kda"]} ({round(stats["kdad"], 2)})\n'
                   f'csm: {round(stats["csm"], 2)}  |  vision:{round(stats["vision"], 1)}\n*totals: {stats["totals"]}*')


@bot.command()
async def top2(ctx, ign, n_games=2):
    player = fm.Player(ign)
    await ctx.send('*GETTING GAMES...*')
    resp = player.get_top_games(n_games)
    pasta = ''

    if resp == 404:
        await ctx.send('NO GAMES FOUND!')
        g_sum, g_avg, stats = 0, 0, 0
    else:
        g_sum, g_avg, stats = resp

    for stat in stats:
        s = stat
        rkp = round(s["kp"]*100, 2)
        pasta += f'-----\n**{s["score"]} POINTS**\n *{s["duration"]}*   **{s["kda"]}** on {s["champ"]}\n {rkp} *%kp*   '
        pasta += f'{s["csm"]} *cs/m*   {s["vision"]} *vision* *{s["role"].lower()}*\n'

    await ctx.send(pasta)
    await ctx.send(f'**POINTS: {round(g_sum, 1)}**')


@bot.command()  # only works in the XFL
async def drafted(ctx):
    league = fm.League(default_league)
    n_drafts = {}

    for team in league.league_dat["teams"]:
        for player in league.league_dat["teams"][team]["players"]:
            if player in n_drafts:
                n_drafts[player] += 1
            else:
                n_drafts[player] = 1

    n_drafts = sorted(n_drafts.items(), key=lambda x: x[1], reverse=True)

    pasta = ''
    for player, pts in n_drafts:
        pasta = pasta + f'\n**{player}**: `{pts}`'
    await ctx.send(pasta)


#####################################################################################################################


@bot.command()
async def register(ctx, league_name=default_league):
    team = ctx.author.id
    name = ctx.author.name
    league = fm.League(league_name)
    if str(team) not in league.league_dat['teams']:
        league.add_rteam(team, name)
        await ctx.send('TEAM ADDED')


@bot.command()
async def whitelist(ctx, ign, league_name=default_league):
    league = fm.League(league_name)
    league.whitelist(ign)
    await ctx.send(f'whitelisted {ign}')


@bot.command()
async def delist(ctx, ign, league_name=default_league):
    league = fm.League(league_name)
    league.delist(ign)
    await ctx.send(f'de-listed {ign}')


@bot.command()
async def draft(ctx, ign, league_name=default_league):
    team = str(ctx.author.id)
    league = fm.League(league_name)

    if ign not in league.league_dat['teams'][team]['players']:
        resp = league.add_player_to_team(ign.lower(), team)
        await ctx.send(f'*team:* {league.league_dat["teams"][team]["players"]}')
        await ctx.send(f'*points left:* {league.league_dat["teams"][team]["budget"]}')

        if isinstance(resp, str):
            await ctx.send(f'`ERROR {resp}`')


@bot.command()
async def drop(ctx, ign, league_name=default_league):
    team = str(ctx.author.id)
    league = fm.League(league_name)

    if ign in league.league_dat['teams'][team]['players']:
        resp = league.remove_player_from_team(ign, team)
        await ctx.send(f'*team:* {league.league_dat["teams"][team]["players"]}')
        if isinstance(resp, int):
            await ctx.send(f'`ERROR {resp}`: TEAMS LOCKED IN')
        await ctx.send(f'*points left:* {league.league_dat["teams"][team]["budget"]}')


@bot.command()
async def teamscore(ctx, league_name=default_league, team=None):
    if not team:
        team = str(ctx.author.id)
    else:
        team = team

    league = fm.League(league_name)
    team_owner = league.league_dat["teams"][team]["owner"]
    pts, savg, gl = league.get_rteam_ppw(team)

    await ctx.send(f'***TEAM {team_owner}***:\n**{round(pts)} POINTS ({round(savg, 2)} SAVG)**')
    await ctx.send(f'-----------------------\n*__games:__*')
    for player in gl:
        await ctx.send(f'***{player}***')
        for game in gl[player]:
            s = game
            if 'score' in game:
                await ctx.send(
                    f'__{s["score"]} POINTS__  |   *{s["duration"]}*   {s["kda"]} on {s["champ"]}\n {s["csm"]} '
                    f'*cs/m*   {s["vision"]} *vision*   {round(s["kp"]*100, 2)} *%kp*   *{s["role"].lower()}*')
            elif 'avg' in game:
                await ctx.send(f'**POINTS: {game["pts"]}  |   AVERAGE {game["avg"]}**\n----------------------')
            else:
                await ctx.send('NO WEEKLY GAMES!')


@bot.command()
async def dm_all_owners(l_n=default_league):
    league = fm.League(l_n)
    for t in league.league_dat['teams']:
        user = bot.get_user(int(t))
        await user.send(f'`HELLO {user.name}, DO NOT BE AFRAID`\nthis is simply a test post for **silver fantasy**.'
                        f' points will be calculated tomorrow morning, and teams will unlock then. you will have the'
                        f' weekend to draft your team but teams lock __sunday night__ so draft your team before then.')


@bot.command()
async def leaguescore(ctx, league=default_league):
    league = fm.League(league)
    await ctx.send(f'__SCORING ALL TEAMS IN `{league.name}`__\n*this might take a minute...*')

    teams = league.score_all_teams()
    for tid, score in teams:
        user = bot.get_user(int(tid))
        await ctx.send(f'{user.name}: {score}')


@bot.command()
async def localrank(ctx, league_name=default_league):
    league = fm.League(league_name)
    ranks = []

    for team_n in league.league_dat["teams"]:
        team = league.league_dat["teams"][team_n]
        ranks.append((team_n, team["points"], [x for x in team["players"]]))

    ranks = sorted(ranks, key=lambda x: x[1], reverse=True)
    for n, pts, players in ranks:
        user = bot.get_user(int(n))
        await ctx.send(f'__**TEAM {user.name}**__:  `{pts}` __**POINTS**__\nROSTER: {players}')

#####################################################################################################################

# COUNT XDs, @ALLs
@bot.event  # on message!!!
async def on_message(message):

    content = message.content
    channel = message.channel  # bot_testing

    # STRIKE FOR @EVERYONE
    if message.mention_everyone:  # everyone counter
        await channel.send(f'{message.author.name} you dumb fuck')
        strike(message.author.name, '@everyones')
        return

    # STRIKE FOR XDs
    if 'xd' in content.lower() and message.author.name != 'elbert':  # xd counter
        xder = strike(message.author.name, 'xds')
        await channel.send(f'* xd counter: {xder["xds"]}')
        return

    await bot.process_commands(message)  # so that other on-message funcs will work


# STATE CHANGES
@bot.event  # announce streaming and afk
async def on_voice_state_update(user, before, after):

    # STREAMING
    stream_channel = bot.get_channel(710226878207754271)  # xanation #general
    if after.self_stream and not before.self_stream:  # if streaming now but not before
        await stream_channel.send(f'-----\n**{user}** is now streaming in **# {after.channel}**\n-----')

    # AFK
    if after.afk and not before.afk:
        await stream_channel.send(f'*{user} is taking an ed nap*')


# BAD COMMAND
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')


def run():
    bot.run(TOKEN)


if __name__ == "__main__":
    run()
