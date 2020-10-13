import matplotlib.pyplot as plt
from elbert.asyncriothandle import AsyncRequester as AR
from elbert.updater import Updater, get_champ
import json
import time

REQ_PER_SEC = 20
LIB_FP = '../json/gamelib.json'


def keynumerate(dictionary: dict):
    assert isinstance(dictionary, dict)
    keys = []
    values = []
    
    for k, v in dictionary.items():
        for s in v:
            keys.append(k)
            values.append(s)
    
    return keys, values


def dict_avg(dictionary: dict):
    assert isinstance(dictionary, dict)
    avgs = {}

    for k, v in dictionary.items():
        avgs[k] = sum(v)/len(v)

    return avgs


class Summoner(Updater):
    def __init__(self, ign: str):
        super().__init__("ABC")
        self.ign = ign
        self.stats = self.load_player()
        self.id = self.stats['dat']['id']
        self.aid = self.stats['dat']['accountId']
        self.cost = self.stats['wr mod']
        self.rank = self.stats['rank']

    def load_player(self):
        """looks up or returns ID's for a summoner's IGN. order is (1) id, (2) account id, (3) puudi"""
        if self.ign not in self.league["PLAYERS"]:
            self.update_summoner([self.ign])
        return self.league["PLAYERS"][self.ign]
    
    def get_history(self, queries: dict):
        hist_ar = AR()
        hist_ar.match_history(self.aid, queries=queries)
        return hist_ar.run()

    def get_soloq(self, update=False):
        match_ar = AR()
        resp = []

        matches = self.get_history({'queue': 420})
        for match in matches[0]['matches']:
            match_ar.match(match['gameId'])
            if (AR.t_req + match_ar.__floor__().c_req) % REQ_PER_SEC == 0:
                resp += match_ar.run()  # run
                time.sleep(1)  # then wait a sec
                Updater.chunks_sent += 1
                if Updater.chunks_sent % 5 == 0:  # 100 req / 90 (120?) sec
                    print('*********************************100*******************************')
                    # time.sleep(1)  # or 120...
        resp += match_ar.run()
        return resp


class Versioner(Updater):
    def __init__(self):
        super().__init__("ABC")
        with open(LIB_FP) as f:
            self.lib = json.load(f)

        self.lv = self.lib['literalVersion']
        self.version = self.lib['version']
        self.key = str(self.version) + '.' + str(self.lv)
        self.cv = self.lib[self.key]
        self.c_games = self.cv['games'] if 'games' in self.cv else {}

    def save_lib(self):
        self.lib['literalVersion'] = self.lv
        self.lib['version'] = self.version
        self.lib[self.key] = self.cv
        self.lib[self.key]['games'] = self.c_games

        with open(LIB_FP, 'w') as f:
            json.dump(self.lib, f, indent=4)

    def load_version(self, version_key: str):
        try:
            self.cv = self.lib[version_key]
            self.version, self.lv = version_key.split('.')
            return True
        except KeyError:
            return False

    def new_version(self, notes: str, values: str):
        def_notes = "points = (kills + .75 * assists - deaths) * (0.9 + kp / 5) + csm + 3 * vpm"
        def_values = (1, 0.75, 1, 0.9, 5, 1, 3, 0)  # K, A, D, KPb, KPd, CSM, VPM, DP coefficients
        k, a, d, kpb, kpd, vsm, vpm, dp = def_values
        
        if notes != self.cv['notes']:  # new notes means new equation, new version!
            self.version += 1  # create new version here
        
        if values != self.cv['values']:  # create new literalVersion (subversion) here
            self.lv += 1  # new subverion here

    def analyze_current(self):
        scores = {}
        for gid, game in self.c_games.items():
            for player, stats in game.items():
                scores[player] = [] if player not in scores else scores[player]
                scores[player].append(stats["score"])

        kn_names, kn_scores = keynumerate(scores)
        avgs = dict_avg(scores)
        fig, axs = plt.subplots(figsize=(len(scores) + 4, 10))
        axs.scatter(kn_names, kn_scores, marker='.')
        axs.scatter(list(avgs.keys()), list(avgs.values()), c='red', label='average', marker='d')
        fig.suptitle('xanax')

        rd, cd = {}, {}
        for ign in avgs:
            summoner = Summoner(ign)
            rd[ign] = (avgs[ign]/summoner.cost)*100
            cd[ign] = summoner.cost - 40
        plt.scatter(list(cd.keys()), list(cd.values()), c='lime', label='cost', marker='d')
        plt.scatter(list(rd.keys()), list(rd.values()), c='m', label='avg/cost', marker='D')

        plt.legend()
        plt.show()

        return scores

    def by_rank(self):
        scores = {}
        i = 0
        for gid, game in self.c_games.items():
            for player, stats in game.items():
                rank = self.league["PLAYERS"][player]['rank']
                scores[rank] = [] if rank not in scores else scores[rank]
                scores[rank].append(stats["score"])

                i += 1
                print(f'{i}/{len(self.c_games)}')

        kn_ranks, kn_scores = keynumerate(scores)
        fig, axs = plt.subplots(figsize=(len(scores) + 4, 10))
        axs.scatter(kn_ranks, kn_scores)
        plt.show()

        return scores

    def _parse_game_resp(self, raw_games):
        for game in raw_games:
            if 'status' in game:  # skip errors
                continue

            matched = self._get_registered_pids(game)  # get riot's dumb participant id's
            self.c_games[game['gameId']] = {} if game['gameId'] not in self.c_games else self.games[game['gameId']]

            for player, pid in matched.items():
                part = game['participants'][pid-1]
                stats = part['stats']

                # CALCULATE (MAKE THIS ITS OWN CLASS)
                duration = game['gameDuration']
                kills = stats["kills"]
                deaths = stats["deaths"]
                assists = stats["assists"]
                csm = (stats['neutralMinionsKilled'] + stats['totalMinionsKilled']) / (duration / 60)
                team = part['teamId']
                tk, td, ta = 0, 0, 0  # team kills, assists, deaths
                for sumr in game["participants"]:
                    if sumr["teamId"] == team:
                        tk += sumr["stats"]["kills"]
                        td += sumr["stats"]["deaths"]
                        ta += sumr["stats"]["assists"]
                kp = (kills + assists) / tk if tk > 0 else 1
                dp = deaths / td if td > 0 else 0
                vpm = stats['visionScore'] / (duration / 60)
                points = (kills + .75 * assists - deaths) * (0.9 + kp / 5) + csm + 3 * vpm

                # WRITE
                c_game = self.c_games[game['gameId']]
                c_game.update({player: {"pid": pid,
                                        "score": round(points, 2),
                                        "champ": get_champ(part['championId']),
                                        "kda": (kills, deaths, assists),
                                        "duration": duration,
                                        "csm": round(csm, 2),
                                        "team": team,
                                        "kp": round(100 * kp, 2),
                                        "dp": round(100 * dp, 2),
                                        "vpm": round(vpm, 2)
                                        }})  # create player dicts within the game
                self.c_games[game['gameId']].update(c_game)

        self.save_lib()
        return self.c_games


wax = Versioner()
print(wax.analyze_current())
