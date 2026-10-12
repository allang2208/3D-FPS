"""Pose-only diagnosis on the saved source skin, not a gameplay screenshot."""
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
source=(root/'Tools/PlayerBody/compare_melee_source_skin20261010.py').read_text()
prefix=source.split('versions = {')[0]
ns={}
exec(compile(prefix,'source-skin-helpers','exec'),ns)
ns['out']=root/'SourceAssets/ThirdPersonDashArm20261010'
ns['versions']={
    'Recovery / before':root/'SourceAssets/ThirdPersonMeleeRegression20261010/adapted-actions.json',
    'Bounded wrist fit':ns['out']/'candidate-actions.json'}
import sys
ns['cases']=[('DashOverhead',p) for p in ([.10,.27,.90] if '--phases' in sys.argv else [.4,.4,.4])]
tail=source[source.index('fig, axes ='):]
tail=tail.replace("R.from_euler('z', 18 if col < 2 else 165, degrees=True)","R.from_euler('xz', [25, [18, 100, 250][col]], degrees=True)")
tail=tail.replace("source-skin-comparison.png","candidate-phases.png" if '--phases' in sys.argv else "candidate-skin.png")
tail=tail.replace("ax.set_ylim(72, 185)","ax.set_ylim(25, 165)")
exec(compile(tail,'dash-skin-render','exec'),ns)
