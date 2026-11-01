"""Targeted source/UE compressed-pose visual review, explicitly requested."""
from pathlib import Path
exec(compile((Path(__file__).parent.parent/'M24QuickMeleeContact20261028/library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
import gzip,numpy as np,sys
from mathutils.bvhtree import BVHTree
label=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'Before'
folder=O/'Review'/label;folder.mkdir(parents=True,exist_ok=True)
source=O/'Review/compressed.json.gz' if label in ('Saved','Final','AnatomyFinal') else O/'authored.json.gz'
if label=='AnatomyPrevious':source=O/'AnatomyBefore/compressed.json.gz'
if label in ('Corrected','Final','AnatomyFinal','AnatomyPrevious'):
    blend_path=O/('AnatomyBefore/M24_Bipod_Hands_Editable.blend' if label=='AnatomyPrevious' else 'M24_Bipod_Hands_Editable.blend')
    bpy.ops.wm.open_mainfile(filepath=str(blend_path),use_scripts=False)
    s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig']
with gzip.open(source,'rt') as f:data=json.load(f)
rate=data['rate'];skin=bpy.data.objects['M24_V9_BareArms'];r.matrix_world=Matrix.Identity(4)
code=(O.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
tree=ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full')
exec(compile(ast.unparse(node),'morphs','exec'))
with bpy.data.libraries.load(str(O.parent/'M24Bipod20261029/M24_Bipod_Editable.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.startswith('M24Bipod_')]
parts=dst.objects
for ob in parts:s.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.color=(.7,.43,.13,1)
for n in ('M24_silencer','M24_ExtraScope_Lowpoly','M24_Laser_Lowpoly','M24_LaserHolder_Lowpoly','M24_bullet','M24_Magazine10'):
    bpy.data.objects[n].hide_render=True
bpy.data.objects['M24_clip'].hide_render=False
geo=json.loads((O/'geometry.json').read_text())
pivots=[K.to_3x3()@Vector(geo['parts'][k]['pivot_cm'])/100 for k in ('LegA','LegB')]
tips=[K.to_3x3()@Vector(v)/100 for v in geo['tips_cm']]
closed=[tips[i].normalized().rotation_difference(Vector((-.005 if i==0 else .005,tips[i].length,0)).normalized()) for i in (0,1)]
def sample_pose(t,family='base'):
    frames=data['clips'][family]['frames'];f=min(t*rate,len(frames)-1);i=min(int(f),len(frames)-2);w=f-i;row={}
    for j,n in enumerate(names):
        a,b=unpack(frames[i][j]),unpack(frames[i+1][j]);local=K@Matrix.LocRotScale(a[0].lerp(b[0],w),a[1].slerp(b[1],w),a[2].lerp(b[2],w))@K
        row[n]=row[parents[n]]@local if parents[n] else local
    return row
def set_pose(row,t,frame=Matrix.Identity(4),family='base'):
    r.matrix_world=frame;r.animation_data_clear()
    for n,m in row.items():
        local=row[parents[n]].inverted()@m if parents[n] else m;r.pose.bones[n].matrix_basis=local_rest[n].inverted()@local
    root=frame@row['WPN_root']@rest['WPN_root'].inverted()
    for ob in parts:
        i=0 if '_LegA_' in ob.name else 1 if '_LegB_' in ob.name else -1
        q=closed[i].slerp(Quaternion(),ease((t-.12)/.18)) if i>=0 else Quaternion()
        ob.matrix_world=root@Matrix.LocRotScale(pivots[i] if i>=0 else Vector(),q,Vector((1,1,1)))
    bpy.context.view_layer.update();morphs_full()
    if label in ('Corrected','Final','AnatomyFinal','AnatomyPrevious'):
        curves=json.loads((O/('AnatomyBefore/elbow_curves.json' if label=='AnatomyPrevious' else 'elbow_curves.json')).read_text())
        saved=data['clips'][family]
        for n,c in curves.items():
            times,weights=(saved['curve_times'],saved['curve_weights'][n]) if n in saved.get('curve_weights',{}) else (c['times'],c['values'])
            skin.data.shape_keys.key_blocks[n].value=float(np.interp(t,times,weights))
        bpy.context.view_layer.update()

metrics=[];previous=None
for i in range(193):
    t=i/400;row=sample_pose(t)
    U=row['lowerarm_l'].translation-row['upperarm_l'].translation;L=row['hand_l'].translation-row['lowerarm_l'].translation
    f=row['middle_01_l'].translation-row['hand_l'].translation
    local={n:row[parents[n]].inverted()@m if parents[n] else m for n,m in row.items()}
    jump=max((math.degrees(2*math.acos(min(1,abs(previous[n].normalized().dot(local[n].to_quaternion().normalized()))))) for n in names if n.endswith('_l')),default=0) if previous else 0
    previous={n:m.to_quaternion() for n,m in local.items()}
    rel=row['lowerarm_l'].to_quaternion().inverted()@row['hand_l'].to_quaternion()@(rest['lowerarm_l'].to_quaternion().inverted()@rest['hand_l'].to_quaternion()).inverted()
    if rel.w<0:rel=-rel
    ax=rest['lowerarm_l'].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
    roll=math.degrees(2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(ax),rel.w))
    metrics.append({'t':t,'elbow':angle(U,L),'wrist_bend':angle(L,f),'roll':roll,'angular_step':jump,
                    'hand_camera_cm':list(C@row['hand_l'].translation),'elbow_camera_cm':list(C@row['lowerarm_l'].translation)})
(folder/'metrics.json').write_text(json.dumps(metrics,indent=2))
s.render.resolution_x=720;s.render.resolution_y=480
for t in (0,.06,.12,.18,.24,.30,.36,.44):
    row=sample_pose(t)
    for view in ('fps','side','hand'):
        if view=='fps':
            set_pose(row,t,cs@C);cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
        else:
            set_pose(row,t);root=row['WPN_root']@rest['WPN_root'].inverted()
            target=row['hand_l'].translation+root.to_3x3()@Vector((.015,.025,.01)) if view=='hand' else (row['hand_l'].translation+row['upperarm_l'].translation)*.5
            offset=Vector((-.26,.06,.18)) if view=='hand' else Vector((-.5,-.14,.20))
            cam.location=target+root.to_3x3()@offset;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.25 if view=='hand' else .65
        s.render.filepath=str(folder/(f'{t:.3f}_{view}.png'));bpy.ops.render.render(write_still=True)
print('BIPOD_REVIEW_READY',label,flush=True)
