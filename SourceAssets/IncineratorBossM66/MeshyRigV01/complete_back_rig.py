"""Extend the user's SmartRig locally. Preserve topology, UVs and limb weights."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/MeshyRigV01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/M66_source.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=bpy.data.objects['output'];original_names=[b.name for b in rig.data.bones]
original_parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
source_bounds=[list(v) for v in (Vector((-0.5372662,-0.4034321,0)),Vector((.5372657,.4034321,1.7000003)))]
positions=np.array([mesh.matrix_world@v.co for v in mesh.data.vertices],dtype=float)
names=[g.name for g in mesh.vertex_groups]
original=[{names[g.group]:float(g.weight) for g in v.groups if g.weight>0} for v in mesh.data.vertices]

# Positions below are measured in the supplied GLB's metre-space, prior to the
# final uniform height conversion. The original 74-bone anatomy is unchanged.
bones=[
 ('M66_Root',None,(0,0,0),(0,0,.12)),
 ('M66_BackAnchor','Bone_005',(.10,.11,1.12),(.10,.17,1.40)),
 ('M66_SacUpper_L','M66_BackAnchor',(.16,.17,1.20),(.30,.23,1.38)),
 ('M66_SacLower_L','M66_BackAnchor',(.15,.19,1.07),(.29,.26,.92)),
 ('M66_SacUpper_R','M66_BackAnchor',(.03,.16,1.19),(-.10,.23,1.35)),
 ('M66_SacLower_R','M66_BackAnchor',(.03,.19,1.08),(-.09,.26,.93)),
]
# Three separated high tips and the shorter lateral projection are present in
# the actual mesh. Do not remove the lateral projection to force the concept art.
vents=[
 ('High',(.155,.090,1.465),(.168,.104,1.595),(.172,.112,1.700),.092),
 ('Rear',(-.003,.052,1.455),(-.008,.067,1.565),(-.010,.070,1.650),.074),
 ('Front',(.031,-.043,1.455),(.039,-.060,1.565),(.044,-.065,1.650),.060),
 ('Lateral',(.265,.150,1.400),(.285,.120,1.490),(.285,.090,1.590),.063),
]
for label,start,middle,end,radius in vents:
    bones.extend([(f'M66_Vent_{label}_Base','M66_BackAnchor',start,middle),
                  (f'M66_Vent_{label}_Tip',f'M66_Vent_{label}_Base',middle,end)])
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name,parent,head,tail in bones:
    bone=rig.data.edit_bones.new(name);bone.head=head;bone.tail=tail;bone.use_deform=True
    if parent:bone.parent=rig.data.edit_bones[parent]
rig.data.edit_bones['Bone_000'].parent=rig.data.edit_bones['M66_Root']
bpy.ops.object.mode_set(mode='OBJECT')
for name,_,_,_ in bones:mesh.vertex_groups.new(name=name)
for pb in rig.pose.bones:pb.custom_shape=None
if 'Icosphere' in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects['Icosphere'],do_unlink=True)

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3.-2.*t)
def add(weights,name,value):
    if value>1e-8:weights[name]=weights.get(name,0.)+value
def mix(a,b,t):
    out={k:v*(1-t) for k,v in a.items()}
    for k,v in b.items():add(out,k,v*t)
    return out

changed=[];weights_out=[];regions={'back_sac':0,'vents':0};families={name:0 for name,_,_,_ in bones}
for index,(point,old) in enumerate(zip(positions,original)):
    x,y,z=point
    # Follow the actual torso's slight yaw. The posterior mask excludes the
    # hanging right forearm and the left arm held in front of the abdomen.
    depth=y+.35*x
    posterior=smooth(.105,.235,depth)*smooth(.70,.91,z)*(1-smooth(1.43,1.54,z))
    posterior*=smooth(-.26,-.13,x)*(1-smooth(.46,.53,x))
    # Preserve attachment transition on the lower pelvis. The far posterior
    # surface is reassigned even if auto-rig gave it an arm/leg influence.
    out=dict(old)
    if posterior>1e-5:
        left=smooth(-.025,.175,x);upper=smooth(1.01,1.28,z)
        back={'M66_BackAnchor':.12}
        for name,w in [('M66_SacUpper_L',left*upper),('M66_SacLower_L',left*(1-upper)),
                       ('M66_SacUpper_R',(1-left)*upper),('M66_SacLower_R',(1-left)*(1-upper))]:add(back,name,w*.88)
        out=mix(out,back,posterior);regions['back_sac']+=1
    candidates=[]
    for label,start,middle,end,radius in vents:
        h=smooth(start[2]+.005,middle[2]+.005,z)
        if h<=0:continue
        t=max(0.,min(1.,(z-start[2])/(end[2]-start[2])))
        cx=start[0]+(end[0]-start[0])*t;cy=start[1]+(end[1]-start[1])*t
        distance=math.hypot(x-cx,y-cy)
        falloff=1.-smooth(radius*.76,radius*1.38,distance)
        a=h*falloff
        if a>1e-5:candidates.append((a,label,middle,end))
    if candidates:
        # Soft overlap between tube bases, never a hard nearest-bone seam.
        strength=max(v[0] for v in candidates);total=sum(v[0]**4 for v in candidates);vw={}
        for alpha,label,middle,end in candidates:
            share=alpha**4/total;tip=smooth(middle[2]-.025,end[2]-.025,z)
            add(vw,f'M66_Vent_{label}_Base',share*(1-tip));add(vw,f'M66_Vent_{label}_Tip',share*tip)
        out=mix(out,vw,strength);regions['vents']+=1
    touched=posterior>1e-5 or bool(candidates)
    weights_out.append(out)
    if touched:changed.append(index)

# glTF has duplicated vertices on UV/normal seams. Share weights at coincident
# positions only within the edited region, retaining the original mesh splits.
seams={}
for i in changed:seams.setdefault(tuple(np.rint(positions[i]/1e-6).astype(int)),[]).append(i)
for ids in seams.values():
    if len(ids)<2:continue
    avg={}
    for i in ids:
        for k,v in weights_out[i].items():add(avg,k,v/len(ids))
    for i in ids:weights_out[i]=dict(avg)
for i in changed:
    out=sorted(weights_out[i].items(),key=lambda p:-p[1])[:8]
    out=[(k,v) for k,v in out if v>=1e-6];total=sum(v for _,v in out)
    for g in list(mesh.data.vertices[i].groups):mesh.vertex_groups[g.group].remove([i])
    for name,value in out:
        mesh.vertex_groups[name].add([i],value/total,'REPLACE')
        if name in families:families[name]+=1

# Keep all original triangles, vertex order, UVs and material slots. Uniform
# conversion establishes the previously designed 3.8 m height for UE import.
factor=3.8/(positions[:,2].max()-positions[:,2].min())
mesh.data.transform(Matrix.Scale(factor,4));rig.data.transform(Matrix.Scale(factor,4))
mesh.name='M66_Body';rig.name='M66_Rig';rig.data.name='M66_SmartRig_BackCompleted'
rig['source_bones_preserved']=74;rig['stage']='Rig only; no locomotion or attack clips'
mesh['M66_source']='User Meshy decimated SmartRig GLB; geometry and UVs preserved'
mesh['M66_back_binding']='Four sac regions plus four two-bone heat-vent chains; original limbs preserved'
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
scene.frame_set(1)
textures={}
for image,key in [('texture_0','BaseColor'),('normal','Normal'),('texture_0_metallic_roughness','MetallicRoughness')]:
    img=bpy.data.images.get(image)
    if not img:raise RuntimeError('Source image missing: '+image)
    destination=ROOT/'Textures'/f'T_M66_{key}.png';img.filepath_raw=str(destination);img.file_format='PNG';img.save();textures[key]=str(destination)
    img.pack()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_back_completed_v01.blend'))
fbx=ROOT/'Export/SK_M66_BackCompleted_V01.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,use_mesh_modifiers=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    mesh_smooth_type='OFF',path_mode='AUTO',embed_textures=False,use_custom_props=True)
glb=ROOT/'Export/M66_back_completed_v01.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,
    export_skins=True,export_all_influences=True,export_yup=True,export_normals=True,
    export_tangents=True,export_materials='EXPORT',export_extras=True)
report={'source':str(ROOT/'Inputs/M66_user_rig.glb'),'authoring':str(ROOT/'Authoring/M66_back_completed_v01.blend'),
    'fbx':str(fbx),'glb':str(glb),'textures':textures,'source_bones':len(original_names),'bones':len(rig.data.bones),
    'added_bones':[{'name':n,'parent':p,'head_source_m':h,'tail_source_m':t,'weighted_vertices':families[n]} for n,p,h,t in bones],
    'original_parents':original_parents,'source_root_reparented_to':'M66_Root','edited_vertices':len(changed),
    'unchanged_vertices':len(original)-len(changed),'vertices':len(mesh.data.vertices),'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),
    'regions':regions,'height_m':3.8,'uniform_scale':factor,'animations':[],
    'source_bind_problem':'No zero-weight body vertices. Posterior sac and heat vents lacked dedicated controls; broad auto-rig influences on generic trunk bones.',
    'runtime_tested':False,'rendered':False}
(ROOT/'Records/rig_completion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_RIG_COMPLETE '+json.dumps({k:report[k] for k in ['source_bones','bones','edited_vertices','unchanged_vertices','vertices','triangles','height_m','fbx','glb']}))
