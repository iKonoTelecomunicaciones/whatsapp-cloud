import time

from cachetools import TTLCache

from .config import Config


class CacheManager(TTLCache):
    """
    A cache manager that extends TTLCache to include configuration management.
    This class provides a way to manage cached items with a time-to-live (TTL) while also
    allowing access to a configuration object.

    Parameters
    ----------
    cache_type : str
        A string indicating the type of cache (e.g., "user", "portal", "puppet"). This can be used
        to apply different configurations based on the cache type.
    config : Config
        A configuration object that contains settings for the cache, such as max size and TTL.
    getsizeof : callable, optional
        A function that takes a cache item and returns its size. This is used to determine the
        size of items in the cache for eviction purposes. If not provided, all items are considered
        to have a size of 1.
    """

    config: Config

    def __init__(self, cache_type: str, config: Config, timer=time.monotonic, getsizeof=None):
        self.config = config
        ttl = self.config["cache.ttl"]
        maxsize = self.config[f"cache.{cache_type}_max_size"]
        super().__init__(maxsize=maxsize, ttl=ttl, timer=timer, getsizeof=getsizeof)

    def get_item(self, key):
        """
        Get an item from the cache and reset its TTL.

        Parameters
        ----------
        key : hashable
            The key of the item to retrieve from the cache.

        Returns
        -------
        The value associated with the key if it exists in the cache, or None if the key is not found.
        """
        try:
            item = super().__getitem__(key)
        except KeyError:
            return None

        # Re-setting the item in TTLCache automatically resets its TTL
        self[key] = item
        return item
