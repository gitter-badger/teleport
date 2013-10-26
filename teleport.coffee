_ = require 'underscore'


BasicPrimitive =
  toJson: (datum) ->
    return datum


class ParametrizedPrimitive
  constructor: (@param) ->


Schema = {
  toJson: (datum) -> datum
  fromJson: (datum) ->
    schema = root[datum.type]
    if schema != undefined
      if schema.param_schema != undefined
        param = schema.param_schema.fromJson datum.param
        return schema(param)
      else
        return schema
    throw new Error()
}


Integer = {
  toJson: (datum) -> datum
  fromJson: (datum) ->
    if _.isNumber(datum) and datum % 1 == 0
      return datum
    throw new Error(datum)
}


Float = {
  toJson: (datum) -> datum
  fromJson: (datum) ->
    if _.isNumber(datum)
      return datum
    throw new Error()
}


Boolean = {
  toJson: (datum) -> datum
  fromJson: (datum) ->
    if _.isBoolean(datum)
      return datum
    throw new Error()
}


String = {
  toJson: (datum) -> datum
  fromJson: (datum) ->
    if _.isString(datum)
      return datum
    throw new Error()
}


DateTime = {
  fromJson: (datum) ->
    if _.isString(datum)
      return new Date Date.parse datum
    throw new Error()
  toJson: (datum) ->
    datum.toJSON()
}


Binary = {
  fromJson: (datum) ->
    if _.isString(datum)
      return new Buffer(datum, 'base64').toString 'ascii'
    throw new Error()
  toJson: (datum) ->
    return new Buffer(datum).toString 'base64'
}


JSON = {
  toJson: (datum) -> datum
  fromJson: (datum) -> datum
}


Array = (param) ->
  return {
    fromJson: (datum) ->
      if _.isArray(datum)
        return (@param.fromJson(item) for item in datum)
      throw new Error()
    toJson: (datum) ->
      return @param.toJson(item) for item in datum
  }
Array.param_schema = Schema


Map = (param) ->
  return {
    fromJson: (datum) ->
      if _.isObject datum
        ret = {}
        for key, value of datum
          ret[key] = param.fromJson value
        return ret
      throw new Error()
    toJson: (datum) ->
      ret = {}
      for key, value of datum
        ret[key] = param.toJson value
      return ret
  }
Map.param_schema = Schema


Struct = (param) ->
  return {
    param: param
    toJson: (datum) -> datum
    fromJson: (datum) ->
      if _.isObject datum
        ret = {}
        for key, value of datum
          if key not in param.order
            throw new Error "Unexpected key: #{key}"
        for key, spec of param.map
          if datum[key] != undefined
            ret[key] = spec.schema.fromJson datum[key]
          else if spec.required
            throw new Error "Required key missing: #{key}"
        return ret
      throw new Error()
  }
Struct.param_schema = {
  fromJson: (p) ->
    m = {}
    for k, v of p.map
      m[k] = {
        required: v.required
        schema: Schema.fromJson v.schema
      }
    return {
      order: p.order
      map: m
    }
}


root =
  Schema: Schema
  Integer: Integer
  Float: Float
  Boolean: Boolean
  DateTime: DateTime
  String: String
  Array: Array
  Map: Map
  JSON: JSON
  Binary: Binary
  Struct: Struct


# If no framework is available, just export to the global object (window.HUSL
# in the browser)
@teleport = root unless module? or jQuery? or requirejs?
# Export to Node.js
module.exports = root if module?
# Export to RequireJS
define(root) if requirejs? and define?