from datetime import time

from cachetools import TTLCache

from .config import Config


class CacheManager(TTLCache):
    config: Config

    def __init__(self, maxsize, ttl, config, timer=time.monotonic, getsizeof=None):
        super().__init__(maxsize=maxsize, ttl=ttl, timer=timer, getsizeof=getsizeof)
        self.config = config

    def set_item(self, key, value):
        ttl = self.config["cache.ttl"]

        try:
            link = self.__getlink(key)
        except KeyError:
            return

        if link is None:
            return

        # Adjust the internal expiration timer
        link.expire = self.timer() + ttl

        # Add the item to the cache and delete the expired items
        super().__setitem__(key, value)

    def get_item(self, key):
        try:
            item = super().__getitem__(key)
        except KeyError:
            return None

        self.set_item(key, item)
        return item
