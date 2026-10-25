import shutil,sys
from workwear_common import *
for f in ('Inputs','Before','Authored','SaveInputs','Exports','Textures','Logs','Hat/Authored','Hat/Exports','Hat/Textures'):(R/f).mkdir(parents=True,exist_ok=True)
if (R/'inputs.json').exists():
    baseline=read(R/'Before/modular_outfits.json');current=read(P/'Content/ColdSteelData/modular_outfits.json')
    for live,old in ((current['items'],baseline['items']),(current['body_variants']['kaitlin']['items'],baseline['body_variants']['kaitlin']['items'])):
        if {k for k,v in live.items() if v.get('slot')==15}!={k for k,v in old.items() if v.get('slot')==15}:raise RuntimeError('New trousers require a new native workwear waist production revision')
        for key,value in old.items():
            if value.get('slot')!=15:continue
            if any(live[key].get(field)!=value.get(field) for field in ('rig_meshes','shoe_fit_meshes')):raise RuntimeError('Refresh the measured waist source in a new production revision: '+key)
    print('WORKWEAR_FROZEN_INPUTS_REUSED');sys.exit(0)
c=read(P/'Content/ColdSteelData/modular_outfits.json');b=read(P/'Content/ColdSteelData/player_body.json');items=read(P/'Content/ColdSteelData/items.json')
for f in ('items.json','modular_outfits.json','player_body.json','source-combat-items.json'):shutil.copy2(P/'Content/ColdSteelData'/f,R/'Before'/f)
for profile in ('Jason','Body'):
    shutil.copy2(P/'SourceAssets/FieldRangerTop20261020/CollarRepair20261021/Before'/(profile+'.json'),R/'Before'/(profile+'.json'))
shutil.copy2(P/'SourceAssets/FieldHat20261019/native_head_jason.json',R/'Hat/native_head_jason.json')
shutil.copy2(P/'SourceAssets/FieldWorkSetDesign20261024/field-work-set-concept-v1.png',R/'Inputs/approved-concept.png')
groups=read(P/'SourceAssets/PantsCompatibility20261022/authored.json')
records={}
for ident,row in groups['groups'].items():
    target=R/'Inputs'/('waist-'+ident+'.json');shutil.copy2(row['guide'],target);records[ident]=dict(row,guide=str(target))
ident='leather_v3';target=R/'Inputs'/('waist-'+ident+'.json');shutil.copy2(P/'SourceAssets/RangerLeatherPants20261021/RealisticCutV3/Authored/ue_leather_pants/Jason.json',target)
records[ident]=dict(guide=str(target),waist_top_cm=99.7,items=['ue_leather_pants'])
routes=groups['routes']
for row in routes.values():
    if row.get('reused'):row['signature']='leather_v3'
# Exact current paths (including the newer ST6 detail revision) inherit only
# the corresponding trousers' measured waist, never a guessed global scale.
item_group={item:g for g,row in records.items() for item in row['items']}
for item,recipe in c['items'].items():
    if recipe.get('slot')!=15:continue
    for path in [recipe['rig_meshes']['Jason']]+[v['Jason'] for v in recipe.get('shoe_fit_meshes',{}).values()]:
        routes[path]=dict(item=item,signature=item_group[item])
write(R/'inputs.json',dict(jason_recipe=c['items']['ue_field_sweater'],kaitlin_recipe=c['body_variants']['kaitlin']['items']['ue_field_sweater'],head=b['head_equipment']['ue_field_hat'],female_head=b['body_variants']['kaitlin']['head_equipment']['ue_field_hat'],groups=records,routes=routes,items={k:items[k] for k in ('ue_field_sweater','ue_field_hat','ue_cargo_pants','ue_boots','ue_original_gloves')},concept='approved-concept.png'))
print('WORKWEAR_INPUTS_PREPARED',len(records),len(routes))
