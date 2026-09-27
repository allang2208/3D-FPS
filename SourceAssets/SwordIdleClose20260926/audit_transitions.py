"""User-requested read-only inspection of installed sword handoffs and compression."""
import ast, json, math, sys
from pathlib import Path
import unreal as u

P = Path(__file__).parent
AFTER = '-swordhandoffafter' in u.SystemLibrary.get_command_line().lower()
tree = ast.parse((P/'author_idle_close.py').read_text(encoding='utf-8'))
helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef)
           and node.name in ('add','sub','mul','hadamard','divide','dot','length','unit','cross','inverse',
                            'qmul','rotate','smooth','unpack','relative','compose','asset_path')]
exec(compile(ast.Module(body=helpers, type_ignores=[]), 'idle_math', 'exec'), globals())
FOLDERS = {
    'Standard': '/Game/Weapons/AzureRunesword20260913',
    'LongGrip': '/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations',
}
CLIPS = ['Idle','Walk','Inspect','Equip','Slash1','Slash2','Thrust','PommelStrike','Overhead',
         'HeavyCharge','HeavyRelease','Guard','GuardHit','GuardBreak','WhirlwindV5',
         'TacticalSprint20260921/SprintEnter','TacticalSprint20260921/SprintLoop',
         'TacticalSprint20260921/SprintExit','TacticalSprint20260921/SprintOverhead']
