"""Editable native-weight contact scenes for the four shared pose families."""
import bpy,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_math import load,matrix,pose
d=load('SK_Super90_V7');profiles=load('profiles_after');poses=load('poses')
C=Matrix.Diagonal((.01,-.01,.01,1));Ci=C.inverted()
def unit(m):return Matrix.LocRotScale(m.translation,m.to_quaternion(),Vector((1,1,1)))
rest={n:unit(C@matrix(v)@Ci) for n,v in d['rest'].items()}
for key,profile in profiles.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig=bpy.data.objects.new('Super90_Native_Contact_Rig',bpy.data.armatures.new('Native reference'))
    bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for n,m in rest.items():
        b=rig.data.edit_bones.new(n);b.matrix=m;b.length=.018
        if d['parents'][n]:b.parent=rig.data.edit_bones[d['parents'][n]]
    bpy.ops.object.mode_set(mode='OBJECT')
    me=bpy.data.meshes.new('Exact native surface');me.from_pydata([(p[0]/100,-p[1]/100,p[2]/100) for p in d['vertices']],[],d['faces']);me.update()
    ob=bpy.data.objects.new('Native Super90 and V7 skin',me);bpy.context.collection.objects.link(ob)
    for label,color in [('Skin',(.62,.40,.28,1)),('Gun',(.13,.15,.17,1))]:
        mat=bpy.data.materials.new(label);mat.diffuse_color=color;me.materials.append(mat)
    for f in me.polygons:
        f.use_smooth=True;f.material_index=int(all(sum(v for n,v in d['weights'][i].items() if n.startswith('WPN_'))>.5 for i in f.vertices))
    for n in rest:ob.vertex_groups.new(name=n)
    for i,weights in enumerate(d['weights']):
        for n,v in weights.items():ob.vertex_groups[n].add([i],v,'REPLACE')
    ob.modifiers.new('Original native weights','ARMATURE').object=rig
    clip=next(c for c in profile['clips'] if 'A_Super90_idle.' in c['base'])
    w,_=pose(d,poses[clip['base']]['samples'][0],clip);normal=matrix(d['rest']['WPN_root'])@w['WPN_root'].inverted()
    for n in rest:
        rig.pose.bones[n].matrix=unit(C@normal@w[n]@Ci);bpy.context.view_layer.update()
    for p in rig.pose.bones:
        p.rotation_mode='QUATERNION'
        for channel in ('location','rotation_quaternion','scale'):p.keyframe_insert(channel,frame=1,group=p.name)
    with bpy.data.libraries.load(str(O/'Exports'/('SM_Super90_'+key+'_Editable.blend'))) as (a,b):b.objects=['SM_Super90_'+key]
    grip=b.objects[0];bpy.context.collection.objects.link(grip)
    grip.matrix_world=Matrix(((0,-1,0,0),(1,0,0,.16),(0,0,1,-.8015),(0,0,0,1)))
    rig['authoring_source']='profiles_after.json.gz contains all 30 current action layers; this scene retains editable idle contact'
    bpy.context.scene.frame_end=1;bpy.context.scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'Exports'/('Super90_'+key+'_Grasp_Editable.blend')))
    print('EDITABLE_GRASP '+key,flush=True)
