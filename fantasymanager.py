from riothandle import Summoner, Match
import json
import datetime

sq_file = open('./json/soloqgames.json')
sq_games = json.load(sq_file)


def recent(raw_timestamp_ms, date=False):

    if date:
        time = datetime.datetime.strptime(raw_timestamp_ms, "%m/%d/%Y")
    else:
        time = datetime.datetime.fromtimestamp(raw_timestamp_ms // 1000)

    week_ago = datetime.datetime.now() - datetime.timedelta(7)
    return time > week_ago


def sq_save():
    with open('./json/soloqgames.json', 'w') as f:
        json.dump(sq_games, f, indent=4)
        print('*SQSAVE')

    global sq_file
    sq_file = open('./json/soloqgames.json')


def sq_clean_games():
    # Using dictionary comprehension to find list
    for player in sq_games:
        delete = [key for key in sq_games[player] if not recent(sq_games[player][key]["date"], True)]

        for key in delete:
            print('delete game')
            del sq_games[player][key]

    sq_save()


def sq_delete_empty_players():
    delete = []

    for player in sq_games:
        if sq_games[player] == {}:
            delete.append(player)

    for player in delete:
        print(f'deleting {player}...')
        del sq_games[player]
    sq_save()


def new_dr_league(name, budget, whitelisted=False):
    with open('./json/silverfantasy.json') as fan_file:
        if League(name).index is None:
            sf_dat = json.load(fan_file)
            l_dat = sf_dat["LEAGUES"]
            p_dat = sf_dat["PLAYERS"]
            l_dat.append({
                "name": name,
                "commissioner": "xân",
                "commisioned": datetime.datetime.now().date(),
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
            points = 50 + (self.games/(self.games+50))*((self.wr*100)-50) + (self.soloq_lin_mmr/400)

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
                        'csm': round(game.get_csm(self.ign), 2),
                        'vision': game.get_vision_score(self.ign),
                        '*cc': round(game.get_cc(self.ign), 2)
                    }

                    gamestatlist[score] = stats
                    games[game.id] = stats
                    roles.append(game.get_role(self.ign))

        if len(games) == 0:
            return 404

        avg = week_total / len(games)
        role = max(set(roles), key=roles.count)

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

        self.player_dat[ign] = {
            "rank": player.rank,
            "wr": (round(player.wr*10000)/100),
            "leagues": leagues,
            "games": player.games,
            "wr mod": player.wr_mod,
            "stats": {}
        }

        return player

    @property
    def master_player_list(self):
        for player in self.player_dat:
            yield player

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

    def update_all(self, new_players=None):
        for player in self.master_player_list:
            print(f'{player} updated!')
            self.update_player(player)

        # ADD NEW PLAYER(S). TAKES LIST OF STRs OR STR
        if new_players is not None:
            if type(new_players) is str and new_players not in self.master_player_list:
                self.update_player(new_players)
            elif type(new_players) is list:
                for player in new_players:
                    if player not in self.master_player_list:
                        print(f'{player} registered!')
                        self.update_player(player)
                    elif player in self.master_player_list:
                        print(f'{player} already registered')
            elif new_players in self.master_player_list:
                print(f'{new_players} already registered')

        self.save_league()

    def add_rteam(self, team, name):
        teams = self.league_dat["teams"]
        teams[team] = {
            'points': 0,
            'owner': name,
            'budget': self.league_dat['budget'],
            'players': {}
        }

        self.save_league()
        return team

    def get_rteam_ppw(self, team):
        team = self.league_dat["teams"][team]
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

        return team_pts, sumavg, gamelist

    def add_player_to_team(self, ign, team):
        player = self.update_player(ign)
        w = self.whitelisted(ign)
        if not w:
            print(f'{ign} NOT WHITELISTED')
            return 403

        elif self.league_dat['royale']:
            budget = self.league_dat['teams'][team]['budget']
            if budget >= player.wr_mod:
                self.league_dat['teams'][team]['players'][ign] = round(player.wr_mod)
                self.league_dat['teams'][team]['budget'] -= round(player.wr_mod)
                self.save_league()
                return self.league_dat['teams'][team]['budget']
            else:
                print(player.wr_mod-budget, ' PTS TOO EXPENSIVE')
                return 403

    def remove_player_from_team(self, ign, team):
        if ign in self.league_dat['teams'][team]['players']:
            pts = self.league_dat['teams'][team]['players'][ign]
            del self.league_dat['teams'][team]['players'][ign]

            if self.league_dat['royale']:
                self.league_dat['teams'][team]['budget'] += pts

            self.save_league()

        else:
            print('SUMMONER NOT ON TEAM')
            return 404

    @property
    def ordered_players(self):
        # MAKE SORTED LIST OF DR COSTS
        pointlist = []
        for player in self.player_dat:
            (pointlist.append(self.player_dat[player]['wr mod']))
        spointlist = sorted(pointlist, reverse=True)

        # MATCH WRS THEN RETURN PLAYER LIST!
        i = 0
        op_list = []
        while i < len(self.player_dat):
            for player in self.master_player_list:
                if self.player_dat[player]['wr mod'] == spointlist[i]:
                    op_list.append(player)
                    i = i+1
                elif i >= len(self.player_dat)-1:
                    return zip(op_list, spointlist)


def main():
    league = League("PRO")


if __name__ == '__main__':
    main()
