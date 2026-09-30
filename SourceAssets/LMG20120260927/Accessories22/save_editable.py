"""Save editable native grip pose scenes, retaining V7 skin and 201 topology."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=json.loads((O/'sources.json').read_text());bones=S['201']['bones']
full=json.loads((O.parent/'PKMFK19/input.json').read_text())['clips']['201_idle']['poses'][0]
reflect=Matrix.Diagonal((1.,-1.,1.))
def ue(v):
    q=v['q'];return Matrix.LocRotScale(Vector(v['p']),Quaternion((q[3],*q[:3])),Vector(v['s']))
def converted(m):
    p,q,s=m.decompose();n=(reflect@q.to_matrix()@reflect).to_4x4()@Matrix.Diagonal((*tuple(v/100 for v in s),1));n.translation=reflect@p*.01;return n
for family in ['vertical','canted','prism','angled']:
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/'PKMFK19/LMG201_PKMFK19_Editable.blend'))
    rig=bpy.data.objects['201_Native_FK'];rig.animation_data_clear()
    for a in list(bpy.data.actions):bpy.data.actions.remove(a)
    keys=json.loads((O/'Keys'/(family+'_idle.json')).read_text())
    local={n:ue(keys[n][0] if n in keys else v['local']) for n,v in full.items()}
    # Current collected idle supplies the weapon/root and unchanged arm parents.
    current=json.loads((O/'Sources/201_idle.json').read_text())['poses'][0]
    local.update({n:ue(v['local']) for n,v in current.items() if n not in keys})
    worlds={}
    def evaluate(n):
        if n not in worlds:
            p=bones[n]['parent'];worlds[n]=evaluate(p)@local[n] if p in local else local[n]
        return worlds[n]
    posed={n:converted(evaluate(n)) for n in local};rest={n:rig.data.bones[n].matrix_local.copy() for n in local}
    rig.animation_data_create();a=bpy.data.actions.new('LMG201_'+family+'_idle_NativeFK');rig.animation_data.action=a
    for n,m in posed.items():
        p=bones[n]['parent'];inv=(rest[p].inverted()@rest[n]).inverted() if p in rest else rest[n].inverted()
        basis=inv@(posed[p].inverted()@m if p in posed else m);loc,q,scale=basis.decompose();b=rig.pose.bones[n]
        b.location=loc;b.rotation_mode='QUATERNION';b.rotation_quaternion=q;b.scale=scale
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=1,group=n)
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/('SM_LMG201_'+family+'.fbx')))
    for ob in set(bpy.data.objects)-before:
        if ob.type!='MESH':continue
        ob.data.transform(rig.data.bones['WPN_root'].matrix_local@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
        ob.parent=rig;group=ob.vertex_groups.new(name='WPN_root');group.add(list(range(len(ob.data.vertices))),1.,'REPLACE')
        ob.modifiers.new('Native weapon attachment','ARMATURE').object=rig
    rig['MotionSource']=S['donors'][family]['asset'];rig['AuthoringKeys']=str(O/'Keys');rig['RuntimeFamily']='/Game/Weapons/LMG201/Accessories22/Animations/'+family
    rig['Method']='Complete native FK transfer. No IK/twist rewrite. Full 14-clip editable local tracks are in Keys/ and installed AnimSequences.'
    bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=6
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(O/('LMG201_'+family+'_Editable.blend')))
    print('LMG20122_EDITABLE',family,flush=True)
