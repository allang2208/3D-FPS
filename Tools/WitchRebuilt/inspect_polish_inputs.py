"""Scoped garment/throw diagnosis requested by the user, with authoring renders."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
OUT=ROOT/'Polish20260922';OUT.mkdir(exist_ok=True)
report={}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
for o in bpy.context.scene.objects:
    if o.type!='MESH' or 'SimulationProxy' in o.name:continue
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00001)
    todo=set(bm.verts);groups=[]
    while todo:
        seed=todo.pop();comp={seed};stack=[seed]
        while stack:
            for e in stack.pop().link_edges:
                for v in e.verts:
                    if v in todo:todo.remove(v);comp.add(v);stack.append(v)
        faces={f for v in comp for f in v.link_faces}
        groups.append({'verts':len(comp),'faces':len(faces),'area':sum(f.calc_area() for f in faces),
            'min':[min(v.co[i] for v in comp) for i in range(3)],'max':[max(v.co[i] for v in comp) for i in range(3)]})
    groups.sort(key=lambda g:-g['area'])
    mats=[]
    for m in o.data.materials:
        mats.append({'name':m.name,'images':[{'name':n.image.name,'path':bpy.path.abspath(n.image.filepath),'exists':Path(bpy.path.abspath(n.image.filepath)).exists()} for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []})
    report[o.name]={'verts':len(o.data.vertices),'faces':len(o.data.polygons),'components':groups,'materials':mats}
    bm.free()
for role in ['Idle','ThrowPoisonBottle']:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'Authoring/WitchRebuilt_{role}.blend'))
    r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    poses=[]
    for frame in [1,10,17,21,23,25,30,37,46] if role!='Idle' else [1]:
        bpy.context.scene.frame_set(frame)
        poses.append({'frame':frame,'bones':{n:{'position':list((r.matrix_world@r.pose.bones[n].matrix).translation),
            'scale':list((r.matrix_world@r.pose.bones[n].matrix).to_scale())} for n in ['pelvis','spine_03','clavicle_r','upperarm_r','lowerarm_r','hand_r','middle_01_r','middle_03_r']}})
    report[role]=poses
(OUT/'inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

def render(role,fr,back=False):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'Authoring/WitchRebuilt_{role}.blend'))
    s=bpy.context.scene;s.frame_set(fr)
    for o in s.objects:
        if o.type=='MESH':o.hide_render='SimulationProxy' in o.name
    s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
    s.render.resolution_x=700;s.render.resolution_y=850;s.render.resolution_percentage=100
    s.world=bpy.data.worlds.new('Review');s.world.color=(.3,.3,.3)
    s.view_settings.view_transform='AgX'
    def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
    cd=bpy.data.cameras.new('Review');c=bpy.data.objects.new('Review',cd);s.collection.objects.link(c)
    c.location=(3,5,2.2) if back else (3,-5,2.2);aim(c,(0,0,1.05));cd.type='ORTHO';cd.ortho_scale=2.4;s.camera=c
    for loc,energy,size in [((1,-3,4),350,4),((-3,-1,2),240,3),((0,3,3),400,3)]:
        d=bpy.data.lights.new('Review','AREA');d.energy=energy;d.shape='DISK';d.size=size
        ob=bpy.data.objects.new('Review',d);s.collection.objects.link(ob);ob.location=loc;aim(ob,(0,0,1))
    s.render.filepath=str(OUT/f'before_{role}_{fr}_{"back" if back else "front"}.png')
    bpy.ops.render.render(write_still=True)
for args in [('Idle',1,False),('Idle',1,True),('ThrowPoisonBottle',17,False),('ThrowPoisonBottle',23,False),('ThrowPoisonBottle',30,False)]:render(*args)
print('Garment topology, source materials and throw poses recorded',flush=True)
