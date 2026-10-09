"""Offline diagnostic preview using current UE-exported meshes and saved poses."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent/'Diagnostics';P=O.parents[2]
author=P/'SourceAssets/Super90Speedloader20261007/author_speedloader.py';s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
source_rest=s['rest'];data=json.loads((O/'saved_assets.json').read_text());ni={n:i for i,n in enumerate(data['names'])}
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
groups={};rigs={};binds={}
for key in ('weapon','props','guide'):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/(key+'.fbx')))
    objects=list(set(bpy.data.objects)-before);groups[key]=[o for o in objects if o.type=='MESH']
    for ob in objects:
        if ob.type=='ARMATURE':
            rigs[key]=ob;binds[key]={b.name:b.matrix_local.copy() for b in ob.data.bones};ob.animation_data_clear()
    for ob in groups[key]:
        if key=='weapon':
            bm=bmesh.new();bm.from_mesh(ob.data)
            bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==0],context='FACES')
            bm.to_mesh(ob.data);bm.free()
        for mat in ob.data.materials:
            if not mat:continue
            if key=='guide':mat.diffuse_color=(.12,.6,.3,1)
            elif key=='props':mat.diffuse_color=(.08,.35,.65,1)
            elif 'Bare' in mat.name:mat.diffuse_color=(.67,.44,.29,1)
            elif '12gauge' in mat.name:mat.diffuse_color=(.6,.07,.035,1)
            else:mat.diffuse_color=(.19,.21,.24,1)
guide_matrices={o:o.matrix_world.copy() for o in groups['guide']}
def boneframe(key,up):
    d=data['framing'][key];r=s['uemat'](d['WPN_root'])
    x=(Vector(d['WPN_FrontSight'][:3])-Vector(d['WPN_RearSight'][:3])).normalized()
    z=r.to_quaternion()@Vector(up);y=z.cross(x).normalized();z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_quaternion()
base=Quaternion((0,0,1),math.pi/2)
cq=base@boneframe('M4',(0,0,1))@boneframe('Super90',(0,-1,0)).inverted()
cp=Vector((6,7,-7))+base@Vector(data['framing']['M4']['hand_r'][:3])-cq@Vector(data['framing']['Super90']['hand_r'][:3])
view=Matrix(((0,1,0,0),(0,0,1,0),(-1,0,0,0),(0,0,0,1)))@Matrix.LocRotScale(cp/100,cq,Vector((1,-1,1)))
bpy.ops.object.camera_add();camera=bpy.context.object;camera.matrix_world=view.inverted();camera.data.type='PERSP'
camera.data.sensor_fit='VERTICAL';camera.data.angle=math.radians(75);camera.data.clip_start=.01;camera.data.clip_end=20
scene.camera=camera
camera_base=camera.matrix_world.copy()
camera_code=Path(__file__).parent/'camera_preview.py';camera_model={'__file__':str(camera_code),'__name__':'offline_camera'}
exec(compile(camera_code.read_text(),str(camera_code),'exec'),camera_model)
camera_axes=Matrix(((0,1,0,0),(0,0,1,0),(-1,0,0,0),(0,0,0,1)))
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='VIEWPORT';scene.display.shading.background_color=(.055,.055,.055)
scene.view_settings.view_transform='Standard';scene.render.image_settings.file_format='PNG'
frames_dir=O/'Frames';frames_dir.mkdir(exist_ok=True)
def actual_pose(row):
    world={}
    for n in s['names']:world[n]=world.get(s['parents'][n],Matrix.Identity(4))@s['uemat'](row['local'][ni[n]])
    return {n:s['evaluation_to_author']@s['Ci']@world[n]@s['Ki'][n] for n in s['names']}
def apply(p):
    for key,rig in rigs.items():
        r=binds[key];targets={n:p[n]@source_rest[n].inverted()@r[n] for n in r if n in p}
        for bone in rig.pose.bones:
            n=bone.name
            if n not in targets:continue
            parent=bone.parent.name if bone.parent else None
            bone.matrix_basis=r[n].inverted()@r[parent]@targets[parent].inverted()@targets[n] if parent in targets else r[n].inverted()@targets[n]
    for ob,m in guide_matrices.items():ob.matrix_world=p['WPN_root']@source_rest['WPN_root'].inverted()@m
    bpy.context.view_layer.update()
items=[]
for kind in ('normal_7','empty_7'):
    clip=data['clips']['A_Super90_loader_'+kind];end=114
    selected=range(0,147,2) if kind=='normal_7' else range(0,183,2)
    for f in selected:
        row=next(r for r in clip['rows'] if r['frame']==f);p=actual_pose(row);apply(p)
        angles,travel=camera_model['sample'](f,7,kind=='empty_7')
        pitch,yaw,roll=[math.radians(v) for v in angles]
        rotation=Quaternion((0,0,1),yaw)@Quaternion((0,1,0),-pitch)@Quaternion((1,0,0),-roll)
        offset=Matrix.LocRotScale(Vector(travel)/100,rotation,Vector((1,1,1)))
        camera.matrix_world=camera_base@camera_axes@offset@camera_axes.inverted()
        for ob in groups['props']:ob.hide_render=not(74<=f<127)
        scene.render.filepath=str(frames_dir/(kind+'_'+str(f).zfill(3)+'.png'))
        bpy.ops.render.render(write_still=True)
        items.append({'kind':kind,'frame':f,'file':scene.render.filepath})
    print('RENDERED_SAVED',kind,flush=True)
(O/'preview.json').write_text(json.dumps({'camera_location_cm':list(cp),'camera_rotation':list(cq),'vertical_fov':75,'diagnostic_colors':True,'uses_saved_ue_meshes_and_compressed_poses':True,'frames':items},indent=2))
