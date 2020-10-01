import requests
import os
from dotenv import load_dotenv
import datetime
import time
from functools import wraps
import json


# RIOTAPI.PY REWRITE.
# RIOT API HANDLER 2


def get_riot_token():
    load_dotenv()
    r_toke = os.getenv('RIOT_TOKEN')  # app API key
    riot_headers = {"X-Riot-Token": r_toke}
    print('T0KEN L0ADED\n')

    return riot_headers


headers = get_riot_token()
with open('./json/silverfantasy.json') as f:
    sf_json = json.load(f)


def get_champ(champ_id):
    champ_dat = requests.get('http://ddragon.leagueoflegends.com/cdn/10.10.3208608/data/en_US/champion.json').json()[
        'data']
    for champ in champ_dat:
        cid = int(champ_dat[champ]['key'])
        if cid == champ_id:
            return champ


def except429(func):
    @wraps(func)
    def except_wrapper(*args, **kwargs):
        funcy = func(*args, **kwargs)
        if type(funcy) is not int:
            return funcy
        else:
            pass

        if funcy == 429:
            print(f'CODE {funcy}')
            print('trying again in 93 seconds...')
            time.sleep(93)
            return func(*args, **kwargs)
        elif funcy == 504 or 503:
            print(f'CODE {funcy}')
            return func(*args, **kwargs)
        else:
            print(f'CODE {funcy}')
            return funcy

    return except_wrapper


class Summoner:

    def __init__(self, ign):
        self.ign = ign
        self.headers = headers
        self.soloq = None
        self.flex = None
        self.rank = None
        self.lp = 0
        self.games = 0
        self.wr = 0
        self.icon = None
        self.ids = self.get_sum_id() if ign not in sf_json["PLAYERS"] else (
            sf_json["PLAYERS"][ign]['dat']['id'],
            sf_json["PLAYERS"][ign]['dat']['accountId'],
            sf_json["PLAYERS"][ign]['dat']['puuid'])

        if type(self.ids) is list or tuple:
            self.get_ranked()

    def __repr__(self):
        return self.ign

    def __str__(self):
        return self.ign

    # GET IDs FROM SUMMONER NAME, [0] is SUM ID [1] is ACCT ID [2] is PUUID
    @except429
    def get_sum_id(self, ret_all=False):
        if self.ign in sf_json and ret_all:
            ids = sf_json["PLAYERS"][self.ign]['dat']
            return ids
        elif self.ign in sf_json:
            ids = sf_json["PLAYERS"][self.ign]['dat']
            return [ids['id'], ids['accountId'], ids['puuid']]

        name_endpoint = f'https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{self.ign}'
        id_ip = requests.get(name_endpoint, headers=self.headers)
        if id_ip.status_code is not 200:
            print('COULDNT GET IDs')
            return id_ip.status_code
        else:
            print('got ID')
            ids = id_ip.json()
            self.icon = ids["profileIconId"]

        if ret_all:
            return ids
        else:
            return [ids['id'], ids['accountId'], ids['puuid']]  # ID, ACCT ID, PUUID

    # GET RANKED DATA FOR A SUMMONER, SOLOQ AND FLEX RANKS + WRS
    @except429
    def get_ranked(self):
        sum_dat_endpoint = f'https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/{self.ids[0]}'
        sum_dat = requests.get(sum_dat_endpoint, headers=self.headers).json()

        # CALCULATE STATS FROM SOLOQ DATA
        @except429
        def get_soloq_stats():
            self.rank = self.soloq['tier'] + ' ' + self.soloq['rank']
            self.wr = self.soloq['wins'] / (self.soloq['wins'] + self.soloq['losses'])
            self.lp = self.soloq['leaguePoints']
            self.games = self.soloq['wins'] + self.soloq['losses']

        # PARSE RANKED DATA
        if not sum_dat:
            print('NOT SUM DAT', sum_dat, '***********')
            return
        elif sum_dat[0]['queueType'] == 'RANKED_SOLO_5x5' and len(sum_dat) == 1:
            self.soloq = sum_dat[0]
            get_soloq_stats()
        elif sum_dat[0]['queueType'] == 'RANKED_FLEX_SR' and len(sum_dat) == 1:
            print(f'{sum_dat}')
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
                        'PLATINUM IV': 4000, 'PLATINUM III': 4250, 'PLATINUM II': 4500, 'PLATINUM I': 4750,
                        'DIAMOND IV': 5000, 'DIAMOND III': 5500, 'DIAMOND II': 6000, 'DIAMOND I': 6500, 'MASTER I':
                            7000, 'GRANDMASTER I': 7500, 'CHALLENGER I': 8000}

        if type(self.rank) is str:
            return lin_mmr_dict[self.rank] + 2 * self.lp
        else:
            print('SUMMONER UNRANKED')
            return None

    @property
    @except429
    def match_history(self):
        print(f"getting match history for {self.ign}...")
        game_hist = requests.get(f"https://na1.api.riotgames.com/lol/match/v4/matchlists/by-account/{self.ids[1]}",
                                 headers=self.headers).json()
        return game_hist

    def yield_games(self, queue_type=420):
        for match in self.match_history['matches']:
            if match['queue'] == queue_type:
                soloq_match = Match(match['gameId'])
                if soloq_match.game_duration > 15 * 60:  # 15 min
                    yield soloq_match

    def get_recent_soloq_games(self, days=7, limit=57):
        matches = []
        for match in self.yield_games(420):
            now = datetime.datetime.now()
            week_ago = now.date() - datetime.timedelta(days=days)
            if week_ago <= match.game_time and len(matches) < limit:  # BC APPARENTLY WHEN ITS OVER 57 THE SHIT CRASHES
                # print(len(matches), ' ', matches)
                matches.append(match)
            else:
                # print('DONE', matches)
                return matches

    @property
    def avg_stats(self):
        n, t_kdad, t_k, t_d, t_a, t_csm, t_vision = 0, 0, 0, 0, 0, 0, 0
        t_points = 0
        roles = []

        for game in self.yield_games():
            n += 1
            t_points += game.calc_point_base(self.ign)
            k, d, a = game.get_kda(self.ign)
            t_k += k
            t_d += d
            t_a += a
            t_csm += game.get_csm(self.ign)
            t_vision += game.get_vision_score(self.ign)

            roles.append(game.get_role(self.ign))

        totals = (n, t_points, t_k, t_d, t_a, t_csm, t_vision)
        t_kdad = (t_k + t_a) / t_d
        most_role = max(set(roles), key=roles.count)
        return {'games': n, 'role': most_role, 'ppg': t_points / n,
                'kda': f'{round(t_k / n)}/{round(t_d / n)}/{round(t_a / n)}'
            , 'csm': t_csm / n, 'vision': t_vision / n, 'kdad': t_kdad, 'totals': totals}

    def weekly_soloq_stats(self):
        games = self.get_recent_soloq_games()
        gamestatlist = {}
        week_total = 0
        roles = []

        for game in games:
            k, d, a = game.get_kda(self.ign)
            score = game.calc_point_base(self.ign)
            week_total += score
            stats = {
                'score': score,
                'champ': game.player_champ(self.ign),
                'role': game.get_role(self.ign),
                'date': game.game_time.strftime("%m/%d/%Y"),
                'duration': game.game_duration_min,
                'kda': f'{k}/{d}/{a}',
                'csm': round(game.get_csm(self.ign), 2),
                'vision': game.get_vision_score(self.ign),
                '*cc': round(game.get_cc(self.ign), 2)
            }

            gamestatlist[score] = stats
            roles.append(game.get_role(self.ign))

        avg = week_total / len(games)
        role = max(set(roles), key=roles.count)
        return gamestatlist, avg, role

    def get_top_games(self, n_games):
        top_games = []
        gsum = 0

        resp = self.weekly_soloq_stats()
        if resp == 404:
            print('NO GAMES FOUND')
            return 404
        else:
            gamestatlist, g_avg, role = resp

        scores = sorted(list(gamestatlist.keys()), reverse=True)
        if len(scores) < n_games:
            n_games = len(scores)

        for i in range(n_games):
            score = scores[i]
            stats = gamestatlist[score]
            top_games.append(stats)
            gsum += score

        return gsum, g_avg, top_games


