import re
import pickle

from teleport import Invalid
from teleport import T as OriginalT


class T(OriginalT):
    pass


@T.register("Color")
class ColorType(object):

    def check(self, t, value):
        if not t("String").check(value):
            return False
        return re.compile('^#[0-9a-f]{6}$').match(value) is not None


@T.register("Nullable")
class NullableType(object):

    def __init__(self, t, param):
        self.child = t(param)

    def deserialize(self, t, value):
        if value is None:
            return None
        return self.child.deserialize(value)

    def serialize(self, t, value):
        if value is None:
            return None
        return self.child.serialize(value)


@T.register("PythonObject")
class PythonObjectType(object):

    def deserialize(self, T, json_value):
        if not T("String").check(json_value):
            raise Invalid("PythonObject must be a string")
        try:
            return pickle.loads(json_value)
        except:
            raise Invalid("PythonObject could not be unpickled")

    def serialize(self, T, native_value):
        return pickle.dumps(native_value)


