import json,math
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME'); OUT=P/'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit'
D='/Game/Characters/VillageBlacksmithNPC20261118'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
SKEL=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def existing(path):
    return u.load_asset(path) if E.does_asset_exist(path) else None
def save(o):
    if not o or not o.get_path_name().startswith(D+'/') or not E.save_loaded_asset(o,False):raise RuntimeError('Asset not saved '+str(o))
    return o
def dup(src,name,folder=''):
    path=(D+'/'+folder).rstrip('/')
    return existing(path+'/'+name) or A.duplicate_asset(name,path,src)
def tex(name,kind):
    folder=D+'/BodyOutfit/Textures';tex=existing(folder+'/'+name)
    if not tex:
        task=u.AssetImportTask();task.set_editor_property('filename',str(OUT/'Textures'/(name+'.png')));task.set_editor_property('destination_path',folder);task.set_editor_property('destination_name',name);task.set_editor_property('automated',True);task.set_editor_property('save',False);A.import_asset_tasks([task]);tex=existing(folder+'/'+name)
    if not tex:raise RuntimeError(name)
    tex.set_editor_property('srgb',kind=='BC')
    tex.set_editor_property('compression_settings',{'BC':u.TextureCompressionSettings.TC_DEFAULT,'N':u.TextureCompressionSettings.TC_NORMALMAP,'ORM':u.TextureCompressionSettings.TC_MASKS}[kind])
    return save(tex)
def material(slot):
    dst=D+'/BodyOutfit/Materials';name='M_Smith_'+slot
    m=existing(dst+'/'+name) or A.create_asset(name,dst,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    m.set_editor_property('two_sided',slot in ['Saddle','Thread','Apron','Linen','Twill'])
    for kind in ['BC','N','ORM']:
        n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.texture=tex('T_Smith_'+slot+'_'+kind,kind)
        n.sampler_type={'BC':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'N':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]
        pins={'BC':[('RGB',u.MaterialProperty.MP_BASE_COLOR)],'N':[('RGB',u.MaterialProperty.MP_NORMAL)],'ORM':[('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]}
        for ch,pin in pins[kind]:
            if not L.connect_material_property(n,ch,pin):raise RuntimeError('Missing shader connection '+kind)
    L.recompile_material(m);return save(m)
def make_hidden():
    name='M_Smith_Covered';folder=D+'/BodyOutfit/Materials'
    m=existing(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    zero=L.create_material_expression(m,u.MaterialExpressionConstant);zero.set_editor_property('r',0)
    L.connect_material_property(zero,'',u.MaterialProperty.MP_OPACITY_MASK);L.recompile_material(m);return save(m)
r4=json.loads((P/'SourceAssets/JasonStrong20261117/R4_PoseRefined/variant_saved.json').read_text())
source=u.load_asset(r4['asset']);graph=dup(u.load_asset(r4['post_process'].split('.')[0]),'ABP_Smith_R4_Correctives','BodyOutfit')
save(graph)
body=dup(source,'SK_Smith_Body')
skin={}
for part,source_mat in [('body','MI_Body_Baked'),('head','MI_Face_Skin_Baked_LOD0')]:
    orig=u.load_asset('/Game/AsianMale_Jason/Material/'+source_mat)
    m=dup(orig,'MI_Smith_'+part.title()+'Skin','BodyOutfit/Materials')
    L.set_material_instance_texture_parameter_value(m,'Basecolor Baked',tex('T_Smith_Skin_'+part+'_BC','BC'))
    L.update_material_instance(m);skin[part]=save(m)
hidden=make_hidden()
slots=list(body.materials)
for idx,s in enumerate(slots):
    if idx==6:continue
    s.material_interface=skin['head'] if idx==5 else hidden if idx not in [0,1,2,3] else skin['body']
body.set_editor_property('materials',slots)
body.set_editor_property('post_process_anim_blueprint',E.load_blueprint_class(graph.get_path_name().split('.')[0]))
save(body);print('SMITH_BODY_SAVED',body.get_path_name(),flush=True)
d=json.loads((OUT/'outfit.json').read_text())
mats=[material(slot) for slot in d['material_slots']]
print('SMITH_WORKWEAR_MATERIALS_SAVED',flush=True)
ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('No R4 binding')
ps=[];ns=[];uvs=[];ws=[];fs=[];lut={}
for i,tri in enumerate(d['triangles']):
    row=[]
    for j,v in enumerate(tri):
        n=d['normals'][i][j];tc=d['uv'][i][j];key=(v,*[round(a,5) for a in n+tc])
        if key not in lut:
            lut[key]=len(ps);ps.append(u.Vector(*d['positions'][v]));ns.append(u.Vector(*n));uvs.append(u.Vector2D(*tc));ws.append(d['weights'][v])
        row.append(lut[key])
    fs.append(u.IntVector(*row))
dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uvs,triangles=fs),0,True)
B.copy_bones_from_mesh(ref,dm);B.mesh_create_bone_weights(dm)
for i,ww in enumerate(ws):
    B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=int(b),weight=float(w)) for b,w in ww if w>0])
for i,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,slot,True)
opts=u.GeometryScriptCreateNewSkeletalMeshAssetOptions();opts.use_mesh_bone_proportions=True;opts.enable_recompute_normals=False;opts.enable_recompute_tangents=True;opts.materials=dict(zip(d['material_slots'],mats))
path=D+'/SK_Smith_Outfit'
ob=existing(path)
if ob is None:
    ob,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,source.skeleton,path,opts)
else:
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,ob,options,u.GeometryScriptMeshWriteLOD(lod_index=0))
if not ob or status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not create skinned outfit')
ob.set_editor_property('physics_asset',source.physics_asset)
lods=SKEL.regenerate_lod(ob,3,True,False)
save(ob)
(OUT/'saved.json').write_text(json.dumps({'body':body.get_path_name(),'outfit':ob.get_path_name(),'skeleton':source.skeleton.get_path_name(),'graph':graph.get_path_name(),'outfit_lods':SKEL.get_lod_count(ob),'morph_targets':r4['morphs'],'source':source.get_path_name(),'runtime_tested':False},indent=2))
print('SMITH_BODY_AND_WORKWEAR_SAVED',flush=True)
