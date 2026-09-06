"""Create a small isolated Godot review project and export checks."""
from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
P=Path('E:/3d/foreman-attack-v09-preview-20260906')
P.mkdir(exist_ok=True)
for source,name in [(R/'foreman-attack-v09.glb','v09.glb'),(R.parent/'foreman-retopo-v08-20260906/foreman-retopo-v08.glb','v08.glb')]:
    shutil.copy2(source,P/name)
shutil.copy2(R/'render_review.gd',P/'render_review.gd')
(P/'project.godot').write_text('''config_version=5
[application]
config/name="Foreman attack comparison"
config/features=PackedStringArray("4.7", "Forward Plus")
[display]
window/size/viewport_width=960
window/size/viewport_height=720
window/size/window_width_override=960
window/size/window_height_override=720
window/vsync/vsync_mode=0
[rendering]
rendering_device/driver.windows="d3d12"
anti_aliasing/quality/msaa_3d=2
''',encoding='utf-8')
source=R.parent/'foreman-retopo-v08-20260906'
for file in ['check_export.py','check_motion.py']:
    text=(source/file).read_text(encoding='utf-8').replace('foreman-retopo-v08.glb','foreman-attack-v09.glb').replace('FOREMAN_V04_REVIEW','FOREMAN_V09_REVIEW')
    if not (R/file).exists():
        (R/file).write_text(text,encoding='utf-8')
print('PREVIEW_PROJECT_READY',P)
