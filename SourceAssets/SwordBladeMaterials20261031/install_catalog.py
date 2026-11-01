"""Merge the blade surface slot without changing existing options or stats."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
OPTIONS=[
    ('folded_steel','折叠纹钢','细密层叠锻纹沿刃面延伸，银灰钢面保留柔和高光。',1),
    ('dark_iron','玄铁','深灰黑金属配细拉丝，刃口呈现克制的银亮反光。',2),
    ('mithril','秘银','银白刃面带细腻纵向纹理，光泽清透而柔和。',3),
]
def update(name,edit):
    path=ROOT/'Content/ColdSteelData'/name
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    backup=P/'Before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    edit(data);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def catalog(d):
    for c in d['columns']:
        if c['key']=='blade_2':c.update(name='符文',default='原厂符文')
    new={'key':'blade_material','name':'剑身材质','default':'原厂材质',
         'description':'保留剑身原有材质与纹理。','weapons':['ue_rune_sword'],
         'options':[{'id':i,'name':n,'description':s,'tier':'common','weapons':['ue_rune_sword'],
                     'effects':[],'stats':{},'special_effects':[]} for i,n,s,_ in OPTIONS]}
    d['columns']=[c for c in d['columns'] if c['key']!='blade_material']
    d['columns'].insert(next(i for i,c in enumerate(d['columns']) if c['key']=='blade_2'),new)
def modules(d):
    d['slots']['blade_material']={'factory':{'mode':0,'appearance':'原有金属与刃面纹理'},
        **{i:{'mode':m,'appearance':s} for i,n,s,m in OPTIONS}}
update('melee-gunsmith.json',catalog)
update('rune-sword-modules.json',modules)
print('BLADE_MATERIAL_CATALOG_SAVED')
