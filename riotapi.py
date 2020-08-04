import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
RIOT_TOKEN = os.getenv('RIOT_TOKEN')  # app API key
headers = {"X-Riot-Token": RIOT_TOKEN}
ex_name = 'black xan bible'  # example name for development
champ_dat = requests.get('http://ddragon.leagueoflegends.com/cdn/10.10.3208608/data/en_US/champion.json').json()['data']
rank_mmrs = {'IRON IV': 0, 'IRON III': 250, 'IRON II': 500, 'IRON I': 750, 'BRONZE IV': 1000, 'BRONZE III': 1250,
             'BRONZE II': 1500, 'BRONZE I': 1750, 'SILVER IV': 2000, 'SILVER III': 2250, 'SILVER II': 2500,
             'SILVER I': 2750, 'GOLD IV': 3000, 'GOLD III': 3250, 'GOLD II': 3500, 'GOLD I': 3750}


# use datadragon to get champ names by id (numerical key)
def get_champ(champ_id):
    for champ in champ_dat:
        cid = int(champ_dat[champ]['key'])
        if cid == champ_id:
            return champ


# function to get a summoner ID from an IGN
def get_sum_id(summoner_name):
    name_endpoint = f'https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}'
    sumr_id = requests.get(name_endpoint, headers=headers).json()['id']
    return sumr_id


# RETURN GAME INFO
# FIRST request game info(summoners, champions) and gets summoner ID
# SECOND get soloq data for summoner and calculate wrs, rank, mmr
# FINALLY return it all as a string
def get_game(sumr):
    sum_id = get_sum_id(sumr)
    spec_endpoint = f'https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/{sum_id}'
    code = requests.get(spec_endpoint, headers=headers).status_code
    if code == 200:  # good code xD
        participants = requests.get(spec_endpoint, headers=headers).json()['participants']
        matchups = {100: {}, 200: {}}
        sum_mmrs = []
        wrs = []
        t1_mmr = None
        t2_mmr = None

        # get the ranks etc. for the match participants
        for participant in participants:
            par_id = participant['summonerId']
            sum_dat_endpoint = f'https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/{par_id}'
            sum_dat = requests.get(sum_dat_endpoint, headers=headers).json()

            # get soloq data
            if sum_dat[0]['queueType'] == 'RANKED_SOLO_5x5':
                soloq = sum_dat[0]
            elif sum_dat[1]['queueType'] == 'RANKED_SOLO_5x5':
                soloq = sum_dat[1]

            # calculate num games, wr, make in to string and get champ name
            t_games = soloq['wins'] + soloq['losses']
            wr = round((soloq['wins']/t_games) * 100)
            print(participant)
            print(soloq)
            champ = get_champ(participant['championId'])
            mstr = f'{t_games} game {wr}% ' + soloq['tier'] + ' ' + soloq['rank'] + ' ' + '*'+champ+'*'
            matchups[participant['teamId']][participant['summonerName']] = (mstr)

            # calculate MMR
            if len(sum_mmrs) < 5 and t1_mmr is None:
                wrs.append(wr)
                sum_mmrs.append(rank_mmrs[soloq['tier'] + ' ' + soloq['rank']] + soloq['leaguePoints'])
            elif len(sum_mmrs) == 5 and t1_mmr is None:
                t1_avg_mmr = sum(sum_mmrs)/5
                t1_avg_wr = sum(wrs)/5
                wrs = []
                sum_mmrs = []

            if len(sum_mmrs) < 5 and t2_mmr is None:
                wrs.append(wr)
                sum_mmrs.append(rank_mmrs[soloq['tier'] + ' ' + soloq['rank']])
            elif len(sum_mmrs) == 5 and t2_mmr is None:
                t2_avg_mmr = sum(sum_mmrs)/5
                t2_avg_wr = sum(wrs)/5

        matchups['mmrs'] = f'**BLU**: MMR: {t2_avg_mmr}, WR: {t2_avg_wr}\n**RED**: MMR: {t1_avg_mmr}, WR: {t1_avg_wr}'
        matchups['playerList'] = list(matchups[100].keys()) + list(matchups[200].keys())
        return matchups

    else:  # bad code >:(
        print(f"ERROR: {code}\nSUMMONER NOT IN GAME")
        return code


# mups = get_game(ex_name)
# print(mups)
# print(mups['mmrs'])
