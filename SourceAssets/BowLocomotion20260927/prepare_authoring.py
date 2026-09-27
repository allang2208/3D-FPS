"""Create a self-contained V23 authoring source from the accepted V21 contact solver."""
from pathlib import Path
P=Path(__file__).parent
source=(P.parent/'BowNockContinuity20260927/author_actions.py').read_text(encoding='utf8')
# Freeze the source solver in this task; subsequent rebuilds use generated_actions.py.
source=source.replace('FPS=240','FPS=120')
start=source.index('EXPORT_ROLES=')
end=source.index('\n',start)
source=source[:start]+"EXPORT_ROLES=('Walk','Run','LoadedWalk','LoadedRun','LoadedIdle')\nDURATIONS.update({r:1. for r in EXPORT_ROLES}); DURATIONS['LoadedIdle']=2.8"+source[end:]
source=source.replace('def pose(role,t):\n', '''def pose(role,t):
    gait_role=role
    gait_phase=t/DURATIONS[role]
    loaded=gait_role.startswith('Loaded')
    running=gait_role in ('Run','LoadedRun')
    breathing=gait_role=='LoadedIdle'
    role='Draw' if loaded else 'Idle'
    t=0.
''',1)
source=source.replace('    left_target=bow@GRIP_CONTACT@left_in_grip', '''    # Closed periodic curves: body lift occurs twice per stride, lateral sway
    # once. The wrist arrives after the shoulders and before the elbow settles.
    w=2*math.pi*gait_phase
    amount=(.62 if running else .72) if loaded else 1.
    shoulder_motion={s:Vector((0,0,0)) for s in ('l','r')}
    pole_motion={s:Vector((0,0,0)) for s in ('l','r')}
    if breathing:
        off=Vector((.075*math.sin(w),.035*math.sin(w-.3),.10*math.sin(w)))
        rot=Matrix.Rotation(math.radians(.09*math.sin(w-.3)),3,'X')
    else:
        off=Vector(((-1.20 if running else -.48)*math.sin(2*w-.28),
                    (1.65 if running else .75)*math.sin(w-.22),
                    (.92 if running else .42)*math.cos(2*w-.38)
                    +(.16 if running else .08)*math.sin(4*w-.76)))*amount
        pitch=(1.35 if running else .55)*math.sin(2*w-.45)*amount
        yaw=(1.75 if running else .70)*math.sin(w-.38)*amount
        roll=(2.25 if running else 1.05)*math.sin(w-.55)*amount
        rot=Matrix.Rotation(math.radians(yaw),3,'Z')@Matrix.Rotation(math.radians(pitch),3,'Y')@Matrix.Rotation(math.radians(roll),3,'X')
        if running:
            # Carry nearer the body and lower, not across the central sight line.
            off+=Vector((-5.0,2.5,-7.0) if loaded else (-6.,3.5,-10.))
            rot=rot@Matrix.Rotation(math.radians(-8. if loaded else -10.),3,'X')
        for side,sign in (('l',1),('r',-1)):
            gain=(1.45 if running else .65)*amount
            shoulder_motion[side]=Vector((.26*sign*math.sin(w+.18),.30*math.sin(w),.24*math.cos(2*w)))*gain
            pole_motion[side]=Vector((.45*sign*math.sin(w-.55),.70*sign*math.sin(w-.45),.48*math.cos(2*w-.60)))*gain
        if not loaded:
            right+=Vector(((3.5 if running else 1.8)*math.sin(w+.35),
                           (.65 if running else .3)*math.sin(w-.20),
                           (1.4 if running else .6)*math.cos(w-.1)))
    bow=mat(bow.translation+off,rot@bow.to_3x3())
    nock=bow@BRACE
    if loaded:right=nock.copy()
    left_target=bow@GRIP_CONTACT@left_in_grip''',1)
source=source.replace('        world[clav].translation+=shoulder_target-',
    '        shoulder_target+=shoulder_motion[side]\n        world[clav].translation+=shoulder_target-',1)
source=source.replace('        bend=(pole-shoulder)',
    '        pole+=pole_motion[side]\n        bend=(pole-shoulder)',1)
source=source.replace("bpy.data.actions['A_Bow_QuickNock'];scene.frame_start=0;scene.frame_end=round(.2*FPS)",
    "bpy.data.actions['A_Bow_Walk'];scene.frame_start=0;scene.frame_end=FPS")
source=source.replace('Bow_NockContinuityV21.blend','Bow_LocomotionV23.blend')
start=source.index("(P/'authoring.json').write_text")
source=source[:start]+'''(P/'authoring.json').write_text(json.dumps({
    'fps':FPS,'durations':{r:DURATIONS[r] for r in EXPORT_ROLES},
    'contact_solver':'V21 native V7 arm lengths, accepted left grasp and right hook',
    'curves':'Original authored two-step cycles; offset wrist, shoulder and elbow phases',
    'loop_phase':'distance driven at runtime; no locomotion root translation',
    'brace_nock_cm':list(BRACE),'runtime_tested':False},indent=2),encoding='utf8')
'''
(P/'generated_actions.py').write_text(source,encoding='utf8')

path=P/'import_assets.py';s=path.read_text(encoding='utf8')
s=s.replace('V21 nocking clips','V23 locomotion clips').replace('NockContinuityV21','LocomotionV23').replace('BOW_NOCK_CONTINUITY_V21','BOW_LOCOMOTION_V23')
s=s.replace("E=u.EditorAssetLibrary;", "if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():\n    raise RuntimeError('Stop Play before saving bow locomotion assets')\nE=u.EditorAssetLibrary;")
path.write_text(s,encoding='utf8')
path=P/'run_import.ps1';s=path.read_text(encoding='utf8').replace('bow-surface-repair-20260927-import.log','bow-locomotion-v23-import.log')
s=s.replace('Four bow surfaces saved in existing paths; no catalog switch required.','Bow locomotion animation import finished; activate saved clips next.')
path.write_text(s,encoding='utf8')
print('BOW_LOCOMOTION_AUTHORING_PREPARED')
