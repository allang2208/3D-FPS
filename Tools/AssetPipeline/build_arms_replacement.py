"""Fit the CC0 WRAD mesh to the existing AKM reference skeleton, without changing its rest bones."""
import bpy, json, re, math
from pathlib import Path
from mathutils import Vector, Matrix

OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\ArmsReplacement')
BASE=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend')
bpy.ops.wm.open_mainfile(filepath=str(BASE))
target=bpy.data.objects['SK_AKM_Viewmodel']
with bpy.data.libraries.load(str(OUT/'WRAD_Original/arms.blend'),link=False) as (src,dst):
    dst.objects=['arms','arms_mesh']
for ob in dst.objects:
    if ob: bpy.context.collection.objects.link(ob)
source=next(ob for ob in dst.objects if ob and ob.type=='ARMATURE')
mesh=next(ob for ob in dst.objects if ob and ob.type=='MESH')
mapping={}
for side in ('l','r'):
    mapping.update({f'shoulder.{side}':f'clavicle_{side}',f'bicep.{side}':f'upperarm_{side}',f'forearm.{side}':f'lowerarm_{side}',f'forearm.Twist0.{side}':f'lowerarm_{side}',f'forearm.Twist1.{side}':f'lowerarm_twist_01_{side}',f'wrist.{side}':f'hand_{side}'})
    for finger in ('index','middle','ring','pinky','thumb'):
        for j in (1,2,3): mapping[f'finger_{finger}{j}.{side}']=f'{finger}_0{j}_{side}'

def head(rig,name): return rig.data.bones[name].head_local.copy()
def palm_normal(rig,side,src=False):
    wrist=head(rig,f'wrist.{side}' if src else f'hand_{side}')
    idx=head(rig,f'finger_index1.{side}' if src else f'index_01_{side}')
    mid=head(rig,f'finger_middle1.{side}' if src else f'middle_01_{side}')
    pnk=head(rig,f'finger_pinky1.{side}' if src else f'pinky_01_{side}')
    return (idx-pnk).cross(mid-wrist).normalized()

def bone_end(rig,name,src=False):
    side=name[-1]
    if src:
        if name.startswith('shoulder.'): return head(rig,f'bicep.{side}')
        if name.startswith('bicep.'): return head(rig,f'forearm.{side}')
        if name.startswith('forearm.Twist0.'): return head(rig,f'forearm.Twist1.{side}')
        if name.startswith('forearm'): return head(rig,f'wrist.{side}')
        if name.startswith('wrist.'): return head(rig,f'finger_middle1.{side}')
        if name.startswith('finger_') and name[-3] in '12': return head(rig,name[:-3]+str(int(name[-3])+1)+'.'+side)
        return rig.data.bones[name].tail_local.copy()
    if name.startswith('clavicle_'): return head(rig,f'upperarm_{side}')
    if name.startswith('upperarm_'): return head(rig,f'lowerarm_{side}')
    if name.startswith('lowerarm_'): return head(rig,f'hand_{side}')
    if name.startswith('hand_'): return head(rig,f'middle_01_{side}')
    if '_01_' in name: return head(rig,name.replace('_01_','_02_'))
    if '_02_' in name: return head(rig,name.replace('_02_','_03_'))
    if '_03_' in name:
        current=head(rig,name); previous=head(rig,name.replace('_03_','_02_'))
        return current+(current-previous)*.72
    return rig.data.bones[name].tail_local.copy()

def frame(h,e,normal):
    y=(e-h).normalized(); x=y.cross(normal).normalized(); z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed()

transforms={}
for old,new in mapping.items():
    sh=head(source,old); th=head(target,new)
    se=bone_end(source,old,True); te=bone_end(target,new)
    sn=palm_normal(source,old[-1],True); tn=palm_normal(target,old[-1],False)
    scale=(te-th).length/(se-sh).length
    # The source twist0 represents half the forearm; both twists share the
    # anatomical forearm fit so there is no discontinuity at the elbow.
    if old.startswith('forearm'):
        sh=head(source,f'forearm.{old[-1]}'); se=head(source,f'wrist.{old[-1]}')
        th=head(target,f'lowerarm_{old[-1]}'); te=head(target,f'hand_{old[-1]}')
        scale=(te-th).length/(se-sh).length
    transforms[old]=(sh,th,frame(th,te,tn)@frame(sh,se,sn).transposed(),scale)

