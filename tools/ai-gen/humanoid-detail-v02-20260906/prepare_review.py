from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
P=Path('E:/3d/humanoid-detail-preview-20260906');P.mkdir(exist_ok=True)
old=R.parent/'modern-zombie-v01-20260906'
variants=R.parent/'humanoid-variants-v01-20260906'
(P/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Humanoid motion review"\nconfig/features=PackedStringArray("4.7", "Forward Plus")\n[display]\nwindow/size/viewport_width=1000\nwindow/size/viewport_height=900\nwindow/vsync/vsync_mode=0\n[rendering]\nrendering_device/driver.windows="d3d12"\nanti_aliasing/quality/msaa_3d=2\n',encoding='utf8')
for kind in ['modern','miner','runner']:
 source=old/'modern-zombie-v01.glb' if kind=='modern' else variants/kind/(kind+'-zombie-v01.glb')
 shutil.copy2(source,P/(kind+'-before.glb'))
 if (R/kind/(kind+'-zombie-v02.glb')).exists():shutil.copy2(R/kind/(kind+'-zombie-v02.glb'),P/(kind+'-after.glb'))
render=(variants/'render.gd').read_text()
render=render.replace('humanoid-variants-v01-20260906/rendered','humanoid-detail-v02-20260906/rendered')
render=render.replace('var versions=["miner","runner"]','var versions=["modern-before","miner-before","runner-before"]\n\tfor kind in ["modern","miner","runner"]:\n\t\tif ResourceLoader.exists("res://"+kind+"-after.glb"):versions.append(kind+"-after")')
render=render.replace('version+"-zombie-v01.glb"','version+".glb"')
render=render.replace('if version in ["miner","runner"]:clips=', 'if version.ends_with("-after") and not "--stills" in OS.get_cmdline_user_args():clips=')
anchor='\t\tcamera.position=Vector3(2.5,1.6,4)'
render=render.replace(anchor,'''\t\tcamera.size=.48
\t\tcamera.position=Vector3(.38,1.65,1.2)
\t\tcamera.look_at(Vector3(0,1.43,0))
\t\tawait snap(folder.path_join("head-close.png"))
\t\tcamera.size=.86
\t\tcamera.position=Vector3(.4,1.15,1.8)
\t\tcamera.look_at(Vector3(0,1.05,0))
\t\tawait snap(folder.path_join("torso-close.png"))
\t\tcamera.size=2.5
'''+anchor)
(P/'render.gd').write_text(render,encoding='utf8');(R/'render.gd').write_text(render,encoding='utf8')
print('DETAIL_REVIEW_PREPARED')
