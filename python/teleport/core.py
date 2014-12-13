from __future__ import unicode_literals

import json
import pyrfc3339
from collections import OrderedDict, namedtuple
from functools import partial

from .compat import test_integer, test_long, normalize_string
from .util import utc, format_multiple_errors, ErrorGenerator, ForceReturn, Errors, IterableError


Implementation = namedtuple("Implementation", [
    'param', 'check', 'serialize', 'deserialize'])

BoundImplementation = namedtuple("Implementation", [
    'check', 'serialize', 'deserialize'])


def partial2(f, *args, **kwargs):
    if f is None:
        return None
    return partial(f, *args, **kwargs)


def implementation_from_class(T, type_cls):
    props = dict(type_cls.__dict__)

    imp = Implementation(
        param=type_cls,
        check=props.get('check', None),
        serialize=props.get('serialize', None),
        deserialize=props.get('deserialize', None))

    if '__init__' not in props:
        inst = type_cls()

        return BoundImplementation(
            check=partial2(imp.check, inst, T),
            serialize=partial2(imp.serialize, inst, T),
            deserialize=partial2(imp.deserialize, inst, T))

    return imp


def bind_generic(imp, T, json_param):
    param = imp.param(T, json_param)
    return BoundImplementation(
        check=partial2(imp.check, param, T),
        serialize=partial2(imp.serialize, param, T),
        deserialize=partial2(imp.deserialize, param, T))


class Invalid(IterableError):

    def __init__(self, message, location=()):
        self.message = message
        self.location = location

    def serialize(self):
        return OrderedDict([
            ("message", self.message),
            ("pointer", list(self.location))
        ])

    def prepend_location(self, item):
        return self.__class__(self.message, (item,) + self.location)


class ValidationError(Invalid):

    def __init__(self, exceptions):
        self.exceptions = exceptions

    def serialize(self):
        return [e.serialize() for e in self.exceptions]

    def __str__(self):
        tups = [(e.message, e.location) for e in self.exceptions]
        return format_multiple_errors(tups)


class T(object):
    """Conceptually, an instance of this class is a value space, a set of
    JSON values. As such, the only method defined by the Teleport specification
    is :meth:`check`, everything else is extentions made by this
    implementation.

    """

    types = {}

    def __init__(self, schema):
        """When you call the :func:`t` function, you are actually calling this
        method. You will rarely want to override this directly.

        :param schema: a JSON value
        :return: a :class:`~teleport.Type` instance

        """
        s = normalize_string(schema)

        if s is not None:
            imp = self.__class__.get_type_or_fail(s)
            if type(imp) != BoundImplementation:
                raise Invalid("Not a concrete type: \"{}\"".format(s))

            self.imp = imp

        elif type(schema) == dict and len(schema) == 1:
            name = list(schema)[0]
            param = schema[name]
            imp = self.__class__.get_type_or_fail(name)

            if type(imp) != Implementation:
                raise Invalid("Not a generic type: \"{}\"".format(name))

            self.imp = bind_generic(imp, self.__class__, param)

        else:
            raise Invalid("Unrecognized schema {}".format(schema))

    @classmethod
    def get_type_or_fail(cls, name):
        type_cls = cls.types.get(name, None)
        if type_cls is None:
            type_cls = cls.get_type_hook(name)
        if type_cls is None:
            raise Invalid("Unknown type {}".format(name))
        return type_cls

    @classmethod
    def get_type_hook(cls, name):
        """Override this method to enapble dynamic type search. It gets called
        if the requested type is neither a core type nor a type added by
        :meth:`register`. In that case, this is the last resort before
        :exc:`~teleport.core.Invalid` is thrown.

        :param name: a string
        :return: a subclass of :class:`~teleport.Type` or None
        """
        return None

    @classmethod
    def register(cls, name):
        """Used as a decorator to add a type to the type map.

        .. code-block:: python

            @t.register("Truth")
            class TruthType(object):
                def check(self, value):
                    return value is True
        """
        def decorator(type_cls):
            cls.types[name] = implementation_from_class(cls, type_cls)
            return type_cls
        return decorator

    def check(self, json_value):
        """
        Returns :data:`True` if *json_value* is a member of this type's value
        space and :data:`False` if it is not.

        .. code-block:: python

            >>> t("DateTime").check(u"2015-04-05T14:30")
            True
            >>> t("DateTime").check(u"2007-04-05T14:30 DROP TABLE users;")
            False
        """
        if self.imp.check:
            return self.imp.check(json_value)
        elif self.imp.deserialize:
            try:
                self.imp.deserialize(json_value)
                return True
            except Invalid:
                return False
        else:
            raise NotImplementedError("check or deserialize necessary")

    def deserialize(self, json_value):
        """Raises :exc:`~teleport.Invalid`, returns *native value*.

        Convert JSON value to native value. Raises :exc:`Invalid` if
        *json_value* is not a member of this type. By default, this method
        returns the JSON value unchanged.

        .. code-block:: python

            >>> t("DateTime").deserialize(u"2015-04-05T14:30")
            datetime.datetime(2015, 4, 5, 14, 30)
        """
        if self.imp.deserialize:
            return self.imp.deserialize(json_value)
        elif self.imp.check:
            if self.imp.check(json_value):
                return json_value
            else:
                raise Invalid("Invalid whatever it is")
        else:
            raise NotImplementedError()

    def serialize(self, native_value):
        """Convert valid native value to JSON value. By default, this method
        returns the native value unchanged, assuming that it is already in
        the format expected by the :mod:`json` module.

        .. code-block:: python

            >>> t("DateTime").serialize(datetime.datetime(2015, 4, 5, 14, 30))
            u"2015-04-05T14:30"


        """
        if self.imp.serialize:
            return self.imp.serialize(native_value)
        else:
            return native_value


