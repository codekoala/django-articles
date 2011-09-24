import functools
import logging
import time

log = logging.getLogger('articles.decorators')

def logtime(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if func.__class__.__name__ == 'function':
            executing = '%s.%s' % (func.__module__, func.__name__)
        elif 'method' in func.__class__.__name__:
            executing = '%s.%s.%s' % (func.__module__, func.__class__.__name__, func.__name__)
        else:
            executing = str(func)

        log.debug('Logging execution time for %s with args: %s; kwargs: %s' % (executing, args, kwargs))

        start = time.time()
        res = func(*args, **kwargs)
        duration = time.time() - start

        log.debug('Called %s... duration: %s seconds' % (executing, duration))
        return res

    return wrapped

def once_per_instance(func):
    """Makes it so an instance method is called at most once before saving"""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        if not hasattr(self, '__run_once_methods'):
            self.__run_once_methods = []

        name = func.__name__
        if name in self.__run_once_methods:
            log.debug('Method %s has already been called for %s... not calling again.' % (name, self))
            return False

        res = func(self, *args, **kwargs)

        self.__run_once_methods.append(name)
        return res

    return wrapped

