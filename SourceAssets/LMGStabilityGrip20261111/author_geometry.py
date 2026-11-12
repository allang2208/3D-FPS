"""Reuse the accepted rigid M249 grip, with host-specific closed mounting collars."""
from pathlib import Path
import bpy,json,sys,numpy as np
from mathutils import Matrix,Vector,Quaternion
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1]
def matrix(values):
    return np.array([Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:])) for v in values])
data=json.loads((HERE/'inputs.json').read_text());out=HERE/'Exports';out.mkdir(exist_ok=True)
def hold(key,family):
    return np.array(json.loads((HERE/'contacts.json').read_text())[key][family]['hand_root'])
source_hold=hold('M249','base');report={'parts':{},'runtime_tested':False}
reflect=np.diag([1.,-1.,1.,1.]);to_blender=np.diag([.01,-.01,.01,1.])
d=data['M249'];bind=matrix(d['bind']);root=bind[d['names'].index('WPN_root')]
to_root=np.diag([100.,100.,100.,1.])@np.linalg.inv(root)
source=PROJECT/'SourceAssets/M249Orpind20261107/M249_Editable.blend'
bpy.context.preferences.filepaths.save_version=0
for key in ['M249','LMG201','PKM']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.objects=['M249_Foregrip','M249_Handguard']
    grip,guard=dst.objects
    for ob in [grip,guard]:
        bpy.context.collection.objects.link(ob);ob.parent=None
        for mod in list(ob.modifiers):ob.modifiers.remove(mod)
        ob.matrix_world=Matrix.Identity(4)
        ob.data.transform(Matrix(to_root@np.diag([100.,-100.,100.,1.])))
    guard_pts=np.array([v.co[:] for v in guard.data.vertices]);gp=np.array([v.co[:] for v in grip.data.vertices])
    if key=='M249':report['m249_handguard_root_cm']=guard_pts.tolist()
    bpy.data.objects.remove(guard,do_unlink=True)
    xf=np.eye(4)
    grip.data.transform(Matrix(xf));grip.name='StabilityGrip_SourceBody';bindings={}
    for i,m in enumerate(grip.data.materials):
        m.name='StabilityGrip_Original_'+str(i)
        bindings[m.name]=data['parts']['factory']['materials'][min(i,len(data['parts']['factory']['materials'])-1)]['path']
    obs=[grip]
    if key!='M249':
        # Interface coordinates come from each host's accepted vertical-grip saddle.
        before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=data['parts'][key+'_vertical']['file'],use_anim=False)
        donors=[o for o in bpy.data.objects if o not in before and o.type=='MESH'];seat_points=[];seat_material=None
        for ob in donors:
            for poly in ob.data.polygons:
                mat=ob.data.materials[poly.material_index]
                spec=next((s for s in data['parts'][key+'_vertical']['materials'] if mat.name.startswith(s['path'].split('.')[-1]) or mat.name.startswith(s['slot'])),None)
                if spec and ('Interface' in spec['slot'] or 'Interface' in spec['path']):
                    seat_material=spec['path']
                    seat_points.extend((np.diag([100.,-100.,100.,1.])@np.r_[ob.matrix_world@ob.data.vertices[i].co,1])[:3] for i in poly.vertices)
        for ob in donors:bpy.data.objects.remove(ob,do_unlink=True)
        if not seat_points:raise RuntimeError('Missing authored host saddle '+key)
        seat_points=np.array(seat_points);host=(seat_points.min(0)+seat_points.max(0))*.5
        top=gp[gp[:,2]>gp[:,2].max()-.7];cap=(top.min(0)+top.max(0))*.5
        xf[:3,3]=host-cap
        grip.data.transform(Matrix(xf));cap=host.copy()
        # Closed short bridge joins the retained grip cap to the measured host saddle.
        direction=host-cap;length=np.linalg.norm(direction)
        bpy.ops.mesh.primitive_cube_add(size=1);neck=bpy.context.object;neck.name='HostMountCollar'
        neck.location=(host+cap)*.5;neck.rotation_euler=Vector(direction).to_track_quat('Z','Y').to_euler();neck.dimensions=(2.6,4.2,length+.35)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        m=bpy.data.materials.new('StabilityGrip_'+key+'_Mount');neck.data.materials.append(m);bindings[m.name]=seat_material
        bevel=neck.modifiers.new('RoundedCollar','BEVEL');bevel.width=.08;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
        neck.data.transform(neck.matrix_world);neck.matrix_world=Matrix.Identity(4);obs.append(neck)
        report['parts'][key]=dict(contact_transform=xf.tolist(),host_saddle_cm=host.tolist(),grip_cap_cm=cap.tolist(),collar_length_cm=float(length))
    else:report['parts'][key]=dict(contact_transform=xf.tolist())
    for ob in obs:ob.data.transform(Matrix(to_blender))
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.context.view_layer.objects.active=grip
    name='SM_'+key+'_StabilityGrip';fbx=out/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(name+'.blend')))
    report['parts'][key].update(file=str(fbx),asset='/Game/Weapons/LMGStabilityGrip20261111/'+name,materials=bindings)
(HERE/'geometry.json').write_text(json.dumps(report,indent=2))
print('Authored three rigid grip variants, preserving source geometry size and UVs.')
