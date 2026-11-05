"""First-person and hand close-up views of the published M24 quick melee."""
from pathlib import Path
O=Path(__file__).resolve().parent
source=(O.parent/'M24QuickMeleeGrip20261104/preview.py').read_text().split("if '--layout' in sys.argv:")[0]
source=source.replace("code=(O/'author.py').read_text().split('# Read physical assembly geometry')[0]", "code=(O/'common.py').read_text()")
source=source.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_RightHandR3_Editable.blend')
exec(compile(source,'saved native-skin preview','exec'))
for family in ('skeleton_base','skeleton_mag10_balanced','skeleton_mag10_stable'):
    folder=OUT/family
    folder.mkdir(exist_ok=True)
    for i in range(28):
        for view in ('fps','grip'):
            draw(family,i/30,view,folder/f'{i:03d}_{view}.png')
print('M24_SAVED_RIGHT_PREVIEW_COMPLETE',flush=True)
