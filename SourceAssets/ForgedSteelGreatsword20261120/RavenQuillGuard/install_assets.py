"""Import Raven Quill's static cosmetics and both fitted meshes in the FPSGAME commandlet."""
import json
import runpy
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
FINISH_ART = HERE/'Art'/'ReliefV3'
ART = HERE/'Art'/'NestedV4'
MODS = HERE.parent/'CommonMods'
ROOT = '/Game/Weapons/ForgedSteelGreatsword20261120/RavenQuillGuard'
FINISH_FOLDER = ROOT+'/ReliefV3'
FOLDER = ROOT+'/NestedV4'
WING = 'M_RavenQuill_ForgedMetal'
E,L = u.EditorAssetLibrary,u.MaterialEditingLibrary
active = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if active != PROJECT or '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Use the background FPSGAME Python commandlet')
imp = runpy.run_path(str(MODS/'install_legendary_blade.py'))['import_asset']
graph = runpy.run_path(str(PROJECT/'SourceAssets/KukriRefinement20261027/hanging_material.py'))
node,wire,out = (graph[k] for k in ('node','link','out'))
assets=[]

def save(obj):
    if not E.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())
    assets.append(obj.get_path_name())

def texture(tag,compression):
    name='T_RavenQuill_'+tag
    tex=imp(FINISH_ART/(name+'.png'),FINISH_FOLDER,name)
    tex.set_editor_properties({'srgb':tag=='BaseColor','compression_settings':compression,'lod_group':u.TextureGroup.TEXTUREGROUP_WEAPON})
    if tag=='Normal':
        tex.set_editor_property('flip_green_channel',True)
    save(tex)
    return tex

def wing_material(maps,temporal=False):
    name=WING+('_Whirlwind' if temporal else '')
    mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,FINISH_FOLDER,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_properties({'used_with_nanite':True,'tangent_space_normal':True,'two_sided':False})
    sm=u.MaterialSamplerType
    samples={k:node(mat,u.MaterialExpressionTextureSample,texture=maps[k],sampler_type=sampler) for k,sampler in
             (('BaseColor',sm.SAMPLERTYPE_COLOR),('Normal',sm.SAMPLERTYPE_NORMAL),('ORM',sm.SAMPLERTYPE_MASKS))}
    front=node(mat,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for tag,ch,pin,prop in (('BaseColor','RGB','BaseColor','BASE_COLOR'),('Normal','RGB','Normal','NORMAL'),
                            ('ORM','G','Roughness','ROUGHNESS'),('ORM','B','Metallic','METALLIC')):
        wire(samples[tag],ch,front,pin)
        out(samples[tag],ch,getattr(u.MaterialProperty,'MP_'+prop))
    out(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    out(front,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    if temporal:
        response=node(mat,u.MaterialExpressionTemporalResponsivenessOutput)
        one=node(mat,u.MaterialExpressionConstant,r=1.)
        if not L.connect_material_expressions(one,'',response,''):
            raise RuntimeError('Could not wire temporal response')
    L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors: raise RuntimeError(str(errors))
    save(mat)
    return mat

def reference_finishes():
    # Both charge variants share these texture packages. Refresh them even when
    # the normal and Whirlwind material graphs already exist from an earlier import.
    maps={tag:texture(tag,compression) for tag,compression in (
        ('BaseColor',u.TextureCompressionSettings.TC_DEFAULT),
        ('Normal',u.TextureCompressionSettings.TC_NORMALMAP),
        ('ORM',u.TextureCompressionSettings.TC_MASKS))}
    mats=[]
    for suffix in ('','_Whirlwind'):
        path=FINISH_FOLDER+'/'+WING+suffix
        if E.does_asset_exist(path):
            mats.append(u.load_asset(path))
            continue
        mats.append(wing_material(maps,bool(suffix)))
    return mats

normal,whirlwind=reference_finishes()
seat_path=json.loads((MODS/'blade_materials.json').read_text(encoding='utf8'))['base']
surfaces={'M_ForgedSteelGreatsword_Surface_V1':u.load_asset(seat_path),WING:normal}
if any(not t for t in surfaces.values()):raise RuntimeError('Missing fitted blade-seat surface')
for slot,base_material in surfaces.copy().items():
    charge_path=ROOT+'/SprintCharge/'+base_material.get_name()
    if E.does_asset_exist(charge_path):
        surfaces[slot]=u.load_asset(charge_path)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI()
opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True
opt.import_as_skeletal=opt.import_materials=opt.import_animations=opt.import_textures=False
settings=opt.static_mesh_import_data
settings.combine_meshes=settings.build_nanite=True
settings.generate_lightmap_u_vs=settings.auto_generate_collision=False
settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
settings.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
meshes={}
for name,source in json.loads((ART/'exports.json').read_text(encoding='utf8')).items():
    mesh=imp(ART/(name+'.fbx'),FOLDER,name,opt)
    slots=[str(slot.material_slot_name) for slot in mesh.static_materials]
    if set(slots)!=set(surfaces):raise RuntimeError('Unexpected imported slots: '+str(slots))
    for i,slot in enumerate(slots):mesh.set_material(i,surfaces[slot])
    nanite=mesh.get_editor_property('nanite_settings')
    nanite.enabled=nanite.explicit_tangents=True
    # Carry the high relief in Nanite. Keep the previous fallback budget.
    nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    nanite.fallback_percent_triangles=min(1.,54000/source['triangles'])
    mesh.set_editor_property('nanite_settings',nanite)
    save(mesh)
    meshes[name]=dict(zip(slots,[mesh.get_material(i).get_path_name() for i in range(len(slots))]))
cards=runpy.run_path(str(MODS/'install_stock_icons.py'))['install_cards']
key='guard_raven_quill_guard'
icon='/Game/ColdSteelData/AttachmentIcons20260913/ue_forged_steel_greatsword_'+key
if not E.does_asset_exist(icon):
    assets.extend(cards({key:key}))
receipt={'assets':assets,'meshes':meshes,'temporal':{normal.get_path_name():whirlwind.get_path_name()}}
(ART/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print('RAVEN_QUILL_SAVED',len(assets))
