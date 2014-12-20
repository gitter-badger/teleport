from __future__ import unicode_literals
from collections import OrderedDict
from datetime import tzinfo, timedelta

from .compat import normalize_string

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


def error(err, loc=None):
    if type(err) == tuple:
        text, location = err
    else:
        text = normalize_string(err)
        if text is None:
            raise TypeError("tuple or string expected as first argument", err)
        location = ()

    if loc is not None:
        location = (loc,) + location

    return text, location


class Impossible(Exception):
    """"""

class ForceReturn(Exception):
    """Not an error, return value from error iterator"""
    def __init__(self, value):
        self.value = value


class Errors(Exception):

    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return format_multiple_errors(list(self))

    def __iter__(self):
        for e in self.errors:
            yield error(e)


class IncorrectErrorGenerator(Exception):
    pass


class ErrorGenerator(object):

    def __init__(self, f):
        setattr(self, 'f', f)

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


