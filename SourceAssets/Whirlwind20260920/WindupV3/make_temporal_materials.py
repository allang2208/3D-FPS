"""Build skill-only foreground materials; originals remain untouched.

TemporalResponsiveness is 1 only on these copies, used during Whirlwind.
Requires r.Velocity.TemporalResponsiveness.Supported=1 at editor/game startup.
"""
import hashlib
import json
from pathlib import Path
import unreal as u

P=Path(__file__).parent
DATA=P.parents[2]/'Content'/'ColdSteelData'
FOLDER='/Game/Skills/Whirlwind20260920/ForegroundV3'
L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
L.make_directory(FOLDER)
sources={};visited=set();mapping={}

def collect_material(mat):
    if mat:sources[mat.get_path_name()]=mat

def collect_asset(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing equipped foreground source: '+path)
    if isinstance(asset,u.MaterialInterface):collect_material(asset)
    elif isinstance(asset,u.SkeletalMesh):
        for slot in asset.get_editor_property('materials'):collect_material(slot.material_interface)
    elif isinstance(asset,u.StaticMesh):
        for slot in asset.get_editor_property('static_materials'):collect_material(slot.material_interface)

def walk(value):
    if isinstance(value,dict):
        for key,child in value.items():
            if key in ('mesh','arms_mesh') and isinstance(child,str):collect_asset(child)
            elif key=='materials' and isinstance(child,dict):
                for path in child.values():collect_asset(path)
            elif key=='library' and isinstance(child,str):catalog(child)
            else:walk(child)
    elif isinstance(value,list):
        for child in value:walk(child)

def catalog(name):
    if name in visited:return
    visited.add(name);walk(json.loads((DATA/name).read_text(encoding='utf-8-sig')))

for name in ('rune-sword-modules.json','frost-sword-modules.json'):catalog(name)
collect_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
collect_asset('/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2')

def clone(source):
    key=source.get_path_name()
    if key in mapping:return u.load_asset(mapping[key])
    name=source.get_name()+'_'+hashlib.sha1(key.encode()).hexdigest()[:8]+'_WhirlwindV3'
    target=FOLDER+'/'+name
    if L.does_asset_exist(target):
        result=u.load_asset(target)
        if L.get_metadata_tag(result,'Whirlwind.TemporalSource')!=key:
            raise RuntimeError('Preserve existing unowned material: '+target)
    else:
        result=L.duplicate_asset(key,target)
        if not result:raise RuntimeError('Material duplication failed: '+key)
        if isinstance(source,u.MaterialInstanceConstant):
            M.set_material_instance_parent(result,clone(source.get_editor_property('parent')))
            M.update_material_instance(result)
        elif isinstance(source,u.Material):
            output=M.create_material_expression(result,u.MaterialExpressionTemporalResponsivenessOutput,-700,-700)
            value=M.create_material_expression(result,u.MaterialExpressionConstant,-950,-700)
            value.set_editor_property('r',1.0)
            if not M.connect_material_expressions(value,'',output,''):
                raise RuntimeError('Temporal output connection failed: '+key)
            errors=M.recompile_material(result)
            if errors:raise RuntimeError('\n'.join(errors))
        else:raise RuntimeError('Unsupported persistent foreground material: '+key)
        # Finish the required material shader build before saving, without PIE.
        M.get_statistics(result)
        L.set_metadata_tag(result,'Whirlwind.TemporalSource',key)
        if not L.save_loaded_asset(result,False):raise RuntimeError('Material save failed: '+target)
    mapping[key]=result.get_path_name()
    (P/'temporal_material_receipt.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
    return result

for key in sorted(sources):clone(sources[key])
(DATA/'whirlwind-temporal-materials.json').write_text(json.dumps(mapping,indent=2)+'\n',encoding='utf-8')
u.log('WHIRLWIND_FOREGROUND_SAVED '+str(len(mapping)))
