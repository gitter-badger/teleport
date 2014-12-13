from __future__ import unicode_literals

from datetime import tzinfo, timedelta
import itertools


class UTC(tzinfo):
    """Why is this not in the standard library?
    """
    ZERO = timedelta(0)

    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO

    def __repr__(self):
        return '<UTC>'

utc = UTC()


def ghetto_json_pointer(tup):
    return '/' + '/'.join(map(str, tup))


def format_multiple_errors(errors):
    ret = "\n"
    for message, location in errors:
        pointer = ghetto_json_pointer(location)

        ret += pointer
        if len(pointer) < 10:
            ret += ' ' * (10 - len(pointer))
        ret += message + '\n'
    return ret


class ForceReturn(Exception):
    """Not an error, return value from error iterator"""
    def __init__(self, value):
        self.value = value


class IterableError(Exception):

    def __iter__(self):
        yield self


class Errors(IterableError):

    def __init__(self, generator):
        self.generator = generator

    def __iter__(self):
        return self.generator


class IncorrectErrorGenerator(Exception):
    pass


class ErrorGenerator(object):

    def __init__(self, f):
        self.f = f

    def __call__(self, *args, **kwargs):
        try:
            gen = getattr(self, 'f')(*args, **kwargs)
            try:
                err = next(gen)
            except StopIteration:
                raise IncorrectErrorGenerator(
                    "No errors generated and no value returned")
            raise Errors(itertools.chain([err], gen))

        except ForceReturn as ret:
            return ret.value


