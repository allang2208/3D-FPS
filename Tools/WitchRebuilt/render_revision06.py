import bpy,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent))
from render_polish_review import setup,ROOT
from refine_bottle_grip import normalized
OUT=ROOT/'Revision06'
for role,times in [('Idle',[0]),('ThrowPoisonBottle',[.42,.75,.92])]:
    s,c,aim=setup(role);r=next(o for o in s.objects if o.type=='ARMATURE');rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
    hand=rest['hand_r'];along=(rest['middle_01_r'].translation-hand.translation).normalized();across=(rest['index_01_r'].translation-rest['pinky_01_r'].translation).normalized();palm=along.cross(across).normalized()
    z=across;x=(along-z*along.dot(z)).normalized();y=z.cross(x).normalized();rot=Matrix((x,y,z)).transposed()
    mount=rot.to_4x4();mount.translation=hand.translation+along*.071+palm*.027-rot@Vector((0,0,.136));relative=normalized(hand).inverted()@mount
    with bpy.data.libraries.load(str(ROOT/'Authoring/WitchRebuilt_Bottle.blend'),link=False) as (src,dst):dst.objects=src.objects
    bottles=[]
    for o in dst.objects:
        if o.type!='MESH':continue
        s.collection.objects.link(o);source=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Identity(4)
        for v in o.data.vertices:v.co=source@v.co
        o.modifiers.clear();bottles.append(o)
        for m in o.data.materials:
            m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.22
    c.location=(-3,-5,2.05);aim(c,(0,-.05,1.13));c.data.ortho_scale=2.15
    s.render.resolution_x=850;s.render.resolution_y=950;s.cycles.samples=24
    for t in times:
        s.frame_set(round(t*s.render.fps)+1)
        for o in bottles:o.hide_render=role=='ThrowPoisonBottle' and t>=.75;o.matrix_world=normalized(r.matrix_world@r.pose.bones['hand_r'].matrix)@relative
        s.render.filepath=str(OUT/f'candidate06_{role}_{round(t*100):03d}.png');bpy.ops.render.render(write_still=True)
print('Scoped upper garment and right-arm source poses rendered; not a Chaos simulation preview')
