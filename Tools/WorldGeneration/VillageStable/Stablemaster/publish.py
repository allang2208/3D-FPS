"""Publish this resident's materials, hair bindings and clothed Kaitlin assembly."""
import json
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
src=root/'SourceAssets/HillsVillageStable/StablemasterR2'
dest='/Game/WorldGeneration/TemperateHills/VillageStable/StablemasterR2'
assets=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools();ml=u.MaterialEditingLibrary
def read(p):return json.loads(p.read_bytes())
def load(p):
    a=assets.load_asset(p)
    if not a:raise RuntimeError('Missing asset '+str(p))
    return a
def save(a):
    if not assets.save_loaded_asset(a,False):raise RuntimeError('Failed to save '+a.get_path_name())
    return a
def owned(name,cl,factory,folder=''):
    path=dest+folder+'/'+name
    return load(path) if assets.does_asset_exist(path) else tools.create_asset(name,dest+folder,cl,factory)
def texture(name):
    path=dest+'/Materials/'+name
    task=u.AssetImportTask();task.filename=str(src/(name+'.png'));task.destination_path=dest+'/Materials';task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True
    tools.import_asset_tasks([task]);tex=load(path)
    tex.set_editor_property('srgb',True);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER)
    return save(tex)
def tint(name,original,keys,tex):
    mat=owned(name,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew(),'/Materials')
    ml.set_material_instance_parent(mat,load(original))
    for key in keys:
        ml.set_material_instance_texture_parameter_value(mat,key,tex)
    ml.update_material_instance(mat);return save(mat)
head=load(dest+'/SK_Stablemaster_Face')
native='/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Face/SKM_MHC_Kaitlin_FaceMesh'
skin=read(src/'Inputs/skin.json');eyes=read(src/'Inputs/iris.json');materials={}
tex=texture('T_Stablemaster_Face_BC')
for key,d in skin.items():
    materials[d['parent']]=tint('MI_Stablemaster_Skin_'+key,d['parent'],d['albedo'],tex)
for side,d in eyes.items():
    materials[d['parent']]=tint('MI_Stablemaster_Eye'+side,d['parent'],[d['parameter']],texture('T_Stablemaster_Iris'+side))
slots=list(load(native).get_editor_property('materials'))
for slot in slots:
    mat=slot.material_interface
    if mat and mat.get_path_name() in materials:slot.material_interface=materials[mat.get_path_name()]
head.set_editor_property('materials',slots)
post=load(native).get_editor_property('post_process_anim_blueprint')
if post:
    bp_path=post.get_path_name().rsplit('.',1)[0]
    local=dest+'/ABP_Stablemaster_FacePost'
    postbp=load(local) if assets.does_asset_exist(local) else assets.duplicate_asset(bp_path,local)
    cdo=u.get_default_object(postbp.generated_class())
    cdo.set_editor_property('EnableHeadMovementIK',False)
    save(postbp);head.set_editor_property('post_process_anim_blueprint',postbp.generated_class())
save(head)

bun_name='Stablemaster_LowBun';hairpath=dest+'/Grooms/'+bun_name
if not assets.does_asset_exist(hairpath):
    task=u.AssetImportTask();task.filename=str(src/(bun_name+'.abc'));task.destination_path=dest+'/Grooms';task.destination_name=bun_name
    task.automated=True;task.save=False;task.factory=u.HairStrandsFactory()
    opts=u.GroomImportOptions();convert=opts.get_editor_property('conversion_settings');convert.rotation=u.Vector(-90,0,0);convert.scale=u.Vector(1,1,1)
    opts.set_editor_property('conversion_settings',convert);task.options=opts;tools.import_asset_tasks([task])
