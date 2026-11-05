"""Focused right-hand views for the user's twist/contact review."""
from pathlib import Path
O=Path(__file__).resolve().parent
source=(O.parent/'M24QuickMeleeGrip20261104/preview.py').read_text().split("if '--layout' in sys.argv:")[0]
source=source.replace("code=(O/'author.py').read_text().split('# Read physical assembly geometry')[0]", "code=(O/'common.py').read_text()")
start=source.index("saved=O/'saved_motion.json.gz'");end=source.index("OUT=O/'GIF'")
replacement="""saved=O/'quick_melee_patch.json.gz'
candidate=json.load(gzip.open(saved,'rt'))
for family,clip in candidate.items():
    D['profiles'][family]['clips']=[clip if v['base']==clip['base'] else v for v in D['profiles'][family]['clips']]
"""
source=source[:start]+replacement+source[end:]
source=source.replace("OUT=O/'GIF'", "OUT=O/'Review'")
source=source.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_RightHandR3_Editable.blend')
exec(compile(source,'candidate right-hand view','exec'))
transition_only='--transition' in sys.argv
for family in ('skeleton_base','skeleton_mag10_balanced'):
    folder=OUT/family;folder.mkdir(exist_ok=True)
    for t in ((7/60,.125,8/60,.25) if transition_only else (.08,.15,.25,.325,.55,.65)):
        draw(family,t,'grip',folder/f'{t:.3f}_grip.png')
        row=pose(family,t);root=row['WPN_root']@rest['WPN_root'].inverted()
        target=(row['hand_r'].translation+row['middle_02_r'].translation)*.5
        cam.location=target+root.to_quaternion()@Vector((-.26,-.12,-.09))
        cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.38
        s.render.filepath=str(folder/f'{t:.3f}_palm.png');bpy.ops.render.render(write_still=True)
    if not transition_only:
        for t in (.25,.55):draw(family,t,'arms',folder/f'{t:.3f}_arms.png')
print('M24_RIGHT_FOCUSED_RENDER_COMPLETE',flush=True)
