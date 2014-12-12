from unittest2 import TestCase
from datetime import datetime

from teleport import T, utc, Invalid, ValidationError
from teleport.compat import PY2

t = T


class SimpleTest(object):
    pairs = []
    undefined = []

    def test_deserialize(self):
        for pair in self.pairs:
            self.assertEqual(t(self.schema).deserialize(pair[0]), pair[1])

    def test_serialize(self):
        for pair in self.pairs:
            self.assertEqual(t(self.schema).serialize(pair[1]), pair[0])


ds = '2013-10-18T01:58:24.904349Z'
dn = datetime(2013, 10, 18, 1, 58, 24, 904349, tzinfo=utc)


class IntegerTest(SimpleTest, TestCase):
    schema = "Integer"
    pairs = [(1, 1)]

    if PY2:
        pairs.append((long(1), long(1)))




class DecimalTest(SimpleTest, TestCase):
    schema = "Decimal"
    pairs = [(0.1, 0.1), (1e10, 1e10)]


class StringTest(SimpleTest, TestCase):
    schema = "String"
    pairs = [(u"lol", u"lol")]


class BooleanTest(SimpleTest, TestCase):
    schema = "Boolean"
    pairs = [(True, True), (False, False)]


class DateTimeTest(SimpleTest, TestCase):
    schema = "DateTime"
    pairs = [(ds, dn)]


class JSONTest(SimpleTest, TestCase):
    schema = "JSON"
    o = object()
    pairs = [(o, o)]


class SchemaTest(SimpleTest, TestCase):
    schema = "Schema"
    pairs = [(u'Integer', u'Integer')]


class ArrayTest(SimpleTest, TestCase):
    schema = {"Array": "DateTime"}
    pairs = [([ds, ds], [dn, dn])]


class MapTest(SimpleTest, TestCase):
    schema = {"Map": "DateTime"}
    pairs = [({"a": ds, "b": ds}, {"a": dn, "b": dn})]


class StructTest(SimpleTest, TestCase):
    schema = {"Struct": {
        "required": {"a": "DateTime"},
        "optional": {"b": "Integer"}}}
    pairs = [({"a": ds, "b": 1}, {"a": dn, "b": 1}), ({"a": ds}, {"a": dn})]




class ErrorTest(TestCase):

    def setUp(self):
        self.t = t({"Struct": {
            "optional": {},
            "required": {
                "name": "String",
                "tags": {"Array": "String"}}}})

    def test_errors(self):

        try:
            self.t.deserialize({
                "tags": ["a", True],
                "lol": 1
            })
        except ValidationError as m:
            pass
            """
            import pdb; pdb.set_trace()
            self.assertEqual(m.serialize(), [
                {"error": ["MissingField", "name"], "pointer": []},
                {"error": ["UnexpectedField", "lol"], "pointer": []},
                {"error": [], "pointer": ["tags", 1]}
            ])
            self.assertEqual([OrderedDict([(u'message', u'Missing field: "name"'), (u'pointer', [])]), OrderedDict([(u'message', u'Unexpected field: "lol"'), (u'pointer', [])]), OrderedDict([(u'message', u'Not a string'), (u'pointer', ['tags', 1])])])
            """
