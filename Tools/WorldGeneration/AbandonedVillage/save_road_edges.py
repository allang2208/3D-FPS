"""Save the common road mask/material and patch only its two RVT writer branches."""
from pathlib import Path
import hashlib,json,runpy
import unreal as u

root=Path('D:/FPS3D/FPSGAME')
out=root/'Saved/ChapelRoadReview20261115'
base='/Game/WorldGeneration/TemperateHills/'
L,E=u.MaterialEditingLibrary,u.EditorAssetLibrary
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
owned=['AbandonedVillage/T_VillageRoadMask','AbandonedVillage/M_VillageMudRoad',
       'M_TemperateGround','PebbleShore/M_PebbleShoreGround']
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Active play session; preserve it and defer road saves')
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(base+rel for rel in owned):
    raise RuntimeError('Road assets have unsaved editor changes; preserve them')
progress_file=out/'road-save-progress.json'
progress=json.loads(progress_file.read_text(encoding='utf-8-sig')) if progress_file.exists() else {}
def record_saved(rel):
    progress[rel]=sha(root/'Content/WorldGeneration/TemperateHills'/(rel+'.uasset'))
    progress_file.write_text(json.dumps(progress,indent=2),encoding='utf-8')
for rel in owned:
    file=Path('Content/WorldGeneration/TemperateHills')/(rel+'.uasset')
    if sha(root/file)!=progress.get(rel,sha(out/'Before'/file)):raise RuntimeError('Asset changed since backup: '+rel)
plan=json.loads((root/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
if owned[0] not in progress:
    task=u.AssetImportTask();task.filename=str(root/'SourceAssets/TemperateHillsVillage/RoadMask.png')
    task.destination_path=base+'AbandonedVillage';task.destination_name='T_VillageRoadMask'
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mask=u.load_asset(task.destination_path+'/'+task.destination_name)
    mask.srgb=False;mask.compression_settings=u.TextureCompressionSettings.TC_MASKS
    mask.address_x=mask.address_y=u.TextureAddress.TA_CLAMP
    if not E.save_loaded_asset(mask,False):raise RuntimeError('mask save failed')
    record_saved(owned[0])
tools=root/'Tools/WorldGeneration/AbandonedVillage'
if owned[1] not in progress:
    runpy.run_path(str(tools/'village_road_material.py'))['build'](plan)
    record_saved(owned[1])
edge=runpy.run_path(str(tools/'village_road_blend.py'))

def one(values,label):
    if len(values)!=1:raise RuntimeError(label+' expected one, found '+str(len(values)))
    return values[0]

for name in ['M_TemperateGround','PebbleShore/M_PebbleShoreGround']:
    if name in progress:continue
    mat=u.load_asset(base+name)
    expressions=L.get_material_expressions(mat)
    customs=[n for n in expressions if isinstance(n,u.MaterialExpressionCustom)]
    coverage=one([n for n in customs if n.get_editor_property('code')=='return max(M.r,M.g*(.62+.38*H))*all(UV>=0)*all(UV<=1);'],name+' coverage')
    roadway=one([n for n in customs if n.get_editor_property('code')=='return saturate(M.r/max(.0001,A));'],name+' roadway')
    uv=one([n for n in customs if n.get_editor_property('code').startswith('return .5+XY/float2(')],name+' local UV')
    samples=[n for n in expressions if isinstance(n,u.MaterialExpressionTextureSample) and n.texture]
    mask_node=one([n for n in samples if n.texture.get_name()=='T_VillageRoadMask'],name+' mask')
    height=one([n for n in samples if n.texture.get_name()=='T_ChapelEarth_H'],name+' earth height')
    mat.modify()
    weights=edge['build_weights'](mat,mask_node,uv,height,[v*200 for v in plan['extent_m']])
    def rewrite(node,code,inputs):
        node.set_editor_property('code',code)
        pins=[]
        for key in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
        node.set_editor_property('inputs',pins)
        for key,source in inputs.items():
            if not L.connect_material_expressions(source,'',node,key):raise RuntimeError('RVT road '+key)
    rewrite(coverage,'return max(W.x,W.y);',{'W':weights})
    rewrite(roadway,'return saturate(W.x/max(.0001,A));',{'W':weights,'A':coverage})
    L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('ground save '+name)
    record_saved(name)

receipt={'saved':[],'road_edge_fade_cm':110,'road_edge_breakup_cm':48,
         'coverage':'All roads and door approaches through common mask; visible decal and dry RVT share one function'}
for rel in owned:
    file=Path('Content/WorldGeneration/TemperateHills')/(rel+'.uasset')
    receipt['saved'].append({'asset':base+rel,'before':sha(out/'Before'/file),'after':sha(root/file)})
(out/'road-assets-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('ROAD_EDGES_SAVED '+str(out/'road-assets-saved.json'))
