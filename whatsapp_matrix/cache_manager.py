import time

from cachetools import TTLCache

from .config import Config


class CacheManager(TTLCache):
    config: Config

    def __init__(self, maxsize, ttl, config, timer=time.monotonic, getsizeof=None):
        super().__init__(maxsize=maxsize, ttl=ttl, timer=timer, getsizeof=getsizeof)
        self.config = config

    def get_item(self, key):
        try:
            item = super().__getitem__(key)
        except KeyError:
            return None

        # Re-setting the item in TTLCache automatically resets its TTL
        self[key] = item
        return item