class Match:
    def __init__(self, match_id):
        self.id = match_id
        self.headers = headers
        self.game = self.get_game()
        print(f'got game at {self.game_time}')

    def __repr__(self):
        return f'DATE: {self.game_time} / LENGTH: {self.game_duration_min}\n{self.game["participantIdentities"]}'

    @except429
    def get_game(self):
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

    def get_player_team(self, name):
        sumr = self.get_participant(name)
        return sumr["teamId"]

    def get_team_kda(self, team: int):
        tk, td, ta = 0, 0, 0

        for sumr in self.game["participants"]:
            if sumr["teamId"] == team:
                tk += sumr["stats"]["kills"]
                td += sumr["stats"]["deaths"]
                ta += sumr["stats"]["assists"]

        return tk, td, ta

    def get_kp(self, name):
        k, d, a = self.get_kda(name)
        tk, td, ta = self.get_team_kda(self.get_player_team(name))
        if tk == 0:
            tk = 1

        return (k + a) / tk

    def get_role(self, name):
        timeline = self.get_participant(name)['timeline']
        return timeline['role'] + ' ' + timeline['lane']

    # USED IN POINT BASE
    def get_kda(self, name, decimal=False):

        # LOOK UP STATS
        stats = self.get_participant(name)['stats']
        kills = stats['kills']
        deaths = stats['deaths']
        assists = stats['assists']

        # RETURN KDA AS DECIMAL
        if decimal and deaths > 0:
            kda = (kills + assists) / deaths
        elif decimal:
            kda = 1.1 * (kills + assists)

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
        return cs / (self.game_duration / 60)

    # MFKING POINT BASE
    def calc_point_base(self, name):
        k, d, a = self.get_kda(name)
        kp = self.get_kp(name)
        csm = self.get_csm(name)
        vpm = self.get_vision_score(name) / (self.game_duration / 60)
        points = (k + .75 * a - d) * (0.9 + kp / 5) + csm + 3 * vpm

        return round(points, 2)

    # USED IN CC POINTS
    def get_cc(self, name):
        stats = self.get_participant(name)['stats']
        cc = stats["timeCCingOthers"]
        kda = self.get_kda(name, True)

        ccp = (kda / (self.game_duration / 60)) * cc
        return ccp

    # LOOK UP CHAMP NAME OF PLAYER IN GAME
    def player_champ(self, name):
        stats = self.get_participant(name)
        return get_champ(stats['championId'])


def main():
    now = datetime.datetime.now()
    week_ago = now.date() - datetime.timedelta(days=7)
    a = datetime.date(2020, 9, 5)
    print(week_ago < a)


if __name__ == '__main__':
    main()
