"""Stage V1 geometry with refined 4K skin materials, preserving current gameplay."""
import json,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ZombieDogFineSkinV3')
DEST='/Game/Monsters/ZombieDog/FineSkinV3'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
def duplicate(source,name):
    path=DEST+'/'+name
    return u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(source,path)
textures={}
for semantic in ['BaseColor','ORM','Opacity','Normal']:
    name='T_ZombieDog_FineSkin_'+semantic;path=DEST+'/Textures/'+name
    tex=u.load_asset(path) if LIB.does_asset_exist(path) else None
    if tex is None:
        task=u.AssetImportTask();task.filename=str(ROOT/'Textures'/(name+'.png'))
        task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.save=True
        TOOLS.import_asset_tasks([task]);tex=u.load_asset(path)
        if tex is None:raise RuntimeError('Texture import failed: '+semantic)
        tex.set_editor_property('srgb',semantic=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if semantic=='Normal' else
            u.TextureCompressionSettings.TC_DEFAULT if semantic=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        save(tex)
    textures[semantic]=tex
materials={}
for role,parent_name in [('Skin','M_ZombieDog_Skin'),('Fur','M_ZombieDog_RemainingFur')]:
    name='MI_ZombieDog_Fine'+role;path=DEST+'/'+name
    material=u.load_asset(path) if LIB.does_asset_exist(path) else None
    if material is None:
        material=TOOLS.create_asset(name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    if LIB.get_metadata_tag(material,'ZombieDog.FineSkin')!='3':
        MEL.set_material_instance_parent(material,u.load_asset('/Game/Monsters/ZombieDog/V1/Materials/'+parent_name))
        for semantic,tex in textures.items():
            # UE 5.8's implementation performs the write but always returns false.
            MEL.set_material_instance_texture_parameter_value(material,semantic,tex)
        LIB.set_metadata_tag(material,'ZombieDog.FineSkin','3')
        MEL.update_material_instance(material);save(material)
    materials[role]=material

# No mesh roundtrip: reuse V1 geometry, binding, UV and material sections directly.
mesh=duplicate('/Game/Monsters/ZombieDog/V1/SK_ZombieDog','SK_ZombieDog_FineSkin')
if LIB.get_metadata_tag(mesh,'ZombieDog.FineSkin')!='3':
    slots=mesh.get_editor_property('materials')
    for i,slot in enumerate(slots):
        slot.material_interface=materials['Fur' if 'Fur' in str(slot.material_slot_name) else 'Skin']
        slots[i]=slot
    mesh.set_editor_property('materials',slots)
    LIB.set_metadata_tag(mesh,'ZombieDog.FineSkin','3');save(mesh)
bp=u.load_asset('/Game/Monsters/ZombieDog/V1/BP_ZombieDog')
active_set=u.get_default_object(bp.generated_class()).get_editor_property('animation_set')
dataset=duplicate(active_set.get_path_name(),'DA_ZombieDog_FineSkin')
if LIB.get_metadata_tag(dataset,'ZombieDog.FineSkin')!='3':
    dataset.set_editor_property('reference_mesh',mesh)
    LIB.remove_metadata_tag(dataset,'ZombieDog.SkinOnly')
    LIB.set_metadata_tag(dataset,'ZombieDog.FineSkin','3');save(dataset)
(ROOT/'ue_import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'dataset':dataset.get_path_name(),
    'materials':{k:v.get_path_name() for k,v in materials.items()},'gameplay_source':active_set.get_path_name(),
    'blueprint_switched':False,'runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
u.log('ZOMBIE_DOG_FINE_SKIN_IMPORTED')
