import asyncio
import aiohttp
import os

# load_dotenv()
# TOKEN = os.getenv("RIOT_TOKEN")  # WAIT IM NOT SURE IF THIS WORKS
HEADERS = {"X-Riot-Token": "RGAPI-9ac67d68-c7fc-4185-a79a-9c1897985cde"}


# COLORS! for console printing
class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class AsyncRequester:
    """class used to both create the API request URL and asynchronously send it to riot"""
    t_req = 0

    def __init__(self, init_req=None):
        if init_req:
            self.c_req = len(init_req)
            self.set_requests(init_req)
        else:
            self.requests = []
            self.c_req = 0

        self.error = None  # not even used
        self.region = 'na1'

    def __floor__(self):
        """removes duplicates from list"""
        self.requests = list(dict.fromkeys(self.requests))
        self.c_req = len(self.requests)
        return self

    def __repr__(self):
        return f'{type(self)}\n{self.c_req} REQUESTS: {self.requests}'

    def __mod__(self, size: int):
        chunks = [self.requests[x:x+size] for x in range(0, len(self.requests), size)]
        return chunks

    def _add_request(self, req):
        self.requests.append(req)
        self.c_req += 1

    def set_requests(self, reqs):
        self.c_req = len(reqs)
        self.requests = reqs

    @staticmethod
    def _add_queries(endpoint: str, queries: dict):
        i = 0
        for k, v in queries.items():
            i += 1
            c = "?" if i < 2 else "&"
            endpoint += f"{c}{k}={v}"

        return endpoint

    async def _make_request(self, endpoint, session):
        async with session.get(endpoint, headers=HEADERS) as s_resp:
            AsyncRequester.t_req += 1
            self.c_req -= 1

            status = s_resp.status
            color = BColors.OKGREEN if status == 200 else BColors.FAIL
            print(f'{color}{AsyncRequester().t_req}{BColors.ENDC} | {BColors.UNDERLINE}{endpoint}{BColors.ENDC} | '
                  f'{color}{s_resp.status}{BColors.ENDC}')
            # print(AsyncRequester.t_req, ' | ', endpoint, ' | ', s_resp.status)
            return await s_resp.json()

    async def _gather_requests(self):
        tasks = []
        print(f'{BColors.HEADER}requests made: {AsyncRequester.t_req} ({self.c_req} pending{BColors.ENDC})')

        async with aiohttp.ClientSession() as session:
            for req in self.requests:
                task = asyncio.ensure_future(self._make_request(req, session))
                tasks.append(task)

            responses = await asyncio.gather(*tasks)
            self.requests = []
            return responses

    def run(self):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._gather_requests())

    def sum_dat(self, ign: str):
        self._add_request(f'https://{self.region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{ign}')

    def ranked(self, s_id: int):
        self._add_request(f'https://{self.region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{s_id}')

    def match_history(self, s_id: str, queries=None):
        endpoint = f"https://{self.region}.api.riotgames.com/lol/match/v4/matchlists/by-account/{s_id}"
        if queries:
            endpoint = self._add_queries(endpoint, queries)
        
        self._add_request(endpoint)

    def match(self, m_id: int):
        self._add_request(f'https://{self.region}.api.riotgames.com/lol/match/v4/matches/{m_id}')

    def dummy(self, name):
        self._add_request(name)


if __name__ == '__main__':
    ar = AsyncRequester()
    ar.sum_dat('ipogoz')
    ar.sum_dat('black xan bible')
    resp = ar.run()

    print(resp[0])
