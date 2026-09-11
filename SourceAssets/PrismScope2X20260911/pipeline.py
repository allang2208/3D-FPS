import json,urllib.request
BASE="http://192.168.3.142:8188"
def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=60))
def defaults(info,name):
    result={}
    for k,v in info[name]['input']['required'].items():
        if len(v)>1 and 'default' in v[1]: result[k]=v[1]['default']
        elif isinstance(v[0],list): result[k]=v[0][0]
    return result
