import requests
import os
from dotenv import load_dotenv
import datetime
import time

# RIOTAPI.PY REWRITE.
# RIOT API HANDLER 2

"""STATIC FUNCS:
- get_riot_token returns the readers for reaching riot api
- get_champ loads the datadragon page and searches for a champ id, returns champ name

CLASSES:
- SUMMONER:
    takes in summoner id
    gets ranked data immediately
    can look up match history and open a specific match
    
- MATCH
    takes in match id
    fetches the game json
    
- ActiveGame
    takes in summoner
"""


def get_riot_token():
    load_dotenv()
    r_toke = os.getenv('RIOT_TOKEN')  # app API key
    headers = {"X-Riot-Token": r_toke}
    print('T0KEN L0ADED\n')

    return headers


HEADERZ = get_riot_token()


def get_champ(champ_id):
    champ_dat = requests.get('http://ddragon.leagueoflegends.com/cdn/10.10.3208608/data/en_US/champion.json').json()[
        'data']
    for champ in champ_dat:
        cid = int(champ_dat[champ]['key'])
        if cid == champ_id:
            return champ


def except429(func):
    def except_wrapper(*args, **kwargs):
        funcy = func(*args, **kwargs)
        if type(funcy) is not int:
            return funcy
        else:
            print(f'CODE {funcy}')
            print('trying again in 100 seconds...')
            time.sleep(100)
            return func(*args, **kwargs)

    return except_wrapper


class Summoner:

    def __init__(self, ign):
        self.ign = ign
        self.headers = HEADERZ
        self.soloq = None
        self.flex = None
        self.rank = None
        self.lp = 0
        self.games = 0
        self.wr = 0
        self.ids = self.get_sum_id()

        if type(self.ids) is list:
            self.get_ranked()

    # GET IDs FROM SUMMONER NAME, [0] is SUM ID [1] is ACCT ID [2] is PUUID
    @except429
    def get_sum_id(self):
        name_endpoint = f'https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{self.ign}'
        id_ip = requests.get(name_endpoint, headers=self.headers)
        if id_ip.status_code is not 200:
            print('COULDNT GET IDs')
            return id_ip.status_code
        else:
            ids = id_ip.json()
        return [ids['id'], ids['accountId'], ids['puuid']]  # ID, ACCT ID, PUUID

    # GET RANKED DATA FOR A SUMMONER, SOLOQ AND FLEX RANKS + WRS
    def get_ranked(self):
        sum_dat_endpoint = f'https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/{self.ids[0]}'
        sum_dat = requests.get(sum_dat_endpoint, headers=self.headers).json()

        # CALCULATE STATS FROM SOLOQ DATA
        def get_soloq_stats():
            self.rank = self.soloq['tier'] + ' ' + self.soloq['rank']
            self.wr = self.soloq['wins'] / (self.soloq['wins'] + self.soloq['losses'])
            self.lp = self.soloq['leaguePoints']
            self.games = self.soloq['wins'] + self.soloq['losses']

        # PARSE RANKED DATA
        if not sum_dat:
            print('NOT SUM DAT')
            return
        elif sum_dat[0]['queueType'] == 'RANKED_SOLO_5x5' and len(sum_dat) == 1:
            self.soloq = sum_dat[0]
            get_soloq_stats()
        elif sum_dat[0]['queueType'] == 'RANKED_FLEX_SR' and len(sum_dat) == 1:
            self.flex = sum_dat[0]
        elif sum_dat[1]['queueType'] == 'RANKED_SOLO_5x5':
            self.soloq = sum_dat[1]
            get_soloq_stats()
            self.flex = sum_dat[0]
        elif sum_dat[0]['queueType'] == 'RANKED_SOLO_5x5' and sum_dat[1]['queueType'] == 'RANKED_FLEX_SR':
            self.soloq = sum_dat[0]
            get_soloq_stats()
            self.flex = sum_dat[1]
        else:
            print('UNRANKED')

    # CONVERT TO LINEARLY DISTRIBUTED NUMERICAL RANKS AT 250 PER RANK
    @property
    def soloq_lin_mmr(self):
        lin_mmr_dict = {'IRON IV': 0, 'IRON III': 250, 'IRON II': 500, 'IRON I': 750, 'BRONZE IV': 1000, 'BRONZE III':
            1250, 'BRONZE II': 1500, 'BRONZE I': 1750, 'SILVER IV': 2000, 'SILVER III': 2250, 'SILVER II':
                            2500, 'SILVER I': 2750, 'GOLD IV': 3000, 'GOLD III': 3250, 'GOLD II': 3500, 'GOLD I': 3750,
                        'PLATINUM IV': 4000, 'PLATINUM III': 4250, 'PLATINUM II': 4500, 'PLATINUM I': 4750}

        if type(self.rank) is str:
            return lin_mmr_dict[self.rank] + 2 * self.lp
        else:
            print('SUMMONER UNRANKED')
            return None

    @property
    def match_history(self):
        # print("MATCH_HISTORY")
        game_hist = requests.get(f"https://na1.api.riotgames.com/lol/match/v4/matchlists/by-account/{self.ids[1]}",
                                 headers=self.headers).json()
        return game_hist

    def yield_games(self, queue_type=420):
        for match in self.match_history['matches']:
            if match['queue'] == queue_type:
                soloq_match = Match(match['gameId'])
                if soloq_match.game_duration > 15*60:  # 15 min
                    print('got match!')
                    yield soloq_match

    def get_recent_soloq_games(self, days=7, limit=57):
        matches = []
        for match in self.yield_games(420):
            now = datetime.datetime.now()
            week_ago = now - datetime.timedelta(days=days)
            time_diff = match.game_time - week_ago
            if time_diff.days > -1 and len(matches) < limit:  # BC APPARENTLY WHEN ITS OVER 57 THE SHIT CRASHES
                # print(len(matches), ' ', matches)
                matches.append(match)
            else:
                # print('DONE', matches)
                return matches

    @property
    def recent_soloq_stats(self):
        games = self.get_recent_soloq_games()
        gamestatlist = {}

        for game in games:
            score = game.calc_point_base(self.ign)
            stats = {
                'champ': game.player_champ(self.ign),
                'date': game.game_time.strftime("%m/%d/%Y"),
                'duration': game.game_duration_min,
                'kda': game.get_kda(self.ign),
                'csm': game.get_csm(self.ign),
                'vision': game.get_vision_score(self.ign)
            }

            gamestatlist[score] = stats

        return gamestatlist


