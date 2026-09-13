"""Read the original P9 FBX motions into a common, metre-based weapon space."""
import bpy, math, pickle, json
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent
ART=Path('E:/3d/infima-fps-staging/reference-art/Art')
FILES={'idle':'Idle_Pose','aim':'Aim_Pose','fire':'Fire','aim_fire':'Aim_Fire',
       'reload':'Reload','reload_empty':'Reload_Empty','draw':'Unholster','holster':'Holster','inspect':'Inspect'}
bpy.ops.wm.read_factory_settings(use_empty=True)
def imported(path):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(path))
    return list(set(bpy.data.objects)-before)
actions={};arms=None
for key,suffix in FILES.items():
    objects=imported(ART/'Animations/Character/Handguns'/('A_FP_PCH_Handgun_'+suffix+'.fbx'))
    rig=next(o for o in objects if o.type=='ARMATURE')
    a=rig.animation_data.action;a.name='P9_SOURCE_'+key;a.use_fake_user=True;actions[key]=a
    if arms is None:arms=rig
    else:
        for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
normalization=bpy.data.objects.new('P9_Centimetres',None);bpy.context.scene.collection.objects.link(normalization)
normalization.scale=(.01,.01,.01);arms.parent=normalization
objects=imported(ART/'Meshes/Weapons/Handguns/SK_Handgun_03.fbx')
weapon=next(o for o in objects if o.type=='ARMATURE')
weapon_actions={a.name.rsplit('|',1)[-1]:a for a in bpy.data.actions if a not in actions.values()}
for a in weapon_actions.values():
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in list(bag.fcurves):
                    if not fc.data_path.startswith('pose.bones['):bag.fcurves.remove(fc)
rotation=weapon.rotation_euler.to_matrix().to_4x4()
weapon.animation_data_clear();weapon.parent=arms;weapon.parent_type='BONE';weapon.parent_bone='ik_hand_gun'
weapon.matrix_parent_inverse=Matrix.Identity(4)
weapon.matrix_basis=Matrix.Translation((0,-arms.data.bones['ik_hand_gun'].length,0))@rotation
def set_action(r,a):
    r.animation_data_create();r.animation_data.action=None
    for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
    r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def frame(f):
    bpy.context.scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
def rigid(m):return Matrix.LocRotScale(m.translation,m.to_quaternion(),Vector((1,1,1)))
def rows(m):return [list(row) for row in m]
set_action(arms,actions['idle']);set_action(weapon,weapon_actions['_Ref_Pose']);frame(1)
# Source weapon vertices use -Y forward and +Z up. Put the gun 42 cm in front
# of the authoring camera, retaining its source wrist/shoulder arrangement.
C=Matrix.Translation((0,-.42,-.13))@rigid(weapon.matrix_world).inverted()
rest={b.name:rows(rigid(C@arms.matrix_world@b.matrix_local)) for b in arms.data.bones}
wrest={b.name:rows(rigid(C@weapon.matrix_world@b.matrix_local)) for b in weapon.data.bones}
report={'source_files':FILES,'arms':len(rest),'weapon_bones':list(wrest),'sample_rate':120,'clips':{}}
data={'rest':rest,'weapon_rest':wrest,'clips':{}}
for key,a in actions.items():
    set_action(arms,a)
    wn='A_FP_WEP_Handgun_03_'+('Reload_Empty' if key=='reload_empty' else 'Reload') if key.startswith('reload') else 'A_WEP_Handgun_03_Fire' if key in ['fire','aim_fire'] else '_Ref_Pose'
    wa=weapon_actions[wn];set_action(weapon,wa)
    start,end=map(float,a.frame_range);duration=(end-start)/30
    samples=[]
    for index in range(round(duration*120)+1):
        f=start+index/4;frame(f)
        samples.append({'arms':{b.name:rows(rigid(C@arms.matrix_world@b.matrix)) for b in arms.pose.bones},
                        'weapon':{b.name:rows(rigid(C@weapon.matrix_world@b.matrix)) for b in weapon.pose.bones},
                        'gun':rows(rigid(C@weapon.matrix_world))})
    data['clips'][key]={'duration':duration,'samples':samples}
    report['clips'][key]={'fps':30,'start':start,'end':end,'duration':duration,'samples':len(samples)}
set_action(weapon,weapon_actions['_Ref_Pose']);set_action(arms,actions['idle']);frame(1)
report['weapon_meshes']=[]
for ob in objects:
    if ob.type!='MESH':continue
    mats=[m.name for m in ob.data.materials]
    bins={}
    # Weapon-space material bounds supply the grip alignment, independently
    # from model origins and the first-person camera offset.
    for poly in ob.data.polygons:
        name=mats[poly.material_index]
        bins.setdefault(name,set()).update(poly.vertices)
    for name,ids in bins.items():
        pts=[weapon.matrix_world.inverted()@ob.matrix_world@ob.data.vertices[i].co for i in ids]
        report['weapon_meshes'].append({'object':ob.name,'material':name,'min':[min(v[k] for v in pts)*.01 for k in range(3)],'max':[max(v[k] for v in pts)*.01 for k in range(3)]})
with (O/'donor.pkl').open('wb') as f:pickle.dump(data,f)
(O/'donor.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('P9_DONOR_EXTRACTED',flush=True)
