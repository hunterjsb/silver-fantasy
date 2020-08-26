import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")  # WAIT IM NOT SURE IF THIS WORKS
HEADERS = {"X-Riot-Token": TOKEN}


class AsyncRequester:
    """class used to both create the API request URL and asynchronously send it to riot"""
    t_req = 0

    def __init__(self):
        self.requests = []
        self.error = None  # not even used
        self.c_req = 0
        self.region = 'na1'

    def __set_name__(self, owner, name):
        self.name = name

    def __iter__(self):
        """"return iterable of request URL's"""
        return iter(self.requests)

    def __lt__(self, val):
        """less than compare number of requests between two AsyncRequester's or an integer"""
        return self.c_req < val

    def __le__(self, val):
        """less than or equal to compare number of requests between two AsyncRequester's or an integer"""
        return self.c_req <= val

    def __gt__(self, val):
        """greater than compare number of requests between two AsyncRequester's or an integer"""
        return self.c_req > val

    def __ge__(self, val):
        """greater than or equal to compare number of requests between two AsyncRequester's or an integer"""
        return self.c_req >= val

    def __eq__(self, reqs):
        """check if two request queries are equal"""
        return self.requests == reqs

    def __add__(self, reqs):
        """returns new AsyncRequester with both sets of requests combined
        ex: if list1 has a, b, c and list2 has a, e... list1 + list2 = a, b, c, a, e"""
        new_reqs = self.requests + reqs.requests
        new_ar = AsyncRequester()
        new_ar.set_requests(new_reqs)
        return new_ar

    def __sub__(self, reqs):
        """returns new AsyncRequester. the requests are the uncommon elements of both lists.
        ex: if list1 has a, b, c and list2 has a, e... list1 - list2 = b, c, e
        ex: if list1 has a, a, b, c, c and list2 has a, e... list1 - list2 = b, c, e
        ex: if list1 has a, e and list2 has a, b, c... list1 - list2 = e, b, c"""
        new_ar = AsyncRequester()

        new_reqs = list(list(set(self.requests) - set(reqs)) + list(set(reqs) - set(self.requests)))
        new_ar.set_requests(new_reqs)
        return new_ar

    def __truediv__(self, reqs):
        """returns new AsyncRequester. the requests are the uncommon elements of the first list.
        ex: if list1 has a, b, c and list2 has a, e... list1 / list2 = b, c,
        ex: if list1 has a, a, b, c, c and list2 has a, e... list1 / list2 = b, c, c
        ex: if list1 has a, e and list2 has a, b, c... list1 / list2 = e"""
        new_reqs = []
        new_ar = AsyncRequester()

        for _ in self.requests:
            if _ not in reqs:
                new_reqs.append(_)

        new_ar.set_requests(new_reqs)
        return new_ar

    def __and__(self, reqs):
        """return common elements without copies.
        ex: if list1 has a, b, c and list2 has a, e... list1 & list2 = a"""
        return self - (self / reqs)

    def __floor__(self):
        """removes duplicates from list"""
        return list(dict.fromkeys(self.requests))

    def __repr__(self):
        return f'{type(self)}\n{self.c_req} REQUESTS: {self.requests}'

    def _add_request(self, req):
        self.requests.append(req)
        self.c_req += 1

    def set_requests(self, reqs):
        self.c_req = len(reqs)
        self.requests = reqs

    async def _make_request(self, endpoint, session):
        async with session.get(endpoint, headers=HEADERS) as resp:
            AsyncRequester.t_req += 1
            print(AsyncRequester.t_req, ' | ', endpoint, ' | ', resp.status)
            return await resp.json()

    async def do(self):
        tasks = []
        print(f'total requests: {AsyncRequester.t_req} ({self.c_req} new)')

        async with aiohttp.ClientSession() as session:
            for req in self.requests:
                task = asyncio.ensure_future(self._make_request(req, session))
                tasks.append(task)

            responses = await asyncio.gather(*tasks)
            self.requests = []  # ADD THIS TO MASTER!
            return responses

    def run(self):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.do())

    def sum_id(self, ign):
        assert isinstance(ign, str)
        self._add_request(f'https://{self.region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{ign}')

    def ranked(self, s_id):
        assert isinstance(s_id, int)
        self._add_request(f'https://{self.region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{s_id}')

    def match_history(self, s_id):
        assert isinstance(s_id, str)
        self._add_request(f"https://{self.region}.api.riotgames.com/lol/match/v4/matchlists/by-account/{s_id}")

    def match(self, m_id):
        assert isinstance(m_id, int)
        self._add_request(f'https://{self.region}.api.riotgames.com/lol/match/v4/matches/{m_id}')


if __name__ == '__main__':
    ar = AsyncRequester()
    ar.sum_id('ipogoz')
    ar.sum_id('ipogoz')
    ar.sum_id('durkledingus')
    ar.sum_id('black xan bible')
    ar.sum_id('black xan bible')

    ar2 = AsyncRequester()
    ar2.sum_id('ipogoz')
    ar2.sum_id('yasuomoe')

    ar3 = ar & ar2
    print(ar.__floor__())
