"""Publish the forged sword's five grip meshes with dedicated metal, leather and textile."""
from pathlib import Path
import json
import runpy
import unreal as u

HERE=Path(__file__).resolve().parent
ART=HERE/'Art'
MODS=HERE.parent/'CommonMods'
ROOT='/Game/Weapons/ForgedSteelGreatsword20261120'
FOLDER=ROOT+'/GripFinish'
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=HERE.parents[2] or '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Run this authoring script in the FPSGAME background commandlet')
import_asset=runpy.run_path(str(MODS/'install_legendary_blade.py'))['import_asset']
assets=[]
def save(obj):
    if not E.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())
    assets.append(obj.get_path_name())

materials={}
properties={}
for kind in ('Leather','Steel','Textile'):
    maps={}
    for channel,compression in [('BaseColor',u.TextureCompressionSettings.TC_DEFAULT),('Normal',u.TextureCompressionSettings.TC_NORMALMAP),('Roughness',u.TextureCompressionSettings.TC_MASKS)]:
        tag=kind+'_'+channel
        tex=import_asset(ART/(tag+'.png'),FOLDER,'T_ForgedGrip_'+tag)
        tex.set_editor_properties({'srgb':channel=='BaseColor','compression_settings':compression,'lod_group':u.TextureGroup.TEXTUREGROUP_WEAPON})
        if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
        save(tex);maps[channel]=tex
    # Keep the original dry and rainy Substrate graphs, replace their sampled PBR maps.
    slot='M_SharedGrip_'+kind
    path=FOLDER+'/M_ForgedGrip_'+kind
    mat=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/SharedSwordGrips20260927/Materials/'+slot,path)
    if not mat:raise RuntimeError('Missing source surface '+slot)
    mat.set_editor_property('used_with_nanite',True)
    used=set()
    for sample in L.get_material_expressions(mat):
        if not isinstance(sample,u.MaterialExpressionTextureSample) or not sample.texture:continue
        for channel,tex in maps.items():
            if sample.texture.get_name() in ('T_SharedGrip_'+kind+'_'+channel,tex.get_name()):
                sample.set_editor_property('texture',tex)
                used.add(channel)
    if used!=set(maps):raise RuntimeError('Incomplete PBR bindings on '+path+': '+str(used))
    if not L.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Missing Substrate output on '+path)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat);materials[slot]=mat
    properties[slot]={'name':mat.get_path_name(),'maps':{k:v.get_path_name() for k,v in maps.items()},'nanite':mat.get_editor_property('used_with_nanite')}
factory_slot='M_ForgedSteelGreatsword_Surface_V1'
materials[factory_slot]=u.load_asset(ROOT+'/V1/Materials/'+factory_slot)
u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI()
opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True
opt.import_as_skeletal=opt.import_textures=opt.import_materials=opt.import_animations=False
fb=opt.static_mesh_import_data
fb.combine_meshes=fb.build_nanite=True
fb.auto_generate_collision=fb.generate_lightmap_u_vs=False
fb.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
fb.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
bindings={}
for row in json.loads((ART/'grip_exports.json').read_text(encoding='utf8'))['options']:
    name=row['mesh']
    obj=import_asset(ART/'Export'/(name+'.fbx'),FOLDER,name,opt)
    slots=[str(slot.material_slot_name) for slot in obj.static_materials]
    if factory_slot not in slots or 'M_SharedGrip_Leather' not in slots:raise RuntimeError('Missing grip wrap or original collar: '+name)
    for i,slot in enumerate(slots):
        obj.set_material(i,materials[slot])
    nanite=obj.get_editor_property('nanite_settings')
    nanite.enabled=nanite.explicit_tangents=True
    nanite.fallback_relative_error=0
    obj.set_editor_property('nanite_settings',nanite)
    save(obj)
    bindings[row['option']]={'mesh':obj.get_path_name(),'material_slot_names':slots,
                             'materials':{slot:obj.get_material(i).get_path_name() for i,slot in enumerate(slots)}}
(ART/'import_receipt.json').write_text(json.dumps({'assets':assets,'surfaces':properties,'grips':bindings},indent=2)+'\n',encoding='utf8')
print('FORGED_GRIPS_SAVED',len(assets),list(bindings))
