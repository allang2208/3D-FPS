"""Copy the live blade material graph; replace only the guard's wing material."""
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[3]
D='/Game/Weapons/HighlandClaymore20260922/ClovenSurface20261002/BladeMetal'
SOURCE='/Game/Weapons/HighlandClaymore20260922/Materials/M_HighlandClaymoreSurface'
DEST=D+'/M_HighlandBladeMetal_Cloven20261002'
L,E,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
catalog=json.loads((ROOT/'Content/ColdSteelData/highland-claymore-modules.json').read_text(encoding='utf-8-sig'))
target=catalog['slots']['guard']['highland_cloven_guard']['mesh']
blade_path=catalog['slots']['blade_1']['factory']['mesh']
mesh=u.load_asset(target)
blade=u.load_asset(blade_path)
source=u.load_asset(SOURCE)
if not mesh or not blade or not source:
    raise RuntimeError('Current blade material or cloven mesh is missing')
if not any(s.material_interface==source for s in blade.static_materials):
    raise RuntimeError('Current blade uses a different metal source; preserve the active assets')
if os.environ.get('CLOVEN_HEADLESS')!='1':
    dirty=u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    if any(p.get_path_name()==mesh.get_outer().get_path_name() for p in dirty):
        raise RuntimeError('Current guard has unsaved mesh edits; preserve them before replacement')
index=next((i for i,s in enumerate(mesh.static_materials) if str(s.material_slot_name)=='M_ClovenWingSurface20261002'),None)
if index is None:
    raise RuntimeError('Accepted arc-UV wing slot is missing')
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
before=P/'Before'/stamp
before.mkdir(parents=True,exist_ok=True)
disk=ROOT/'Content'/(target.split('.')[0].removeprefix('/Game/')+'.uasset')
for suffix in ['.uasset','.uexp','.ubulk']:
    old=disk.with_suffix(suffix)
    if old.exists():shutil.copy2(old,before/old.name)
receipt={'revision':'BladeMetal_20261002','target':target,'source_material':source.get_path_name(),
    'old_wing_material':mesh.get_material(index).get_path_name(),'assets':[],
    'backup':str(before),'geometry_reimported':False,'complete':False,'tested':False}

def record():
    (P/'install_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')

def save(asset):
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append({'asset':asset.get_path_name(),'saved':True})
    record()

textures={}
for key in ['BaseColor','Normal','Metallic','Roughness']:
    name='T_ClovenBladeMetal_'+key
    texture=u.load_asset(D+'/Textures/'+name)
    if texture is None:
        task=u.AssetImportTask()
        task.filename=str(P/'Textures'/(name+'.png'))
        task.destination_path=D+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False
        A.import_asset_tasks([task])
        texture=u.load_asset(D+'/Textures/'+name)
        if not texture or not task.imported_object_paths:raise RuntimeError('Texture import failed: '+name)
        texture.set_editor_property('srgb',key=='BaseColor')
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else
            u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if key=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
        texture.set_editor_property('max_texture_size',2048)
        if key=='Normal':texture.set_editor_property('flip_green_channel',True)
        save(texture)
    textures[key]=texture
material=u.load_asset(DEST)
if material is None:
    material=L.duplicate_asset(SOURCE,DEST)
    if not material:raise RuntimeError('Could not copy the current blade material')
if L.get_metadata_tag(material,'ClovenSurfaceRevision')!='BladeMetal_20261002':
    replaced={}
    for node in E.get_material_expressions(material):
        if not isinstance(node,u.MaterialExpressionTextureSample):continue
        old=node.get_editor_property('texture')
        if not old:continue
        for key,texture in textures.items():
            if old.get_name() in ['T_Highland_'+key,'T_ClovenBladeMetal_'+key]:
                node.set_editor_property('texture',texture)
                replaced[key]=texture.get_path_name()
    if set(replaced)!=set(textures):
        raise RuntimeError('Blade PBR texture inputs differ from the authoring source: '+str(replaced))
    errors=list(E.recompile_material(material) or [])
    if errors:raise RuntimeError('Blade-metal material compilation failed: '+str(errors))
    L.set_metadata_tag(material,'ClovenSurfaceRevision','BladeMetal_20261002')
    L.set_metadata_tag(material,'ClovenMaterialSource',SOURCE)
    save(material)
    receipt['texture_inputs']=replaced
mesh.set_material(index,material)
L.set_metadata_tag(mesh,'ClovenSurfaceRevision','BladeMetal_20261002')
save(mesh)
receipt.update(complete=True,material=material.get_path_name(),
    materials={str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials})
record()
print('CLOVEN_BLADE_METAL_INSTALL_COMPLETE '+target)
