"""Scoped local release of the authored concept-fidelity garment revision."""
import json,copy,sys,os,uuid,hashlib,shutil,ast
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR2';D=P/'Content/ColdSteelData';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR2'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
tree=ast.parse((P/'Tools/ModernTacticalSet/shirt_publish.py').read_text(encoding='utf-8'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='transaction'],type_ignores=[]),'scoped_combat_release','exec'))
saved=read(R/'saved.json');authored=read(R/'authored.json');art=read(R/'artwork-saved.json');mapping={};pants={}
if not saved.get('completed') or not art.get('completed'):raise RuntimeError('Save every authored asset before release')
for row in authored['rows']:
    record=saved['wear'][row['asset']]
    if record['sha256']!=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest():raise RuntimeError('Unsaved garment change '+row['file'])
    if row.get('source'):mapping[row['source']]=record['asset']
    else:pants[row['rig']+'/'+row['kind']]=record['asset']
def substitute(value):
    if isinstance(value,dict):return {k:substitute(v) for k,v in value.items()}
    if isinstance(value,list):return [substitute(v) for v in value]
    return mapping.get(value,value) if isinstance(value,str) else value
snapshot=read(P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR1/Inputs/modular_outfits.json');current=read(D/'modular_outfits.json');V='ue_modern_kevlar_vest';T='ue_modern_tactical_pants';B='ue_modern_tactical_boots';edits=[]
for prefix,rig,source in [(['items'],'Jason',snapshot),(['body_variants','kaitlin','items'],'Kaitlin',snapshot['body_variants']['kaitlin'])]:
    items=current
    for key in prefix:items=items[key]
    shirt=substitute(copy.deepcopy(source['items']['ue_st6_sleeves']));shirt.update(appearance_family='TS01CombatConcept20261114',first_person_mode='native_sleeves',wear_mode='tucked_combat_shirt_with_carrier',pants_fit_pipeline='Tools/ModernTacticalSet/combat2_assemble.py',waist_fit_revision='TS01CombatShirtR2-native-waist',world_covers=[0,1,3,8,9],base_material_overrides={})
    # The legacy Body viewmodel keeps its own native-material fallback. Jason
    # and Kaitlin use the complete authored garment and retained neck patch.
    shirt['base_material_overrides']['Body']={'0':saved['materials']['CombatRipstop'],'1':saved['materials']['CombatRipstop'],'3':saved['materials']['CombatStretch']}
    recipe=copy.deepcopy(items[T]);old_default=recipe['rig_meshes'][rig];replacements={old_default:pants[rig+'/pants']};recipe['rig_meshes'][rig]=pants[rig+'/pants']
    for shoe,fit in recipe.get('shoe_fit_meshes',{}).items():
        old=fit[rig];kind='pants_tactical' if shoe==B else 'pants_short' if shoe=='ue_boots' else 'pants_boot' if shoe=='ue_st6_tactical_boots' else 'pants_high';new=pants[rig+'/'+kind];fit[rig]=new
        if shoe!=B:replacements[old]=new
        else:
            modern_old=old;modern_new=new
    recipe['appearance_family']='TS01CombatConcept20261114';edits.append((prefix+[T],recipe))
    for old,new in [*replacements.items(),(modern_old,modern_new)]:
        fit=shirt.get('pants_mesh_fit_meshes',{}).get(old,shirt['pants_fit_meshes'][T]);shirt['pants_mesh_fit_meshes'][new]=copy.deepcopy(fit)
        for key,value in items.items():
            if key==V or value.get('slot')!=7:continue
            oldfit=value.get('pants_mesh_fit_meshes',{}).get(old)
            if oldfit is not None:edits.append((prefix+[key,'pants_mesh_fit_meshes',new],copy.deepcopy(oldfit)))
    edits.append((prefix+[V],shirt))
transaction(D/'modular_outfits.json',edits)
catalog=read(D/'items.json');transaction(D/'items.json',[([V,'desc'],'土棕色凯夫拉防弹衣搭配长袖作战上衣。防撕裂袖片、深棕弹力躯干、贴臂袖袋和护肘，领袖与下摆带实体回折及双排针脚，后摆扎入裤腰。'),([V,'world_mesh'],art['pickup']),([V,'ue_equipment_icon_mesh'],art['display']),([T,'world_mesh'],art['pants_pickup']),([T,'ue_equipment_icon_mesh'],art['pants_display'])])
for item,filename in [(V,'artwork.json'),(T,'lower-artwork.json')]:
    png=read(R/filename)['icon']['png']
    for destination in [D/catalog[item]['ue_icon'],D/'Icons'/(item+'.png')]:
        tmp=destination.with_suffix('.'+uuid.uuid4().hex+'.tmp');shutil.copyfile(png,tmp);os.replace(tmp,destination)
transaction(P/'Tools/GarmentWaist/policies.json',[(['shirts',V],dict(mode='tuck',producer='Tools/ModernTacticalSet/combat2_assemble.py',source_root='SourceAssets/ModernTacticalSet20261113/CombatShirtR2',requires_native_waist_refresh=True,outer_slots={'Jason':[0,1,2,3,4],'Owner_Jason':[0,1,2,3,4]},outer_carrier_preserved=True))])
(R/'published.json').write_text(json.dumps(dict(completed=True,wear_assets=len(authored['rows']),pants=pants,artwork=art,inventory_granted=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8');print('TS01_COMBAT2_PUBLISHED',flush=True)
