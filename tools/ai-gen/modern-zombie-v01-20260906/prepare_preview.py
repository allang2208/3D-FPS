from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
P=Path('E:/3d/modern-zombie-preview-20260906');P.mkdir(exist_ok=True)
for f in R.glob('denys-*-motions.gltf'):shutil.copy2(f,P/f.name)
shutil.copy2(R.parents[2]/'assets/models/zombie_quaternius.glb',P/'quaternius.glb')
previous=R.parents[2]/'assets/models/ordinary_zombie/zombie_v03.glb'
if previous.exists():shutil.copy2(previous,P/'previous.glb')
for f in ['modern-zombie-v01.glb','ual-mannequin.glb','render_candidates.gd']:
 if (R/f).exists():shutil.copy2(R/f,P/f)
(P/'project.godot').write_text('''config_version=5
[application]
config/name="Modern zombie motion review"
config/features=PackedStringArray("4.7", "Forward Plus")
[display]
window/size/viewport_width=1000
window/size/viewport_height=900
window/vsync/vsync_mode=0
[rendering]
rendering_device/driver.windows="d3d12"
anti_aliasing/quality/msaa_3d=2
''',encoding='utf8')