class Match:
    def __init__(self, match_id):
        self.id = match_id
        self.headers = HEADERZ
        self.game = self.get_game()

    @except429
    def get_game(self):
        # print('GET_GAME')
        game = requests.get(f'https://na1.api.riotgames.com/lol/match/v4/matches/{self.id}', headers=self.headers)
        if game.status_code == 200:
            game = game.json()
            return game
        else:
            print(f'TOO MANY GET_GAME REQUESTS')
            return game.status_code

    @property
    def game_time(self):
        time_ms = self.game['gameCreation']
        game_datetime = datetime.datetime.fromtimestamp(time_ms // 1000.0)
        return game_datetime

    @property
    def game_duration(self):
        return self.game['gameDuration']

    @property
    def game_duration_min(self):
        g_d = self.game['gameDuration']
        mins = g_d // 60
        remainder = round((g_d - mins) / 100)
        if remainder > 9:
            return f'{mins}:{remainder}'
        else:
            return f'{mins}:0{remainder}'

    def get_participant(self, name):
        for part in self.game['participantIdentities']:
            sumr_name = part['player']['summonerName']
            if sumr_name.lower() == name.lower():
                pid = part['participantId']

                # SET NAME
                game = self.game['participants'][pid - 1]
                game['name'] = name
                return game
        else:
            print(self.game['participantIdentities'])
            print(self.game['participants'])
            print('SUMMONER NOT FOUND!')
            return 404

    # USED IN POINT BASE
    def get_kda(self, name, decimal=False):

        # LOOK UP STATS
        stats = self.get_participant(name)['stats']
        kills = stats['kills']
        deaths = stats['deaths']
        assists = stats['assists']

        # RETURN KDA AS DECIMAL
        if decimal:
            kda = (kills + assists) / deaths

        # RETURN KDA TUPLE
        else:
            kda = (kills, deaths, assists)
        return kda

    # USED IN POINT BASE
    def get_cs(self, name):
        stats = self.get_participant(name)['stats']
        cs = stats['neutralMinionsKilled'] + stats['totalMinionsKilled']
        return cs

    # USED IN POINT BASE
    def get_vision_score(self, name):
        return self.get_participant(name)['stats']['visionScore']

    # USED IN POINT BASE
    def get_csm(self, name):
        cs = self.get_cs(name)
        return cs/(self.game_duration/60)

    # MFKING POINT BASE
    def calc_point_base(self, name):
        k, d, a = self.get_kda(name)
        csm = self.get_csm(name)
        vision = self.get_vision_score(name)
        points = k - d + a/2 + 1.5*csm + vision/10
        return round(points, 2)

    # LOOK UP CHAMP NAME OF PLAYER IN GAME
    def player_champ(self, name):
        stats = self.get_participant(name)
        return get_champ(stats['championId'])


# PRINT BASE STATS FOR TWO PLAYERS SIDE-BY-SIDE OVER N GAMES IN M DAYS
def compare_bois(sum1, sum2, n_games=57, days=7):
    ed = Summoner(sum1)
    pogoz = Summoner(sum2)
    edwins = 0
    pogozwins = 0

    # get and zip da matches as match objects
    matches = ed.get_recent_soloq_games(days=days, limit=n_games)
    p_matches = pogoz.get_recent_soloq_games(days=days, limit=n_games)
    z_matches = zip(matches, p_matches)

    # pull da stats from the match objects and print! also count wins
    print(f'{sum1} vs {sum2} over {n_games}\n--------------------------------------------------------------\n')
    for match, p_match in z_matches:

        # pull stats sum1
        k, d, a = match.get_kda(ed.ign)
        csm = round(100*match.get_csm(ed.ign))/100
        pts = match.calc_point_base(ed.ign)
        v = match.get_vision_score(ed.ign)

        # pull stats sum2
        pk, pd, pa = p_match.get_kda(pogoz.ign)
        pcsm = round(p_match.get_csm(pogoz.ign), 2)
        ppts = p_match.calc_point_base(pogoz.ign)
        pv = p_match.get_vision_score(pogoz.ign)

        # preeeent
        print('      ', match.game_duration_min, match.player_champ(ed.ign), "  vs  ",
              p_match.game_duration_min, p_match.player_champ(pogoz.ign))
        print(f'    {k}/{d}/{a} {csm}cs/m | {pk}/{pd}/{pa} {pcsm}cs/m\n          {v} vision | {pv} vision\n'
              f'        {pts} POINTS | {ppts} POINTS')

        # win count
        if pts > ppts:
            print(ed.ign, ' wins')
            edwins += 1
        else:
            print(pogoz.ign, ' wins')
            pogozwins += 1
        print(f'{edwins} - {pogozwins}\n')


def main():
    ed = Summoner('ipogoz')
    gamestats = ed.recent_soloq_stats
    for stat in gamestats:
        print(stat, gamestats[stat])


if __name__ == '__main__':
    main()
