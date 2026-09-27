"""V16: carry the arrow into the string during the existing 0.20 s entry."""
from pathlib import Path
P=Path(__file__).parent
s=(P.parent/'BowFlex20260927/generated_actions.py').read_text(encoding='utf8')
def replace(a,b):
    global s
    if a not in s: raise RuntimeError('Authoring source changed: '+a[:80])
    s=s.replace(a,b)
replace("R=Matrix.Rotation(math.pi/2,3,'Z')", "DURATIONS.update(QuickNock=.2,ChainNock=.2)\nEXPORT_ROLES=('Nock','QuickNock','ChainNock')\nR=Matrix.Rotation(math.pi/2,3,'Z')")
replace("    if role=='Nock':return smooth((t/DURATIONS[role]-.35)/.35)","    if role in ('Nock','QuickNock','ChainNock'):return smooth((t/DURATIONS[role]-.35)/.47)")
replace("    if role=='Nock':\n        result={}","    if role in ('Nock','QuickNock','ChainNock'):\n        result={}")
replace("    if role=='Release':\n        release=smooth(t/.085)","""    if role in ('QuickNock','ChainNock'):
        lift=smooth(phase/.90)
        raised=lift if role=='QuickNock' else 1.
        # The chained take keeps the bow raised instead of first visiting idle.
        start_bow=idle_bow_frame() if role=='QuickNock' else bow_frame(1.)
        bow=blend_frame(start_bow,bow_frame(0.),lift)
        support=0.
        nock=bow@BRACE
        start=RIGHT_PARK if role=='QuickNock' else bow_frame(1.)@ANCHOR
        keys=[(0.,start),(.30,RIGHT_PARK+Vector((2,2,-2))),
              (.58,Vector((27,14,-26))),(.78,nock+Vector((1,5,-4))),(.90,nock),(1.,nock)]
        right=hand_path(keys,phase) if phase<.90 else nock.copy()
    if role=='Release':
        release=smooth(t/.085)""")
replace("    world['bow_nock']=mat(right if role=='Nock' else nock)","""    if role in ('Nock','QuickNock','ChainNock'):
        # Marker rotation is the carried arrow's axis, with +X toward its tip.
        # Roll follows the bow; align to the actual rest only near contact.
        seat=.82 if role=='Nock' else .90
        carry=Vector((1.,-.08,.22)).normalized()
        aligned=(bow@Vector((-3.5,-3.9,2.6))-right).normalized()
        orient=carry.rotation_difference(aligned)
        axis=Quaternion().slerp(orient,smooth((phase-.48)/(seat-.48)))@carry
        frame=limb_frame(axis,bow.to_3x3()@Vector((0,1,0)))
        world['bow_nock']=mat(right,frame)
    else:world['bow_nock']=mat(nock)""")
replace('for role,seconds in DURATIONS.items():','for role in EXPORT_ROLES:\n    seconds=DURATIONS[role]')
replace("rig.animation_data.action=bpy.data.actions['A_Bow_Idle'];scene.frame_start=0;scene.frame_end=240;scene.frame_set(0)","rig.animation_data.action=bpy.data.actions['A_Bow_QuickNock'];scene.frame_start=0;scene.frame_end=24;scene.frame_set(0)")
replace('Bow_EffortReleaseV15.blend','Bow_QuickNockV16.blend')
replace("'durations':DURATIONS", "'durations':{r:DURATIONS[r] for r in EXPORT_ROLES},'quick_nock_contact_phase':.90,'arrow_visible_phase':.34")
replace("'one_handed_idle_roles':['Idle','Ready','Equip','Run']", "'one_handed_idle_roles':['Idle','Ready','Equip','Run'],'source_actions':'ElasticV15','reference_detail':'BV1jGdDBkEkc 37.6-37.8 and 44.4-44.7: short visible hand return; extraction outside view'")
(P/'generated_actions.py').write_text(s,encoding='utf8')
exec(compile(s,str(P/'generated_actions.py'),'exec'),{'__file__':str(P/'generated_actions.py')})
