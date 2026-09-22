import bpy,sys,math
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from render_polish_review import setup,ROOT,OUT
s,c,aim=setup('ThrowPoisonBottle');s.cycles.samples=8;s.render.resolution_x=500;s.render.resolution_y=610
r=next(o for o in s.objects if o.type=='ARMATURE');rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
def normalized(m):
    loc,q,scale=m.decompose();return Matrix.LocRotScale(loc,q,Vector((1,1,1)))
props=[]
for side,file,height in [('r',ROOT/'Authoring/WitchRebuilt_Bottle.blend',.09)]:
    with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=src.objects
    hand=rest['hand_'+side];along=(rest['middle_01_'+side].translation-hand.translation).normalized()
    across=(rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized()
    palm=along.cross(across).normalized()*(-1 if side=='l' else 1)
    z=across;x=(along-z*along.dot(z)).normalized();y=z.cross(x).normalized()
    rot=Matrix((x,y,z)).transposed();mount=rot.to_4x4();mount.translation=hand.translation+along*.071+palm*.022-rot@Vector((0,0,height))
    relative=normalized(hand).inverted()@mount
    for o in dst.objects:
        if o.type!='MESH':continue
        s.collection.objects.link(o);source=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Identity(4)
        for v in o.data.vertices:v.co=source@v.co
        o.modifiers.clear()
        if side=='r':
            for m in o.data.materials:
                m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.22
        props.append((o,side,relative))
frames=OUT/'PreviewFrames';frames.mkdir(exist_ok=True)
for i in range(24):
    t=min(1.5,i/15);s.frame_set(round(t*60)+1)
    for o,side,relative in props:
        o.matrix_world=normalized(r.matrix_world@r.pose.bones['hand_'+side].matrix)@relative
        o.hide_render=side=='r' and t>=.75
    s.render.filepath=str(frames/f'{i:03d}.png');bpy.ops.render.render(write_still=True)
print('Rendered authored throw preview; no engine cloth simulation or projectile preview')
