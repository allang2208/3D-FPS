import bpy,sys
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent))
from render_polish_review import setup,ROOT
from refine_bottle_grip import normalized
OUT=ROOT/'Refinement20260922'
s,c,aim=setup('Idle');s.frame_set(1)
r=next(o for o in s.objects if o.type=='ARMATURE');rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
hand=rest['hand_r'];along=(rest['middle_01_r'].translation-hand.translation).normalized()
across=(rest['index_01_r'].translation-rest['pinky_01_r'].translation).normalized();palm=along.cross(across).normalized()
z=across;x=(along-z*along.dot(z)).normalized();y=z.cross(x).normalized();rot=Matrix((x,y,z)).transposed()
mount=rot.to_4x4();mount.translation=hand.translation+along*.071+palm*.027-rot@Vector((0,0,.136))
relative=normalized(hand).inverted()@mount
with bpy.data.libraries.load(str(ROOT/'Authoring/WitchRebuilt_Bottle.blend'),link=False) as (src,dst):dst.objects=src.objects
for o in dst.objects:
    if o.type!='MESH':continue
    s.collection.objects.link(o);source=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Identity(4)
    for v in o.data.vertices:v.co=source@v.co
    o.modifiers.clear();o.matrix_world=normalized(r.matrix_world@r.pose.bones['hand_r'].matrix)@relative
    for m in o.data.materials:
        m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.22
target=(r.matrix_world@r.pose.bones['hand_r'].matrix).translation
for o in s.objects:
    if o.type=='MESH' and o.name.startswith(('Witch_','WitchRebuilt_Lining')):o.hide_render=True
s.render.resolution_x=850;s.render.resolution_y=650;s.cycles.samples=24;c.data.ortho_scale=.34
c.location=target+Vector((-1,-1,.65));aim(c,target+Vector((0,-.015,-.04)))
s.render.filepath=str(OUT/'grip_closeup.png');bpy.ops.render.render(write_still=True)
