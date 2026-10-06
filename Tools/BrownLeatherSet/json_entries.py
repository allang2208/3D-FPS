"""Scoped JSON object entry publication helpers; preserve unrelated file text."""
import json
decoder=json.JSONDecoder()
def ws(text,start):
    while text[start].isspace():start+=1
    return start

def span(text,path):
    start=ws(text,0)
    for key in path:
        pos=ws(text,start+1);found=False
        while text[pos]!='}':
            candidate,end=decoder.raw_decode(text,pos);pos=ws(text,end);pos=ws(text,pos+1)
            _,end=decoder.raw_decode(text,pos)
            if candidate==key:start=pos;found=True;break
            pos=ws(text,end)
            if text[pos]==',':pos=ws(text,pos+1)
        if not found:raise KeyError(path)
    _,end=decoder.raw_decode(text,start);return start,end

def replace(text,path,value):
    start,end=span(text,path);line=text.rfind('\n',0,start)+1;indent=len(text[line:start])-len(text[line:start].lstrip())
    lines=json.dumps(value,ensure_ascii=False,indent=2).splitlines();replacement=lines[0]+''.join('\n'+' '*indent+x for x in lines[1:])
    return text[:start]+replacement+text[end:]

def insert(text,path,key,value):
    start,_=span(text,path);line=text.rfind('\n',0,start)+1;indent=len(text[line:start])-len(text[line:start].lstrip())+2
    entry=json.dumps({key:value},ensure_ascii=False,indent=2).splitlines()[1:-1]
    addition='\n'+'\n'.join(' '*(indent-2)+x for x in entry)+','
    return text[:start+1]+addition+text[start+1:]
