from asyncriothandle import AsyncRequester
# from asyncriothandle import AsyncRequester
import json
import sys
import datetime

# FILE-PATHS FOR THE DATA!!!
LEAGUE_FP = "../json/silverfantasy.json"
GAMES_FP = "../json/soloqgames.json"


# CHECKS TO SEE IF A TIMESTAMP IS WITHIN A WEEK
def recent(raw_timestamp_ms, date=False):

    if date:
        time = datetime.datetime.strptime(raw_timestamp_ms, "%m/%d/%Y")
    else:
        time = datetime.datetime.fromtimestamp(raw_timestamp_ms // 1000)

    week_ago = datetime.datetime.now() - datetime.timedelta(7)  # changed to 8 bc line up with get_recent_soloq_games
    return time.date() >= week_ago.date()


class Updater:
    def __init__(self, request_type: str):
        """open the two json files, creates an AsyncRequester object and take the request type as input"""
        with open(LEAGUE_FP) as f:
            self.league = json.load(f)
        with open(GAMES_FP) as f2:
            self.games = json.load(f2)

        self.ar = AsyncRequester()
        self.request_type = request_type

    def save(self, league=False, games=False):
        """write the instance data in .league or .games to its respective file bu setting it to True"""
        if league:
            with open(LEAGUE_FP, 'w') as f:
                json.dump(self.league, f, indent=4)
                print(f'saved {LEAGUE_FP}')

        if games:
            with open(GAMES_FP, 'w') as f2:
                json.dump(self.games, f2, indent=4)
                print(f'saved {GAMES_FP}')

    def request_summoner(self, args):
        """takes a list of IGN's and requests summoner data for each"""
        id_ar = AsyncRequester()

        for s_ign in args:
            id_ar.sum_dat(s_ign)

        self.ar.__floor__()
        resp = id_ar.run()
        for player in resp:
            self.league["PLAYERS"][player["name"].lower()]['dat'] = player

        self.save(league=True)
        return resp

    def request_ranked(self, args):
        """takes in a list of IGN's and returns season ranked data. may need to get id's - uses [id] aka summoner id"""
        ids_to_request = []
        rank_ar = AsyncRequester()

        for ign in args:
            if ign in self.league["PLAYERS"]:
                rank_ar.ranked(self.league["PLAYERS"][ign]['dat']['id'])
            else:
                self.league["PLAYERS"][ign] = {}
                ids_to_request.append(ign)

        # get id's here if you have to - makes a new async req instance to avoid conflict
        if ids_to_request:
            sum_dat = self.request_summoner(ids_to_request)
            for dat in sum_dat:
                rank_ar.ranked(dat['id'])
                self.league["PLAYERS"][dat['name'].lower()]['dat'] = dat  # go ahead and assign the data locally

        resp = rank_ar.run()
        for ranked_dat in resp:
            for stats in ranked_dat:
                if stats['queueType'] == 'RANKED_SOLO_5x5':
                    player = stats

            c_player = self.league["PLAYERS"][player["summonerName"].lower()]
            c_player["rank"] = player["tier"] + ' ' + player["rank"]
            c_player["inactive"] = player["inactive"]

        self.save(league=True)
        return resp
    
    def request_match_history(self, args):
        """takes in a bunch of summoners and return a bunch of match histories. """
        hist_ar = AsyncRequester()

        for player in args:
            if player in self.games:
                hist_ar.match_history(self.league["PLAYERS"][player]['dat']["accountId"])
            else:
                print('no player!')

        return hist_ar.run()

    def run(self):
        """meat of the class right here. decides on which function to call."""
        args = sys.argv[2:]

        if self.request_type == "summoner":
            return self.request_summoner(args)
        elif self.request_type == "ranked":
            return self.request_ranked(args)
        elif self.request_type == "history":
            return self.request_match_history(args)


if __name__ == "__main__":
    u = Updater(sys.argv[1])  # take first argument as class input
    print('\n\n', u.run())
