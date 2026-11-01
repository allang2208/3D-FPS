"""Offline source preview; does not launch UE or simulate its camera feedback."""
from pathlib import Path
import ast
O=Path(__file__).resolve().parent
exec(compile((O/'inspect.py').read_text().split('\nfolder=')[0],'preview_setup','exec'))
tree=ast.parse((O/'review.py').read_text())
injection=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='injection' for v in n.targets))
exec(compile(injection,'edited_pose','exec'))
s.render.resolution_x=640;s.render.resolution_y=360
folder=O/'Preview';folder.mkdir(exist_ok=True)
for i in range(55):
    t=i/60;row,_=pose('quick_melee',t)
    r.matrix_world=Matrix.Identity(4);set_pose(row);morphs_full()
    for view in ('fps','hand'):
        if view=='fps':
            r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
        else:
            r.matrix_world=Matrix.Identity(4)
            root=row['WPN_root']@rest['WPN_root'].inverted()
            target=row['hand_r'].translation+root.to_3x3()@Vector((.03,.02,.04))
            cam.location=target+root.to_3x3()@Vector((.24,-.12,-.08))
            cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
            cam.data.type='ORTHO';cam.data.ortho_scale=.32
        s.render.filepath=str(folder/(f'{i:03d}_{view}.png'));bpy.ops.render.render(write_still=True)
print('M24_CLUB_SOURCE_PREVIEW_READY',flush=True)
