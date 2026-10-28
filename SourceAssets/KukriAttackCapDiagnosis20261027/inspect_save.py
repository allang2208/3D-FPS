"""Read selected tagged SaveGame fields only; never load or write a live profile."""
import json, struct
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
class Reader:
    def __init__(self,data):self.data=data;self.pos=0
    def take(self,n):
        out=self.data[self.pos:self.pos+n]
        if len(out)!=n:raise ValueError('Truncated property payload')
        self.pos+=n;return out
    def integer(self):return struct.unpack('<i',self.take(4))[0]
    def string(self):
        n=self.integer()
        if not n:return ''
        return self.take(-n*2).decode('utf-16-le').rstrip('\0') if n<0 else self.take(n).decode('utf-8',errors='replace').rstrip('\0')
    def typename(self):
        name=self.string();count=self.integer()
        return name,[self.typename() for _ in range(count)]
    def fields(self):
        out={}
        while True:
            name=self.string()
            if name=='None':return out
            typ=self.typename();size=self.integer();flags=self.take(1)[0]
            if flags&1:self.take(4)
            if flags&2:self.take(16)
            if flags&4:raise ValueError('Extended property: '+name)
            out[name]=(typ,self.take(size),flags)

def value(tag):
    (kind,args),data,flags=tag;r=Reader(data)
    if kind in ('NameProperty','StrProperty'):return r.string()
    if kind=='IntProperty':return r.integer()
    if kind=='Int64Property':return struct.unpack('<q',data)[0]
    if kind=='FloatProperty':return struct.unpack('<f',data)[0]
    if kind=='BoolProperty':return bool(flags&16)
    return None

save=ROOT/'Saved/SaveGames/ColdSteelPlayer_PIE_0_B.sav'
data=save.read_bytes()
offset=data.index(struct.pack('<i',8)+b'Profile\0')
root=Reader(data[offset:]).fields()['Profile']
fields=Reader(root[1]).fields()
attrs=Reader(fields['Attributes'][1]);removed=attrs.integer();count=attrs.integer()
attributes={}
for _ in range(count):
    key=attrs.string();attributes[key]=attrs.integer()
skills=Reader(fields['Skills'][1]);removed=skills.integer();count=skills.integer()
levels={}
for _ in range(count):
    key=skills.string();levels[key]=value(skills.fields()['Level'])
items=Reader(fields['Items'][1]);count=items.integer();equipped=[]
for _ in range(count):
    props=items.fields()
    if value(props['Place'])!=1:continue
    record={key:value(props[key]) for key in ('InstanceId','Definition','Place','Cell','Data')}
    record['Data']=json.loads(record['Data'])
    equipped.append(record)
report={'save':str(save),'active_weapon_slot':value(fields['ActiveWeaponSlot']),
        'attributes':attributes,'skill_levels':levels,'equipped':equipped,
        'survival':{k:value(v) for k,v in Reader(fields['Survival'][1]).fields().items()},
        'infection':{k:value(v) for k,v in Reader(fields['Infection'][1]).fields().items()} if 'Infection' in fields else {}}
(P/'saved-profile-readout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({**report,'equipped':[{**e,'Data':{k:v for k,v in e['Data'].items() if k in
    ('id','bonusStats','bonusPerEnhance','enhanceLevel','_enchantEffects','_craftEffects','gunsmith_parts','attack_seconds')}} for e in equipped]},ensure_ascii=False,indent=2))
