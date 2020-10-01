from riothandle import Summoner, Match
import json
import datetime
from elbert.updater import Updater


def _sq_open():  # this is called on sq_save, which is called by elbert on_ready
    global sq_file, sq_games
    with open('./json/soloqgames.json') as sq_file:
        sq_games = json.load(sq_file)


_sq_open()
# ^ open the soloq games... called a bunch. below i open sf just for id reference. all other sf ops are in class League


def recent(raw_timestamp_ms, date=False, last=True):
    if date:
        time = datetime.datetime.strptime(raw_timestamp_ms, "%m/%d/%Y")
    else:
        time = datetime.datetime.fromtimestamp(raw_timestamp_ms // 1000)

    today = datetime.datetime.today()
    n = 7 if last else 0
    friday = today + datetime.timedelta((4 - today.weekday()) % 7) - datetime.timedelta(n)
    return time.date() >= friday.date()


def update_pts(name):
    for player in sq_games:
        if player == name:
            for game in sq_games[player]:
                new_pts = Match(game).calc_point_base(name)
                sq_games[player][game]['score'] = new_pts
            print(f'UPDATED {name}!\n')
            sq_save()


def sq_save():
    with open('./json/soloqgames.json', 'w') as f:
        json.dump(sq_games, f, indent=4)
        print('*SQSAVE')

    _sq_open()


def sq_clean_games():
    for player in sq_games:
        delete = [key for key in sq_games[player] if not recent(sq_games[player][key]["date"], True)]

        for key in delete:
            print(f'delete game {key} on {sq_games[player][key]["date"]}')
            del sq_games[player][key]

    sq_delete_empty_players()
    sq_save()


def sq_delete_empty_players():  # call this at the end
    _delete = []

    for _player in sq_games:
        if sq_games[_player] == {}:
            _delete.append(_player)

    for _player in _delete:
        print(f'deleting {_player}...')
        del sq_games[_player]


def new_dr_league(name, budget, whitelisted=False):
    now = datetime.datetime.now().date()

    with open('./json/silverfantasy.json') as fan_file:
        if League(name).index is None:
            sf_dat = json.load(fan_file)
            l_dat = sf_dat["LEAGUES"]
            p_dat = sf_dat["PLAYERS"]
            l_dat.append({
                "name": name,
                "commissioner": "xân",
                "start": now.strftime('%m/%d/%Y'),
                "lock@": now.strftime('%m/%d/%Y'),
                "index": len(l_dat),
                "budget": budget,
                "royale": True,
                "whitelisted": whitelisted,
                "teams": {

                }
            })

            data = {"LEAGUES": l_dat, "PLAYERS": p_dat}
            with open('./json/silverfantasy.json', 'w') as outfile:
                json.dump(data, outfile, indent=4)

            return League(name)
        else:
            print('League already exists')
            return 40


class Player(Summoner):
    def __init__(self, ign):
        super().__init__(ign)
        self.wr_mod = self.calc_linpoints()

    def calc_linpoints(self):
        if not self.rank:
            points = 0
        else:
            points = 50 + (self.games / (self.games + 50)) * ((self.wr * 100) - 50) + (self.soloq_lin_mmr / 400)

        return points

    def weekly_soloq_stats(self):
        gamestatlist = {}
        week_total = 0
        roles = []

        # CHECK TO SEE IF THE PLAYER IS IN SOLOQGAMES.JSON
        if self.ign in sq_games:
            games = sq_games[self.ign]
        else:
            sq_games[self.ign] = {}
            games = {}

        try:
            for game in self.match_history['matches']:
                if recent(game['timestamp']) and game['queue'] == 420:
                    if str(game['gameId']) in list(games.keys()):
                        print('game loaded')
                        g = games[str(game['gameId'])]  # game id's are stored as strings for... whatever reason.
                        gamestatlist[g['score']] = g
                        week_total += g['score']
                        roles.append(g['role'])
                    else:
                        game = Match(game['gameId'])
                        k, d, a = game.get_kda(self.ign)
                        score = game.calc_point_base(self.ign)  # here's where you would swap the point calc.
                        week_total += score

                        stats = {
                            'score': score,
                            'champ': game.player_champ(self.ign),
                            'date': game.game_time.strftime("%m/%d/%Y"),
                            'role': game.get_role(self.ign),
                            'duration': game.game_duration_min,
                            'kda': f'{k}/{d}/{a}',
                            'kp': game.get_kp(self.ign),
                            'csm': round(game.get_csm(self.ign), 2),
                            'vision': game.get_vision_score(self.ign),
                            '*cc': round(game.get_cc(self.ign), 2)
                        }

                        gamestatlist[score] = stats
                        games[game.id] = stats
                        roles.append(game.get_role(self.ign))
        except KeyError:
            print(self.match_history)
            return 404

        if len(games) == 0:
            return 404

        avg = week_total / len(games)
        role = max(set(roles), key=roles.count) if roles else None

        sq_games[self.ign] = games
        sq_save()
        return gamestatlist, avg, role


class League:
    def __init__(self, name):
        self.name = name.upper()
        self.league_dat, self.player_dat = self.load_league()

        if self.league_dat is not None:
            self.index = self.league_dat['index']
        else:
            self.index = None
            print('404 League not found')

    @property
    def is_royale(self):
        return self.league_dat['royale']

    def load_league(self):
        with open('./json/silverfantasy.json') as fan_file:
            sf_dat = json.load(fan_file)
            l_dat = sf_dat["LEAGUES"]
            p_dat = sf_dat["PLAYERS"]
            for league in l_dat:
                if league["name"] == self.name:
                    return league, p_dat
            else:
                return None, None

    @staticmethod
    def load_all_leagues():
        with open('./json/silverfantasy.json') as fan_file:
            sf_dat = json.load(fan_file)
            l_dat = sf_dat["LEAGUES"]

            return l_dat

    def save_league(self):  # for writing j_dat to local json file
        leagues = self.load_all_leagues()
        leagues[self.index] = self.league_dat
        data = {"LEAGUES": leagues, "PLAYERS": self.player_dat}
        print('*LEAGUESAVE')
        with open('./json/silverfantasy.json', 'w') as outfile:
            json.dump(data, outfile, indent=4)

    def update_player(self, ign):
        player = Player(ign)

        try:
            leagues = self.player_dat[ign]['leagues']
        except KeyError:
            leagues = []

        dat = player.get_sum_id(ret_all=True)
        self.player_dat[ign] = {
            "rank": player.rank,
            "wr": (round(player.wr * 10000) / 100),
            "leagues": leagues,
            "games": player.games,
            "wr mod": player.wr_mod,
            "dat": dat
        }

        return player

    @property
    def master_player_list(self):
        for player in self.player_dat:
            yield player

    def score_local(self, player):
        score_tups = []

        if player in (self.player_dat and sq_games):
            player_games = sq_games[player]
            for gid, game in player_games.items():
                score_tups.append((gid, game["score"], game["champ"], game["kda"]))

        score_tups = sorted(score_tups, key=lambda x: x[1], reverse=True)
        return score_tups

    # ADD A LEAGUE TO A PLAYERS LEAGUE LIST SO THAT THEY CAN BE DRAFTED TO IT IF ITS EXCLUSIVE
    def whitelist(self, ign):
        self.update_player(ign)
        self.player_dat[ign]["leagues"].append(self.name)
        self.save_league()

    def delist(self, ign):
        for name in self.player_dat[ign]['leagues']:
            if name == self.name:
                self.player_dat[ign]["leagues"].remove(name)
                return self.save_league()
            else:
                print('player not found')
                return 404

    def whitelisted(self, ign):
        if self.name in self.player_dat[ign]['leagues']:
            return True
        elif not self.league_dat['whitelisted']:
            return True
        else:
            return False

    # NOT USED IN ANY OTHER FUNCTIONS RN (aka a TOOL)
    def update_player_teamlist(self):
        for team_id, team in self.league_dat['teams'].items():
            for player in team['players']:
                pasta = self.name + ':' + team_id
                if pasta not in self.player_dat[player]['teams']:
                    self.player_dat[player]['teams'].append(pasta)
                    print(pasta)

        self.save_league()

    def add_rteam(self, team, name):
        if self.locked:
            return 403

        teams = self.league_dat["teams"]
        teams[team] = {
            'points': 0,
            'owner': name,
            'budget': self.league_dat['budget'],
            'players': {}
        }

        self.save_league()
        return team

    def get_rteam_ppw(self, team_n):
        team = self.league_dat["teams"][team_n]
        team_pts = 0
        sumavg = 0
        gamelist = {}

        for player in team["players"]:
            summoner = Player(player)
            resp = summoner.get_top_games(2)
            if resp == 404:
                pts, avg = 0, 0
                games = [{}, {}]
            else:
                pts, avg, games = resp

            team_pts += pts
            sumavg += avg
            gamelist[player] = games
            gamelist[player].append({'avg': round(avg, 1), 'pts': round(pts, 1)})

        self.league_dat["teams"][team_n]["points"] = team_pts
        self.save_league()
        return team_pts, sumavg, gamelist

    def score_all_teams(self):
        teams = []

        for team in self.league_dat["teams"]:
            team_pts, sumavg, gamelist = self.get_rteam_ppw(team)
            teams.append((team, team_pts))

        teams = sorted(teams, key=lambda x: x[1], reverse=True)
        print('SORTED TEAMS:  ', teams)

        return teams

    def add_player_to_team(self, ign, team):
        if self.locked:
            return f'403: TEAMS LOCKED IN'

        player = self.update_player(ign)
        w = self.whitelisted(ign)
        if not w:
            return f'403: {ign} NOT WHITELISTED'

        elif self.league_dat['royale']:
            budget = self.league_dat['teams'][team]['budget']
            if budget >= player.wr_mod:
                self.league_dat['teams'][team]['players'][ign] = round(player.wr_mod)
                self.league_dat['teams'][team]['budget'] -= round(player.wr_mod)
                self.save_league()
                return self.league_dat['teams'][team]['budget']
            else:
                return f'400: {round(player.wr_mod - budget, 2)}  PTS TOO EXPENSIVE'

    def remove_player_from_team(self, ign, team):
        if self.locked:
            return 403

        if ign in self.league_dat['teams'][team]['players']:
            pts = self.league_dat['teams'][team]['players'][ign]
            del self.league_dat['teams'][team]['players'][ign]

            if self.league_dat['royale']:
                self.league_dat['teams'][team]['budget'] += pts

            self.save_league()

        else:
            print('SUMMONER NOT ON TEAM')
            return 404

    def ordered_players(self):
        # MAKE SORTED LIST OF DR COSTS
        pointlist = []
        for player in self.player_dat:
            if 'wr mod' not in self.player_dat[player]:
                summoner = Player(player)
                self.player_dat[player]['wr mod'] = summoner.calc_linpoints()

            pointlist.append((player, self.player_dat[player]['wr mod']))
        spointlist = sorted(pointlist, key=lambda x: x[1], reverse=True)

        return spointlist

    @property
    def start_date(self):
        return datetime.datetime.strptime(self.league_dat['start'], '%m/%d/%Y')

    @property
    def lock_at(self):
        lock_date = datetime.datetime.strptime(self.league_dat['lock@'], '%m/%d/%Y')
        return datetime.datetime.combine(lock_date.date(), datetime.time(hour=23, minute=59, second=59))

    @property
    def unlock_at(self):
        return self.lock_at + datetime.timedelta(5)

    @property
    def locked(self):
        now = datetime.datetime.now()
        # return False
        return now > self.lock_at

    def start_friday(self):
        today = datetime.datetime.today()
        friday = today + datetime.timedelta((4 - today.weekday()) % 7)  # ITS ACTUALLY SUNDAY LMAO
        self.league_dat['lock@'] = friday.strftime('%m/%d/%Y')
        self.save_league()

        return friday.date()


def main():
    xfl = League("XFL")
    xfl.update_player_teamlist()


if __name__ == '__main__':
    main()