weights=[]
for v in mesh.data.vertices:
    influences=[(mesh.vertex_groups[g.group].name,g.weight) for g in v.groups if g.weight>.000001 and mesh.vertex_groups[g.group].name in mapping]
    total=sum(w for n,w in influences)
    if total<=0: raise RuntimeError(f'Unmapped WRAD vertex {v.index}')
    mapped=Vector()
    for n,w in influences:
        sh,th,rot,scale=transforms[n]
        mapped+=(th+(rot@(v.co-sh))*scale)*(w/total)
    v.co=mapped
    merged={}
    for n,w in influences: merged[mapping[n]]=merged.get(mapping[n],0)+w/total
    weights.append(merged)

mesh.vertex_groups.clear()
for name in sorted(set(n for w in weights for n in w)): mesh.vertex_groups.new(name=name)
for i,w in enumerate(weights):
    for name,weight in w.items(): mesh.vertex_groups[name].add([i],weight,'REPLACE')
mesh.name='SK_ArmsReplacement_WRAD'
mesh.data.name='ArmsReplacement_WRAD_Geometry'
mesh.parent=target
mesh.matrix_world=target.matrix_world.copy()
mesh.modifiers.clear()

def material(name,color,roughness):
    mat=bpy.data.materials.new(name); mat.use_nodes=True; mat.diffuse_color=(*color,1)
    bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); bsdf.inputs['Base Color'].default_value=(*color,1); bsdf.inputs['Roughness'].default_value=roughness
    noise=mat.node_tree.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=145
    noise.inputs['Detail'].default_value=2
    bump=mat.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.12; bump.inputs['Distance'].default_value=.00025
    mat.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']); mat.node_tree.links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    return mat
mesh.data.materials.clear()
mesh.data.materials.append(material('M_ArmsReplacement_OliveFabric',(.085,.105,.074),.86))
mesh.data.materials.append(material('M_ArmsReplacement_CharcoalGlove',(.019,.024,.026),.64))
for p in mesh.data.polygons:
    glove=sum(sum(w for n,w in weights[i].items() if n.startswith(('hand_','index_','middle_','pinky_','ring_','thumb_'))) for i in p.vertices)/len(p.vertices)
    p.material_index=1 if glove>.35 else 0
    p.use_smooth=True
# Catmull-Clark creates a rounded silhouette and joint loops from the CC0
# quad cage. Apply before skinning so the exported FBX keeps the same result.
bpy.context.view_layer.objects.active=mesh
mesh.select_set(True)
sub=mesh.modifiers.new('RoundedAnatomy','SUBSURF'); sub.levels=2; sub.render_levels=2
bpy.ops.object.modifier_apply(modifier=sub.name)
arm=mesh.modifiers.new('Armature','ARMATURE'); arm.object=target
bpy.data.objects.remove(source,do_unlink=True)
for ob in bpy.data.objects:
    if ob.type=='MESH' and 'SK_FP_CH_Default_Cubic' in ob.name: ob.hide_render=True; ob.hide_set(True)
mesh.hide_render=False; mesh.hide_set(False)
for act_name in ('AKM_idle','AKM_aim','AKM_reload','AKM_reload_empty'):
    act=bpy.data.actions[act_name]
    target.animation_data.action=act; target.animation_data.action_slot=act.slots[0]
    for f in (act.frame_range[0],sum(act.frame_range)*.5,act.frame_range[1]):
        bpy.context.scene.frame_set(int(f)); bpy.context.view_layer.update()
        ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); em=ev.to_mesh()
        assert all(math.isfinite(v.co.length) for v in em.vertices)
        ev.to_mesh_clear()
target.animation_data.action=bpy.data.actions['AKM_idle'];target.animation_data.action_slot=target.animation_data.action.slots[0]
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SK_ArmsReplacement_Source.blend'))
report={'source':'WRAD ARMS by wriks, CC0 1.0','mesh':mesh.name,'target_rig':target.name,'rest_bones_changed':False,'mapped_bones':mapping,'vertices':len(mesh.data.vertices),'polygons':len(mesh.data.polygons),'materials':[m.name for m in mesh.data.materials],'status':'candidate; requires visual contact inspection'}
(OUT/'arms_replacement_export.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('ARMS_REPLACEMENT_READY',mesh.name,len(mesh.data.vertices))
