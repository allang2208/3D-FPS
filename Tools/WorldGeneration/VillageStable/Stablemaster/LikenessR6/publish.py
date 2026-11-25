"""Save the rebuilt head as its own asset and change the placed stablemaster's existing head template."""
from pathlib import Path
import json,hashlib,shutil
import unreal as u
P=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
S=P/'SourceAssets/HillsVillageStable/StablemasterLikenessR6'
base='/Game/WorldGeneration/TemperateHills/VillageStable/'
old=base+'StablemasterMeshyR3'
out=base+'StablemasterLikenessR6'
E=u.EditorAssetLibrary;T=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
def get(p):
    ob=E.load_asset(p)
    if not ob:raise RuntimeError('Missing '+p)
    return ob
def save(ob):
    if not E.save_loaded_asset(ob,False):raise RuntimeError('Save failed: '+ob.get_path_name())
    return ob
def import_one(p,folder,factory,opts=None):
    t=u.AssetImportTask();t.filename=str(p);t.destination_path=out+'/'+folder;t.destination_name=p.stem;t.automated=True;t.replace_existing=True;t.save=False;t.factory=factory
    if opts:t.options=opts
    T.import_asset_tasks([t]);return get(out+'/'+folder+'/'+p.stem)
def node(cls,x,y,**attrs):
    n=M.create_material_expression(mat,cls,x,y)
    for k,v in attrs.items():n.set_editor_property(k,v)
    return n
def wire(a,output,b,input):
    if not M.connect_material_expressions(a,output,b,input):raise RuntimeError('Invalid pin '+b.get_name()+'.'+input)
def build_material():
    M.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',True)
    M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    slab=node(u.MaterialExpressionSubstrateSlabBSDF,0,0)
    model=next(getattr(u.MaterialSubSurfaceType,n) for n in dir(u.MaterialSubSurfaceType) if 'DIFFUSION' in n and 'PROFILE' not in n)
    slab.set_editor_property('sub_surface_type',model)
    maps={}
    for i,(name,sampler,comp) in enumerate([
        ('Color',u.MaterialSamplerType.SAMPLERTYPE_COLOR,u.TextureCompressionSettings.TC_DEFAULT),
        ('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,u.TextureCompressionSettings.TC_NORMALMAP),
        ('Surface',u.MaterialSamplerType.SAMPLERTYPE_MASKS,u.TextureCompressionSettings.TC_MASKS)]):
        tex=import_one(S/('T_Stablemaster_FaceR6_'+name+'.png'),'Textures',u.TextureFactory())
        tex.set_editor_property('srgb',name=='Color');tex.set_editor_property('compression_settings',comp)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if name=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
        if name=='Normal':tex.set_editor_property('flip_green_channel',True)
        save(tex);maps[name]=node(u.MaterialExpressionTextureSample,-820,260*i,texture=tex,sampler_type=sampler)
    wire(maps['Color'],'RGB',slab,'Diffuse Albedo');wire(maps['Normal'],'RGB',slab,'Normal');wire(maps['Surface'],'G',slab,'Roughness')
    reflective=node(u.MaterialExpressionMultiply,-300,470,const_b=.08);wire(maps['Surface'],'B',reflective,'A');wire(reflective,'',slab,'F0')
    scatter=node(u.MaterialExpressionConstant3Vector,-400,690,constant=u.LinearColor(.38,.18,.085,1))
    wire(scatter,'',slab,'SSS MFP');wire(maps['Surface'],'R',slab,'SSS MFP Scale')
    if not M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Front material')
    M.recompile_material(mat);save(mat)
def import_head():
    ui=u.FbxImportUI();ui.automated_import_should_detect_type=False;ui.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    ui.import_as_skeletal=True;ui.import_mesh=True;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False;ui.create_physics_asset=False;ui.skeleton=skel
    opt=ui.skeletal_mesh_import_data;opt.convert_scene=True;opt.convert_scene_unit=True;opt.force_front_x_axis=False
    opt.set_editor_property('bUseT0AsRefPose',False);opt.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_one(S/'SK_Stablemaster_FaceR6.fbx','Meshes',u.FbxFactory(),ui);slots=list(mesh.materials)
    if len(slots)!=1 or mesh.skeleton!=skel:raise RuntimeError('Unexpected head binding')
    slots[0].material_interface=mat;mesh.set_editor_property('materials',slots);return save(mesh)
bp=get(old+'/BP_Stablemaster');bpfile=P/'Content'/(old[6:]+'/BP_Stablemaster.uasset')
before=hashlib.sha256(bpfile.read_bytes()).hexdigest()
if bp.get_outermost() in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Stablemaster has unsaved changes')
skel=get(old+'/Meshes/SK_Stablemaster_Body_Skeleton');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
matpath=out+'/Materials/M_Stablemaster_FaceR6'
mat=get(matpath) if E.does_asset_exist(matpath) else T.create_asset('M_Stablemaster_FaceR6',out+'/Materials',u.Material,u.MaterialFactoryNew())
build_material();head=import_head()
lib=u.SubobjectDataBlueprintFunctionLibrary;sub=u.get_engine_subsystem(u.SubobjectDataSubsystem)
templates=[lib.get_object_for_blueprint(lib.get_data(h),bp) for h in sub.k2_gather_subobject_data_for_blueprint(bp)]
child,=[c for c in templates if isinstance(c,u.SkeletalMeshComponent) and 'StablemasterHead' in c.get_name()]
main=u.get_default_object(bp.generated_class()).mesh
body=main.skeletal_mesh_asset;clip=main.get_editor_property('animation_data').anim_to_play
if hashlib.sha256(bpfile.read_bytes()).hexdigest()!=before:raise RuntimeError('The blueprint changed during import')
bp.modify();child.modify();child.set_skeletal_mesh_asset(head)
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class());cdo.modify();main=cdo.mesh;main.modify();main.set_skeletal_mesh_asset(body)
main.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE);play=main.get_editor_property('animation_data')
play.anim_to_play=clip;play.saved_looping=True;play.saved_playing=True;main.set_editor_property('animation_data',play)
save(bp)
(S/'published.json').write_text(json.dumps(dict(blueprint=bp.get_path_name(),body=body.get_path_name(),head=head.get_path_name(),idle=clip.get_path_name(),material=mat.get_path_name(),skeleton=skel.get_path_name(),previous_blueprint=before,after_blueprint=hashlib.sha256(bpfile.read_bytes()).hexdigest()),indent=2))
