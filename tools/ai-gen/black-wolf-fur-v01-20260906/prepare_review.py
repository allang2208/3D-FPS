from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
P=Path('E:/3d/black-wolf-fur-preview-20260906');P.mkdir(exist_ok=True)
shutil.copy2(R.parents[2]/'assets/models/wolf_quaternius.gltf',P/'source.gltf')
if (R/'black-wolf-fur-v01.glb').exists():shutil.copy2(R/'black-wolf-fur-v01.glb',P/'wolf.glb')
shutil.copy2(R/'render_review.gd',P/'render_review.gd')
(P/'project.godot').write_text('''config_version=5
[application]
config/name="Black wolf fur material review"
config/features=PackedStringArray("4.7", "Forward Plus")
[display]
window/size/viewport_width=1100
window/size/viewport_height=800
window/size/window_width_override=1100
window/size/window_height_override=800
window/vsync/vsync_mode=0
[rendering]
rendering_device/driver.windows="d3d12"
anti_aliasing/quality/msaa_3d=2
''',encoding='utf-8')
print('BLACK_WOLF_PREVIEW_READY',P)