@T.register("Array")
class ArrayType(object):

    def __init__(self, T, param):
        self.space = T(param)

    @ErrorGenerator
    def deserialize(self, T, json_value):
        if type(json_value) != list:
            yield Invalid("Must be list")
            return

        fail = False
        arr = []
        for i, item in enumerate(json_value):
            try:
                arr.append(self.space.deserialize(item))
            except IterableError as errs:
                fail = True
                for err in errs:
                    yield err.prepend_location(i)

        if not fail:
            raise ForceReturn(arr)

    def serialize(self, T, value):
        return list(map(self.space.serialize, value))


@T.register("Map")
class MapType(object):

    def __init__(self, T, param):
        self.space = T(param)

    @ErrorGenerator
    def deserialize(self, T, json_value):

        if type(json_value) != dict:
            yield Invalid("Must be dict")
            return

        fail = False
        m = {}
        for key, val in json_value.items():
            try:
                m[key] = self.space.deserialize(val)
            except IterableError as errs:
                fail = True
                for err in errs:
                    yield err.prepend_location(key)

        if not fail:
            raise ForceReturn(m)

    def serialize(self, T, value):
        ret = {}
        for key, val in value.items():
            ret[key] = self.space.serialize(val)

        return ret


@T.register("Struct")
class StructType(object):

    def __init__(self, T, param):
        expected = {'required', 'optional'}

        if type(param) != dict or not expected.issubset(set(param.keys())):
            raise Invalid("Boom")

        self.schemas = {}
        for kind in expected:
            if type(param[kind]) != dict:
                raise Invalid("Bang")

            for k, s in param[kind].items():
                self.schemas[k] = T(s)

        self.opt = set(param['optional'].keys())
        self.req = set(param['required'].keys())

        if not self.opt.isdisjoint(self.req):
            raise Invalid("Hwoah")

    @ErrorGenerator
    def deserialize(self, T, json_value):

        if type(json_value) != dict:
            yield Invalid("Dict expected")
            return

        fail = False

        for k in self.req:
            if k not in json_value:
                fail = True
                yield Invalid("Missing field: {}".format(json.dumps(k)))

        for k in json_value.keys():
            if k not in self.schemas.keys():
                fail = True
                yield Invalid("Unexpected field: {}".format(json.dumps(k)))

        struct = {}
        for k, v in json_value.items():
            if k not in self.schemas.keys():
                continue

            try:
                struct[k] = self.schemas[k].deserialize(v)
            except IterableError as errs:
                fail = True
                for err in errs:
                    yield err.prepend_location(k)

        if not fail:
            raise ForceReturn(struct)

    def serialize(self, T, value):
        ret = {}
        for k, v in value.items():
            ret[k] = self.schemas[k].serialize(v)

        return ret


@T.register("JSON")
class JSONType(object):
    def check(self, T, value):
        return True


@T.register("Integer")
class IntegerType(object):
    def check(self, T, value):
        return test_integer(value)


@T.register("Decimal")
class DecimalType(object):
    def check(self, T, value):
        return test_long(value)


@T.register("String")
class StringType(object):

    def deserialize(self, T, value):
        s = normalize_string(value)
        if s is not None:
            return s
        raise Invalid("Not a string")


@T.register("Boolean")
class BooleanType(object):
    def check(self, T, value):
        return type(value) == bool


@T.register("DateTime")
class DateTimeType(object):

    def deserialize(self, T, value):
        try:
            return pyrfc3339.parse(value)
        except (TypeError, ValueError):
            raise Invalid("Invalid DateTime")

    def serialize(self, T, value):
        return pyrfc3339.generate(value, accept_naive=True, microseconds=True)


@T.register("Schema")
class SchemaType(object):

    def check(self, T, value):
        try:
            T(value)
            return True
        except Invalid:
            return False