bun=load(hairpath)
info=bun.get_editor_property('hair_groups_rendering')[0];geo=info.get_editor_property('geometry_settings')
geo.set_editor_property('hair_width',.011);geo.set_editor_property('hair_tip_scale',.28);info.set_editor_property('geometry_settings',geo);bun.set_editor_property('hair_groups_rendering',[info])
lod=bun.get_editor_property('hair_groups_lod')[0];lod.import_text('(LODs=((ScreenSize=1.0,GeometryType=Strands),(CurveDecimation=0.55,VertexDecimation=0.70,ScreenSize=0.15,ThicknessScale=1.20,GeometryType=Strands),(CurveDecimation=0.24,VertexDecimation=0.50,ScreenSize=0.04,ThicknessScale=1.45,GeometryType=Strands)))')
bun.set_editor_property('hair_groups_lod',[lod]);save(bun)
def binding(name,g):
    path=dest+'/Grooms/'+name+'_Binding'
    if assets.does_asset_exist(path):return load(path)
    obj=u.GroomLibrary.create_new_groom_binding_asset_with_path(path,g,head,100,None,0)
    if not obj:raise RuntimeError('Groom binding unavailable '+name)
    return save(obj)
player=read(root/'Content/ColdSteelData/player_body.json')['body_variants']['kaitlin']
outfit=read(root/'Content/ColdSteelData/modular_outfits.json')['body_variants']['kaitlin']['items']
factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.Actor)
bp=owned('BP_Stablemaster',u.Blueprint,factory)
sub=u.get_engine_subsystem(u.SubobjectDataSubsystem);lib=u.SubobjectDataBlueprintFunctionLibrary
def template(h):return lib.get_object_for_blueprint(lib.get_data(h),bp)
def component(name,cl,parent):
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        ob=template(h)
        if isinstance(ob,cl) and ob.get_name().removesuffix('_GEN_VARIABLE')==name:return h,ob
    h,why=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=cl,blueprint_context=bp))
    if not template(h):raise RuntimeError('Component '+name+' '+str(why))
    sub.rename_subobject(h,u.Text(name))
    return h,template(h)
origin=sub.k2_gather_subobject_data_for_blueprint(bp)
root_handle=next((h for h in origin if isinstance(template(h),u.SceneComponent)),origin[0])
bh,body=component('KaitlinBody',u.SkeletalMeshComponent,root_handle)
body.set_skeletal_mesh_asset(load(player['body_mesh']))
body.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
play=body.get_editor_property('animation_data');play.anim_to_play=load(player['clips']['Unarmed.Idle']);play.saved_looping=True;play.saved_playing=True
body.set_editor_property('animation_data',play)
hh,face=component('StablemasterFace',u.SkeletalMeshComponent,bh);face.set_skeletal_mesh_asset(head)
copy=u.load_class(None,'/Script/FPSGAME.FPSPlayerHeadAnimInstance')
face.set_anim_instance_class(copy)
wear=[('FittingJacket','ue_work_jacket',outfit['ue_work_jacket']['pants_fit_meshes']['ue_leather_pants']['rig_meshes']['Kaitlin']),
      ('BootCutBreeches','ue_leather_pants',outfit['ue_leather_pants']['shoe_fit_meshes']['ue_leather_boots']['Kaitlin']),
      ('RidingBoots','ue_leather_boots',outfit['ue_leather_boots']['rig_meshes']['Kaitlin'])]
hidden=set()
for name,item,path in wear:
    _,part=component(name,u.SkeletalMeshComponent,bh);part.set_skeletal_mesh_asset(load(path));part.set_anim_instance_class(copy)
    hidden.update(outfit[item]['rig_world_covers']['Kaitlin'])
hide=load('/Game/Characters/KaitlinPlayer20261023/Native/Common/Materials/M_Hide')
for i in hidden:body.set_material(i,hide)
grooms=player['heads']['kaitlin']['grooms']
groom_parts=[('RidingBun',bun,['/Game/Characters/ChapelNun20261115/HairReferenceR5/Materials/MI_Nun_Hair'])]
for key,g in zip(('Eyebrows','Eyelashes'),grooms):groom_parts.append((key,load(g['asset']),g['materials']))
for name,g,mats in groom_parts:
    _,part=component(name,u.GroomComponent,hh)
    part.set_editor_property('groom_asset',g);part.set_editor_property('binding_asset',binding(name,g))
    for i,m in enumerate(mats):part.set_material(i,load(m))
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
(src/'assembly.json').write_text(json.dumps({'blueprint':bp.get_path_name(),'body':player['body_mesh'],'head':head.get_path_name(),'native_lods':u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(head),'fitting_clothes':wear,'grooms':[g.get_path_name() for _,g,_ in groom_parts],'gameplay_test':False},ensure_ascii=False,indent=2))
