import bpy,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
from r4_pose import BASE,OUT,DRIVERS,pose_values
r3=BASE/'R3_ArmsRefined'
bpy.ops.wm.open_mainfile(filepath=str(r3/'Jason_StrongTall_R3.blend'))
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['Jason_StrongTall_R3']
rig=bpy.data.objects['Jason_NativeSkeleton']
prior=bpy.data.objects['Jason_Original']
native=json.loads((r3/'AnatomyReview/derived_saved_mesh.json').read_text())
form=json.loads((OUT/'Review/forms.json').read_text())
body.name='Jason_StrongTall_R4';prior.name='Jason_StrongTall_R3_Comparison'
prior.data.vertices.foreach_set('co',(np.asarray(native['positions'])*.01).ravel())
bpy.data.objects['Jason_OriginalHead'].location.z+=.045
key=body.data.shape_keys.key_blocks['Muscle_R3'];key.name='R4_Build'
key.data.foreach_set('co',(np.asarray(form['base'])*.01).ravel())
calc=bpy.data.objects.new('R4 joint angle components',None)
bpy.context.scene.collection.objects.link(calc);calc.empty_display_size=.01;calc.hide_render=True
boneinfo={b['name']:b for b in native['bones']}
neutral=np.array([v.co[:] for v in body.data.shape_keys.key_blocks['Basis'].data])
def property_var(driver,name,ob,path):
    var=driver.variables.new();var.name=name;var.type='SINGLE_PROP';var.targets[0].id=ob;var.targets[0].data_path=path
for shape,bone,axis,start,end in DRIVERS:
    points=neutral.copy()
    for i,x,y,z in form['targets'][shape]:points[i]+=np.array([x,y,z])*.01
    sk=body.shape_key_add(name=shape,from_mix=False);sk.data.foreach_set('co',points.ravel())
    par=native['bones'][boneinfo[bone]['parent']]
    coordinate=np.array(par['axes'])@np.array(rig.data.bones[bone].matrix_local.to_3x3())
    # Rotate the local quaternion's vector part into UE parent space; w is invariant.
    for row,chn in enumerate('xyzw'):
        prop=shape+'_'+chn;calc[prop]=0.
        driver=calc.driver_add('["'+prop+'"]').driver
        variables='w' if chn=='w' else 'xyz'
        for component in variables:
            var=driver.variables.new();var.name='q'+component;var.type='TRANSFORMS'
            target=var.targets[0];target.id=rig;target.bone_target=bone
            target.transform_type='ROT_'+component.upper();target.transform_space='LOCAL_SPACE';target.rotation_mode='QUATERNION'
        driver.expression='qw' if chn=='w' else '+'.join('(%0.8f*q%s)'%(co,c) for co,c in zip(coordinate[row],'xyz'))
    driver=sk.driver_add('value').driver
    for chn in 'xyzw':property_var(driver,'q'+chn,calc,'["'+shape+'_'+chn+'"]')
    euler='asin(max(-1,min(1,2*(qx*qz-qw*qy))))' if axis==1 else 'atan2(2*(qw*qz+qx*qy),1-2*(qy*qy+qz*qz))'
    driver.expression=f'max(0,min(1,(({euler})*57.2957795-{start})/{end-start}))'
bpy.context.view_layer.update()
body['UE_asset']='SK_Jason_StrongTall_R4';body['correctives']='Four independent pose-driven shoulder and elbow shapes'
bpy.context.scene['preview_note']='Left R3, right R4. Raise and bend the arms to activate the drivers.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Jason_StrongTall_R4.blend'),relative_remap=True)
# Compare both sides against the mathematical driver on actual posing.
rig.hide_set(False)
samples={}
for side,sign in [('l',1),('r',-1)]:
    for name,waxis,angle in [('upperarm_'+side,Vector((0,-sign,0)),65),('lowerarm_'+side,None,60)]:
        if waxis is None:
            direction=Vector(boneinfo[name]['position'])-Vector(boneinfo['upperarm_'+side]['position'])
            fore=Vector(boneinfo['hand_'+side]['position'])-Vector(boneinfo[name]['position'])
            waxis=direction.cross(fore).normalized()
        pb=rig.pose.bones[name];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(pb.bone.matrix_local.to_3x3().inverted()@waxis,math.radians(angle))
    bpy.context.view_layer.update()
    samples[side]={s:body.data.shape_keys.key_blocks[s].value for s,*_ in DRIVERS}
(OUT/'Review/blender_driver_check.json').write_text(json.dumps(samples,indent=2))
print('R4_BLENDER_SAVED',samples)
