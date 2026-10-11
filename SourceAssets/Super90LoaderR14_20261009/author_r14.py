"""Preserve R12 baked local poses; change only their sampling times.

Every count uses the complete seven-shell source push. No pose/IK reconstruction,
new gun motion, mesh edit, rendering or game run is performed here.
"""
import bpy,json,sys,hashlib,math
from pathlib import Path
from mathutils import Quaternion
O=Path(__file__).parent;S=O.parent;R12=S/'Super90LoaderR12_20261009'
timing=json.loads((O/'timing.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(R12/'Super90_Speedloader_R12.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['SK_Super90'];scene.render.fps=60
sys.path.insert(0,str(S/'M1911RevolverInspect20260927'))
import author_support as support
X=O/'Exports';X.mkdir(exist_ok=True)
families=('vertical','canted','prism','angled')
inputs={fam:json.loads((R12/(fam+'_profiles.json')).read_text()) for fam in families}
rows_by_branch={}
for branch,end in (('normal',170),('empty',206),('cycle',66)):
    name='A_Super90_loader_'+(branch+'_7' if branch!='cycle' else branch)
    rig.animation_data.action=bpy.data.actions[name];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    rows=[]
    for f in range(end+1):
        source=float(f) if branch=='cycle' else timing['source_frames'][f]
        scene.frame_set(math.floor(source),subframe=source-math.floor(source));bpy.context.view_layer.update()
        row={b.name:list(b.matrix_basis.copy().decompose()) for b in rig.pose.bones}
        if rows:
            for n in row:
                if rows[-1][n][1].dot(row[n][1])<0:row[n][1].negate()
        rows.append(row)
    rows_by_branch[branch]=rows
# Remove only actions that will be replaced inside this new Blend. R12 is never saved.
for a in list(bpy.data.actions):
    if a.name.startswith('A_Super90_loader_'):bpy.data.actions.remove(a)
def export(name,rows):
    frames=list(range(len(rows)));support.DURATION=frames[-1]/60
    rig.animation_data_create();support.bake_action(rig,scene,name,rows,frames)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    path=X/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    return path
def sample_track(track,t):
    import bisect
    times=track['times'];values=track['values'];i=max(0,min(len(times)-2,bisect.bisect_right(times,t)-1))
    a=values[i*10:(i+1)*10];b=values[(i+1)*10:(i+2)*10]
    u=max(0,min(1,(t-times[i])/(times[i+1]-times[i])))
    qa=Quaternion((a[6],*a[3:6]));qb=Quaternion((b[6],*b[3:6]))
    if qa.dot(qb)<0:qb.negate()
    q=qa.slerp(qb,u)
    return [a[j]+(b[j]-a[j])*u for j in range(3)]+[q.x,q.y,q.z,q.w]+[a[j]+(b[j]-a[j])*u for j in range(7,10)]
profiles={fam:{'family':fam,'clips':[]} for fam in families}
report=dict(revision='LoaderR14-20261009',source_blend=str(R12/'Super90_Speedloader_R12.blend'),
    source_sha256=hashlib.sha256((R12/'Super90_Speedloader_R12.blend').read_bytes()).hexdigest(),
    method='Unmodified baked R12 poses, monotone common retiming; full push for all counts',runtime_tested=False,clips=[])
ANIM='/Game/Weapons/Super90/Speedloader20261007/Animations/'
for branch in ('normal','empty','cycle'):
    rows=rows_by_branch[branch];end=len(rows)-1
    source_name='A_Super90_loader_'+(branch+'_7' if branch!='cycle' else branch)
    family_clips={}
    for fam in families:
        src=next(c for c in inputs[fam]['clips'] if c['base'].endswith(source_name))
        tracks=[]
        for track in src['tracks']:
            vals=[]
            for f in range(end+1):
                t=(float(f) if branch=='cycle' else timing['source_frames'][f])/60
                vals.extend(sample_track(track,t))
            tracks.append(dict(bone=track['bone'],times=[f/60 for f in range(end+1)],values=vals))
        family_clips[fam]=tracks
    for count in ([0] if branch=='cycle' else range(1,8)):
        name='A_Super90_loader_'+(branch if count==0 else branch+'_'+str(count))
        path=export(name,rows)
        report['clips'].append(dict(name=name,file=str(path),count=count,empty=branch!='normal',duration=end/60,
            contacts=[] if count==0 else [f/60 for f in timing['contacts_frames'][-count:]],
            release=(timing['cycle_release_frame'] if count==0 else timing['release_frame'])/60 if branch!='normal' else None,
            props_visible=None if count==0 else [timing['show_frame']/60,timing['hide_frame']/60],
            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for fam in families:profiles[fam]['clips'].append(dict(base=ANIM+name,duration=end/60,tracks=family_clips[fam]))
        print('R14_PRESERVED',name,end/60,flush=True)
for fam,p in profiles.items():(O/(fam+'_profiles.json')).write_text(json.dumps(p,separators=(',',':')),encoding='utf-8')
rig.animation_data.action=bpy.data.actions['A_Super90_loader_empty_7'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=206;scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Speedloader_R14.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_LOADER_R14_AUTHORED',len(report['clips']),'preserved source clips',flush=True)
