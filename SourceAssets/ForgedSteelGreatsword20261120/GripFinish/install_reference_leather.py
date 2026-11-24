"""Install the warm grained leather on the stock grip and five dedicated alternatives."""
import json
import runpy
from pathlib import Path
import unreal as u

HERE=Path(__file__).resolve().parent
ART=HERE/'Art/ReferenceLeather'
PROJECT=HERE.parents[2]
if Path(u.Paths.project_dir()).resolve()!=PROJECT or '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Use the background FPSGAME commandlet')
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
imp=runpy.run_path(str(HERE.parent/'CommonMods/install_legendary_blade.py'))['import_asset']
old=json.loads((HERE/'Art/import_receipt.json').read_text(encoding='utf8'))
root='/Game/Weapons/ForgedSteelGreatsword20261120'
folder=root+'/GripFinish/ReferenceLeather'
leather_slot='M_SharedGrip_Leather'
assets=[]
def save(obj):
    if not obj or not E.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+str(obj))
    assets.append(obj.get_path_name())

def derivative(source,dest):
    existing=u.load_asset(dest) if E.does_asset_exist(dest) else E.duplicate_asset(source,dest)
    if not existing: raise RuntimeError('Could not create '+dest)
    return existing

maps={}
for tag,mode in [('BaseColor',u.TextureCompressionSettings.TC_DEFAULT),('Normal',u.TextureCompressionSettings.TC_NORMALMAP),('Roughness',u.TextureCompressionSettings.TC_MASKS)]:
    name='T_ForgedGrip_Leather_'+tag
    tex=imp(ART/('Leather_'+tag+'.png'),folder,name)
    tex.set_editor_properties({'srgb':tag=='BaseColor','compression_settings':mode,'lod_group':u.TextureGroup.TEXTUREGROUP_WEAPON})
    if tag=='Normal':tex.set_editor_property('flip_green_channel',True)
    save(tex);maps[name]=tex
mat=derivative(old['surfaces'][leather_slot]['name'],folder+'/M_ForgedGrip_Leather')
bound=set()
for node in L.get_material_expressions(mat):
    if not isinstance(node,u.MaterialExpressionTextureSample) or not node.texture:continue
    name=node.texture.get_name()
    if name in maps:
        node.set_editor_property('texture',maps[name]);bound.add(name)
if bound!=set(maps):raise RuntimeError('Missing leather maps: '+str(set(maps)-bound))
mat.set_editor_property('used_with_nanite',True)
if L.recompile_material(mat):raise RuntimeError('Leather graph compilation failed')
save(mat)
obj_name='SM_ForgedSteelGreatsword_Grip_FactoryLeather'
u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI()
opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True
opt.import_as_skeletal=opt.import_materials=opt.import_textures=opt.import_animations=False
fb=opt.static_mesh_import_data
fb.combine_meshes=fb.build_nanite=True
fb.generate_lightmap_u_vs=fb.auto_generate_collision=False
fb.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
fb.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
factory=imp(ART/(obj_name+'.fbx'),folder,obj_name,opt)
binding={}
def bind(option,mesh,preserved):
    slots=[str(s.material_slot_name) for s in mesh.static_materials]
    if leather_slot not in slots:raise RuntimeError('Missing leather material on '+option)
    for i,slot in enumerate(slots):
        surf=mat if slot==leather_slot else u.load_asset(preserved[slot])
        if not surf:raise RuntimeError('Missing preserved fitting '+slot)
        mesh.set_material(i,surf)
    settings=mesh.get_editor_property('nanite_settings')
    settings.enabled=settings.explicit_tangents=True
    mesh.set_editor_property('nanite_settings',settings)
    save(mesh)
    binding[option]={'mesh':mesh.get_path_name(),'material_slot_names':slots,
                     'materials':{slot:mesh.get_material(i).get_path_name() for i,slot in enumerate(slots)}}

stock='M_ForgedSteelGreatsword_Surface_V1'
bind('factory',factory,{stock:root+'/V1/Materials/'+stock})
for option,part in old['grips'].items():
    source=part['mesh']
    bind(option,derivative(source,folder+'/'+source.rsplit('.',1)[1]),part['materials'])
(ART/'import_receipt.json').write_text(json.dumps({'assets':assets,'grips':binding},indent=2)+'\n',encoding='utf8')
print('REFERENCE_LEATHER_SAVED',len(assets),list(binding))
