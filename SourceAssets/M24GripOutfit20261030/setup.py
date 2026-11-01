from pathlib import Path
exec(compile((Path(__file__).parent.parent/'M24IdleArm20261030/inspect.py').read_text().split("\nif __name__=='__main__':")[0],'setup','exec'))
import copy
roles=json.loads((O/'roles_before.json').read_text())
node=next(n for n in ast.parse((O.parent/'M24IdleArm20261030/author_profiles.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='local_pose')
exec(compile(ast.unparse(node),'local_pose','exec'))
if (O/'game_context.json').exists():
    # Reproduce FRifleHipFraming with the currently saved M4 ruler and M24
    # profile. Historical calibration files can drift when that ruler changes.
    ctx=json.loads((O/'game_context.json').read_text())['m4_reference'];refrow={};index={v['index']:n for n,v in ctx['bones'].items()}
    for n,v in ctx['bones'].items():
        loc=Matrix.LocRotScale(*unpack(ctx['poses'][n]));parent=index.get(v['parent']);refrow[n]=refrow[parent]@loc if parent else loc
    def axes(forward,up):
        x=forward.normalized();z=(up-x*up.dot(x)).normalized();return Matrix((x,z.cross(x),z)).transposed()
    base=pose('idle',0)[0];reflect=K.to_3x3();cm=Matrix.Diagonal((100,-100,100))
    refaxis=axes(refrow['WPN_FrontSight'].translation-refrow['WPN_RearSight'].translation,refrow['WPN_root'].to_quaternion()@Vector((0,0,1)))
    axis=axes(cm@(base['WPN_FrontSight'].translation-base['WPN_RearSight'].translation),reflect@base['WPN_root'].to_3x3()@reflect@Vector((0,-1,0)))
    rz=Matrix.Rotation(math.pi/2,3,'Z');rotation=rz@refaxis@axis.inverted()
    target=Vector((0,7,-7))+rz@refrow['hand_r'].translation+Vector((23.219236,1.379742,1.296371))
    C=(rotation@cm).to_4x4();C.translation=target-rotation@cm@base['hand_r'].translation
    (O/'current_camera_frame.json').write_text(json.dumps([list(v) for v in C]))
with bpy.data.libraries.load(str(O.parent/'M24AdvancedAction20261029/FullBodyV3/M24_AdvancedAction_FullBodyV3.blend'),link=False) as (src,dst):
    dst.objects=['M24_AdvancedAction_DetailBody']
advanced=dst.objects[0];s.collection.objects.link(advanced);advanced.parent=None
advanced.color=(.16,.19,.22,1)
advanced_rest=advanced.matrix_world.copy()
def place(row):
    set_pose(row)
    advanced.matrix_world=r.matrix_world@row['WPN_root']@rest['WPN_root'].inverted()@advanced_rest
def view(row,path,mode='fps'):
    if mode=='fps':
        r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
    else:
        r.matrix_world=Matrix.Identity(4);root=row['WPN_root']@rest['WPN_root'].inverted();target=row['thumb_02_l'].translation
        off=Vector((-.24,-.02,.10)) if mode=='thumb' else Vector((.30,-.12,.15));cam.location=target+root.to_3x3()@off
        cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.20
    # set_pose clears the rig transform; restore it after evaluation.
    matrix=r.matrix_world.copy();set_pose(row);r.matrix_world=matrix
    advanced.matrix_world=matrix@row['WPN_root']@rest['WPN_root'].inverted()@advanced_rest
    s.render.resolution_x=800;s.render.resolution_y=540;s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
