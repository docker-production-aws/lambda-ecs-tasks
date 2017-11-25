from voluptuous import Required, All, Range, Schema, Length

def ToInt(value):
  if isinstance(value, int):
    return value
  if isinstance(value, basestring) and value.isdigit():
    return int(value)
  else:
    raise ValueError

def ToBool(value):
  if isinstance(value, bool):
    return value
  if isinstance(value, basestring) and value.lower() in ['true','yes']:
    return True
  if isinstance(value, basestring) and value.lower() in ['false','no']:
    return False
  else:
    raise ValueError

def DictToString(value):
  def string_values(node):
    if type(node) is dict:
      result={}
      for k,v in node.iteritems():
        result[k] = string_values(v)
    elif type(node) is list:
      result=[]
      for v in node:
        result.append(string_values(v))
    else:
      result = str(node)
    return result
  if isinstance(value, dict):
    return string_values(value)
  else:
    raise ValueError

def get_validator():
  return Schema({
    Required('Cluster'): All(basestring),
    Required('TaskDefinition'): All(basestring),
    Required('Count', default=1): All(ToInt, Range(min=0, max=10)),
    Required('RunOnUpdate', default=True): All(ToBool),
    Required('Instances', default=list()): All(list, Length(max=10)),
    Required('Overrides', default=dict()): All(DictToString),
    Required('Timeout', default=3600): All(ToInt, Range(min=60, max=3600))
  }, extra=True)

def validate(data):
  request_validator = get_validator()
  return request_validator(data)