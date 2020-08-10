import riothandle as rh
import json


def new_dr_league(name, budget):
    with open('./json/silverfantasy.json') as fan_file:
        if League(name).index is None:
            sf_dat = json.load(fan_file)
            l_dat = sf_dat["LEAGUES"]
            p_dat = sf_dat["PLAYERS"]
            l_dat.append({
                "name": name,
                "commissioner": "xân",
                "index": len(l_dat),
                "budget": budget,
                "royale": True,
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


class Player(rh.Summoner):
    def __init__(self, ign):
        super().__init__(ign)
        self.leagues = []
        self.wr_mod = self.calc_linpoints()

    def calc_linpoints(self):
        if not self.rank:
            points = 0
        else:
            points = 50 + (self.games/(self.games+50))*((self.wr*100)-50) + (self.soloq_lin_mmr/400)

        return points


class League:
    def __init__(self, name):
        self.name = name
        self.league_dat, self.player_dat = self.load_league()
        if self.league_dat is not None:
            self.index = self.league_dat['index']
        else:
            self.index = None
            print('404 League not found')

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
        with open('./json/silverfantasy.json', 'w') as outfile:
            json.dump(data, outfile, indent=4)

    def update_player(self, ign):
        player = Player(ign)
        self.player_dat[ign] = {
            "rank": player.rank,
            "wr": (round(player.wr*10000)/100),
            "leagues": player.leagues,
            "games": player.games,
            "wr mod": player.wr_mod,
            "stats": {}
        }

        return player

    @property
    def master_player_list(self):
        for player in self.player_dat:
            yield player

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

    def add_player_to_team(self, ign, team):
        player = self.update_player(ign)
        self.league_dat['teams'][team]['players'][ign] = round(player.wr_mod)

        if self.league_dat['royale']:
            budget = self.league_dat['teams'][team]['budget']
            if budget >= player.wr_mod:
                self.league_dat['teams'][team]['budget'] -= round(player.wr_mod)
                self.save_league()
                return self.league_dat['teams'][team]['budget']
            else:
                print(player.wr_mod-budget, ' PTS TOO EXPENSIVE')
                return 101

    def remove_player_from_team(self, ign, team):
        pts = self.league_dat['teams'][team]['players'][ign]
        del self.league_dat['teams'][team]['players'][ign]

        if self.league_dat['royale']:
            self.league_dat['teams'][team]['budget'] += pts

        self.save_league()

    def sum_team_pts(self, team):
        team_dict = self.league_dat['teams'][team]["players"]
        team_sum = 0
        for player in team_dict:
            team_sum += team_dict[player]

        return team_sum

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
    rc = League("ROYALE COUNCIL")
    rc.add_player_to_team('bobbyzlich', 'x')
    # for t, u in [('yasuomoe', 'x'), ('ipogoz', 'x'), ('nkjukko', 'x'), ('fent bars', 'x'), ('xxda1hpwarriorxx', 'x')]:
    #     rc.add_player_to_team(t, u)


if __name__ == '__main__':
    main()
