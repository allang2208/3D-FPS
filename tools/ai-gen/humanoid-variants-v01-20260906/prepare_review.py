from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
SOURCE=R.parent/'modern-zombie-v01-20260906'
P=Path('E:/3d/humanoid-variants-preview-20260906');P.mkdir(exist_ok=True)
(P/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Humanoid motion review"\nconfig/features=PackedStringArray("4.7", "Forward Plus")\n[display]\nwindow/size/viewport_width=1000\nwindow/size/viewport_height=900\nwindow/vsync/vsync_mode=0\n[rendering]\nrendering_device/driver.windows="d3d12"\nanti_aliasing/quality/msaa_3d=2\n',encoding='utf8')
for version in ['miner','runner']:
    model=R/version/(version+'-zombie-v01.glb')
    assert model.exists()
    shutil.copy2(model,P/model.name)
    check=(SOURCE/'check_model.py').read_text().replace("R/'modern-zombie-v01.glb'",f"R/'{model.name}'")
    (R/version/'check_model.py').write_text(check,encoding='utf8')
renderer=(SOURCE/'render_candidates.gd').read_text()
start=renderer.index('\tvar versions=')
end=renderer.index('\t\tvar folder=',start)
renderer=renderer[:start]+'''\tvar versions=["miner","runner"]
\tfor version in versions:
\t\tvar file="res://"+version+"-zombie-v01.glb"
'''+renderer[end:]
renderer=renderer.replace('modern-zombie-v01-20260906/rendered','humanoid-variants-v01-20260906/rendered')
renderer=renderer.replace('model.scale=Vector3.ONE*(1.0 if version in ["previous","modern","ual"] else (1.25 if version=="quaternius" else .01))','model.scale=Vector3.ONE')
renderer=renderer.replace('var idle="Idle" if version in ["quaternius","previous","modern"] else "idle_220f"','var idle="Idle"')
renderer=renderer.replace('if version=="modern":clips=', 'if version in ["miner","runner"]:clips=')
(P/'render.gd').write_text(renderer,encoding='utf8')
(R/'render.gd').write_text(renderer,encoding='utf8')
print('VARIANT_REVIEW_PREPARED')