mesh = u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
comp = u.SkeletalMeshComponent(); comp.set_skeletal_mesh_asset(mesh)
names = [str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
parents = {n:str(comp.get_parent_bone(n)) for n in names}
watched = ['WPN_root','hand_r','hand_l','lowerarm_r','lowerarm_l','upperarm_r','upperarm_l']
options = u.AnimPoseEvaluationOptions(); options.optional_skeletal_mesh = mesh
rows = []
report = {'runtime_played':False, 'inspection':'Installed source/compressed poses and C++ handoff paths',
          'families':{}, 'edges':rows}
IDENTITY = {'p':(0,0,0),'q':(0,0,0,1),'s':(1,1,1)}


def angle(a,b):
    return math.degrees(2*math.acos(min(1,abs(dot(unit(a),unit(b))))))


def gap(a,b):
    return {'max_anchor_cm':max(length(sub(a[n]['p'],b[n]['p'])) for n in ('WPN_root','hand_r','hand_l')),
            'max_arm_cm':max(length(sub(a[n]['p'],b[n]['p'])) for n in watched),
            'max_anchor_deg':max(angle(a[n]['q'],b[n]['q']) for n in ('WPN_root','hand_r','hand_l')),
            'bones':{n:{'cm':length(sub(a[n]['p'],b[n]['p'])), 'deg':angle(a[n]['q'],b[n]['q'])} for n in watched}}


for variant,folder in FOLDERS.items():
    assets = {c:u.load_asset(asset_path(folder,c)) for c in CLIPS}
    if any(not a for a in assets.values()):
        raise RuntimeError('Missing animation in '+variant)
    times = {c:a.get_play_length() for c,a in assets.items()}
    old_data = {}
    for c in CLIPS:
        file=P/variant/(c.replace('/','_')+'_before.json')
        if file.exists():old_data[c]=json.loads(file.read_text())
    cache={}
    def pose(c,t,compressed=False,old=False):
        t=times[c] if t=='end' else max(0.,min(times[c],float(t)))
        key=(c,round(t,8),compressed,old)
        if key in cache:return cache[key]
        options.evaluation_type=u.AnimDataEvalType.COMPRESSED if compressed else u.AnimDataEvalType.SOURCE
        evaluated=u.AnimPoseExtensions.get_anim_pose_at_time(assets[c],t,options)
        world={n:unpack(u.AnimPoseExtensions.get_bone_pose(evaluated,n,u.AnimPoseSpaces.WORLD)) for n in names}
        if old and c in old_data:
            data=old_data[c];f=min(len(data['samples'])-1,round(t/times[c]*data['frames']))
            keys=data['samples'][f]['bones']
            for n in names:
                if n in keys:world[n]=compose(world.get(parents[n],IDENTITY),keys[n])
        cache[key]=world;return world
    def edge(label,a,ta,b,tb,policy):
        new=gap(pose(a,ta),pose(b,tb));old=gap(pose(a,ta,old=True),pose(b,tb,old=True))
        rows.append({'variant':variant,'transition':label,'from':[a,ta],'to':[b,tb],
            'runtime_policy':policy,'new':new,'before_idle_change':old,
            'added_anchor_cm':new['max_anchor_cm']-old['max_anchor_cm']})
    for c in ('Idle','Walk'):
        edge(c+' loop',c,'end',c,0,'loop without capture')
    for c in ('Inspect','Equip','Slash1','Slash2','Thrust','PommelStrike','Overhead','HeavyRelease','GuardBreak','WhirlwindV5'):
        edge(c+' -> Idle',c,'end','Idle',0,'grip-constrained capture' if AFTER else 'Inspect captured; others direct SetClip')
    for c in ('Slash1','Slash2','Thrust','PommelStrike','HeavyCharge','Guard'):
        edge('Idle -> '+c,'Idle',0,c,0,'grip-constrained capture, capped before damage' if AFTER else 'direct SetClip')
    edge('Guard lower -> Idle','Guard',0,'Idle',0,'reverse sample to zero')
    edge('Charge cancel -> Idle','HeavyCharge',0,'Idle',0,'reverse sample to zero')
    edge('Full charge -> HeavyRelease','HeavyCharge',2.,'HeavyRelease',0,'direct SetClip')
    edge('Guard hold -> GuardHit','Guard',.20,'GuardHit',0,'captured over 60 ms' if AFTER else 'direct SetClip')
    edge('GuardHit -> Guard hold','GuardHit','end','Guard',.20,'direct SetClip then .20 sample')
    edge('Guard hold -> GuardBreak','Guard',.20,'GuardBreak',0,'captured over 60 ms' if AFTER else 'direct SetClip')
    edge('GuardBreak stun release -> Idle','GuardBreak',1.5,'Idle',0,'captured when gameplay stun expires' if AFTER else 'gameplay stun expires, direct SetClip')
    edge('Early guard raise -> GuardHit','Guard',.04,'GuardHit',0,'captured over 60 ms' if AFTER else 'direct SetClip')
    edge('Cloven instant counter from guard','Guard',.20,'HeavyRelease',0,'UNRESOLVED: immediate damage from zero, authored pose switch retained')
    pref='TacticalSprint20260921/'
    edge('Idle -> SprintEnter','Idle',0,pref+'SprintEnter',0,'captured')
    edge('SprintEnter -> SprintLoop',pref+'SprintEnter','end',pref+'SprintLoop',0,'captured')
    edge('SprintLoop loop',pref+'SprintLoop','end',pref+'SprintLoop',0,'loop')
    edge('SprintExit -> Idle',pref+'SprintExit','end','Idle',0,'captured')
    edge('SprintOverhead -> Idle',pref+'SprintOverhead','end','Idle',0,'captured')
    compression=[]
    for c in CLIPS:
        for t in (0.,min(.20,times[c]),max(0.,times[c]-.28),times[c]):
            compression.append({'clip':c,'t':t,**gap(pose(c,t),pose(c,t,compressed=True))})
    authoring_grid=[]
    for c,a in assets.items():
        file=P/variant/(c.replace('/','_')+'_keys.json')
        if file.exists():
            data=json.loads(file.read_text())
            m=a.get_editor_property('data_model_interface')
            authoring_grid.append({'clip':c,'authored_frames':data['frames'],
                                   'model_frames':m.get_number_of_frames(),
                                   'rate':str(m.get_frame_rate())})
    report['families'][variant]={'durations':times,'compression':compression,'authoring_grid':authoring_grid,
        'poses':{c:{'start':{n:pose(c,0)[n] for n in watched},
                    'end':{n:pose(c,'end')[n] for n in watched}} for c in CLIPS}}
    print('SWORD_HANDOFF_AUDITED',variant,flush=True)
suffix='after' if AFTER else 'before'
out=P/('handoff_audit_'+suffix+'.json')
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
for row in sorted(rows,key=lambda x:x['added_anchor_cm'],reverse=True)[:12]:
    print('HANDOFF',row['variant'],row['transition'],'new_cm',round(row['new']['max_anchor_cm'],4),
          'old_cm',round(row['before_idle_change']['max_anchor_cm'],4),flush=True)
print('SWORD_HANDOFF_AUDIT_SAVED',str(out),flush=True)
