"""Install the bounded wet-forest material layers; save only owned packages."""
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME');BATCH=ROOT/'SourceAssets/HillsWetForest20261111'
spec=importlib.util.spec_from_file_location('forest_wet_materials',ROOT/'Tools/WorldGeneration/forest_wet_materials.py')
wet=importlib.util.module_from_spec(spec);spec.loader.exec_module(wet)
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
BASE='/Game/WorldGeneration/TemperateHills'
POND=BASE+'/WetForest/M_ForestPond'
paths=[wet.MPC,BASE+'/Grass/M_TemperateMeadow',BASE+'/M_TemperateGround',
    BASE+'/PebbleShore/M_PebbleShoreGround','/Game/Fluids/RiverPilot20260923/M_RiverPilot',POND,wet.GRASS_MPC]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):raise RuntimeError('Preserve unsaved target assets: '+str(dirty.intersection(paths)))
stamp=datetime.now().strftime('%Y%m%d-%H%M%S');report={'saved':[],'map_saved':False,'backups':[]}
for path in paths:
    source=ROOT/'Content'/(path[6:]+'.uasset')
    if source.is_file():
        target=BATCH/'Backups'/('Assets-'+stamp)/(path[6:]+'.uasset');target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target);report['backups'].append(str(target))
def save(obj):
    if isinstance(obj,u.Material):
        errors=L.recompile_material(obj)
        if errors:raise RuntimeError('Material compile request failed: '+str(errors))
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
    report['saved'].append(obj.get_path_name())
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj

save(wet.ensure_collection())
save(wet.ensure_collection(wet.GRASS_MPC))
grass=load(paths[1]);wet.apply_grass(grass);save(grass)
for path in paths[2:4]:
    ground=load(path);wet.apply_ground(ground);save(ground)
river=load(paths[4]);wet.apply_water(river);save(river)
pond=load(POND) if E.does_asset_exist(POND) else E.duplicate_asset(paths[4],POND)
if not pond:raise RuntimeError('Cannot create local pond material')
# Retain the native optical/interaction graph. Shallow pools have no stream foam,
# no surface displacement and very small wind waves; their level comes from the plan.
for n in L.get_material_expressions(pond):
    tag=str(n.get_editor_property('desc'))
    if isinstance(n,u.MaterialExpressionScalarParameter):
        name=str(n.get_editor_property('parameter_name'))
        values={'NativeWaveScale':.065,'NativeCausticStrength':.065,'NativePhaseG':.65}
        if name in values:n.set_editor_property('default_value',values[name])
    if isinstance(n,u.MaterialExpressionVectorParameter):
        name=str(n.get_editor_property('parameter_name'))
        values={'NativeScatteringPerCm':(.0009,.0010,.0006,0),'NativeAbsorptionPerCm':(.0040,.0036,.0062,0)}
        if name in values:n.set_editor_property('default_value',u.LinearColor(*values[name]))
    if isinstance(n,u.MaterialExpressionCustom) and tag=='NativeWater20260926.Foam':n.set_editor_property('code','return 0;')
    if isinstance(n,u.MaterialExpressionCustom) and tag=='NativeWater20260926.Roughness':n.set_editor_property('code','return lerp(.10,.18,smoothstep(1500,10000,length(P-Cam)));')
vertex=wet.node(pond,u.MaterialExpressionVertexColor,'PoolShoreCoverage')
wet.connect(pond,'OPACITY_MASK',(vertex,'R'))
pond.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
pond.set_editor_property('opacity_mask_clip_value',.015)
E.set_metadata_tag(pond,'NativeWater.Profile','forest_pool')
wet.apply_water(pond);save(pond)
report['finished_at']=datetime.now().astimezone().isoformat()
(BATCH/'Receipts/assets-authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('HILLS_WET_ASSETS_SAVED '+str(len(report['saved'])))
