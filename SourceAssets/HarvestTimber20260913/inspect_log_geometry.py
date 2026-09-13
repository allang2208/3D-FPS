"""Focused geometry diagnosis requested by the user; inspect delivered FBX logs."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).parent;OUT=ROOT/'SolidRepair';OUT.mkdir(exist_ok=True)
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
fixed=mode!='before'
bpy.ops.wm.read_factory_settings(use_empty=True)
report={};models=[]
blend=OUT/'SolidTimber_Editable.blend' if fixed else ROOT/'HarvestTimber_Editable.blend'
bark_name='TimberSolidBark' if fixed else 'TimberBark'
end_name='TimberSolidEndGrain' if fixed else 'TimberEndGrain'
with bpy.data.libraries.load(str(blend),link=False) as (a,b):
    b.materials=[n for n in a.materials if n in (bark_name,end_name)]
for index,kind in enumerate('ABC'):
    before=set(bpy.data.objects)
    folder=OUT/('UEExport' if mode=='engine' else 'Delivery') if fixed else ROOT/'Delivery'
    name=('SM_PoplarLog_Solid_' if fixed else 'SM_PoplarLog_')+kind+'.fbx'
    bpy.ops.import_scene.fbx(filepath=str(folder/name),use_anim=False)
    obj=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
    # UE's exporter keeps centimetres in vertices with a 0.01 object scale.
    # Measure physical metres after applying the imported world transform.
    matrix=obj.matrix_world.copy();obj.parent=None;obj.data.transform(matrix);obj.matrix_world=Matrix.Identity(4)
    for slot in obj.material_slots:
        slot.material=bpy.data.materials[end_name if 'End' in slot.name else bark_name]
    bm=bmesh.new();bm.from_mesh(obj.data)
    raw_boundary=sum(e.is_boundary for e in bm.edges)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    visited=set();components=[]
    for first in bm.verts:
        if first in visited:continue
        group=set();stack=[first];visited.add(first)
        while stack:
            v=stack.pop();group.add(v)
            for e in v.link_edges:
                other=e.other_vert(v)
                if other not in visited:visited.add(other);stack.append(other)
        faces={f for v in group for f in v.link_faces}
        components.append({'verts':len(group),'faces':len(faces),'area':sum(f.calc_area() for f in faces)})
    ends=[]
    for sign in (-1,1):
        x=(min if sign<0 else max)(v.co.x for v in bm.verts)
        faces=[f for f in bm.faces if all(abs(v.co.x-x)<1e-4 for v in f.verts)]
        ends.append({'x':x,'faces':len(faces),'area_m2':sum(f.calc_area() for f in faces),
            'material_slots':sorted({f.material_index for f in faces}),
            'outward_faces':sum(f.normal.x*sign>.9 for f in faces)})
    report[kind]={'raw_boundary_edges':raw_boundary,'welded_boundary_edges':sum(e.is_boundary for e in bm.edges),
        'non_manifold_edges':sum(not e.is_manifold for e in bm.edges),'vertices':len(bm.verts),
        'faces':len(bm.faces),'signed_volume_m3':bm.calc_volume(signed=True),
        'components':sorted(components,key=lambda c:-c['area'])[:12],'ends':ends}
    bm.free();obj.location=(0,(index-1)*.63,.20);models.append(obj)
(OUT/(mode+'_geometry.json')).write_text(json.dumps(report,indent=2))
if fixed:
    for kind,info in report.items():
        if info['welded_boundary_edges'] or info['non_manifold_edges']:raise RuntimeError('Open repaired log '+kind)
        if len(info['components'])!=1 or info['signed_volume_m3']<=0:raise RuntimeError('Disconnected or inverted repaired log '+kind)
        if any(e['area_m2']<.04 or e['outward_faces']!=e['faces'] for e in info['ends']):raise RuntimeError('Incomplete end cap '+kind)
# Actual FBX models with their source materials, viewed from one cut end.
for mat in bpy.data.materials:mat.use_backface_culling=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.device='CPU'
scene.render.threads_mode='FIXED';scene.render.threads=10
scene.world=bpy.data.worlds.new('InspectionWorld');scene.world.color=(.18,.18,.18)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0))
ground=bpy.context.object;mat=bpy.data.materials.new('NeutralFloor');mat.diffuse_color=(.12,.14,.16,1);ground.data.materials.append(mat)
for at,power,size in [((1.5,-1,3),450,3),((-2,1,1.5),180,2)]:
    bpy.ops.object.light_add(type='AREA',location=at);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size
    light.rotation_euler=(Vector((0,0,.1))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(1.65,-1.5,1.45));camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,.19))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=2.25;scene.camera=camera
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(mode+'_logs.png'))
bpy.ops.render.render(write_still=True)
print('LOG_GEOMETRY_DIAGNOSIS',json.dumps(report),flush=True)
