"""Reuse the established scoped import and readback, with R8-specific outputs."""
from pathlib import Path
import shutil
O=Path(__file__).parent;P=O.parents[1];review=P/'Saved/Super90R7Review20261008'
code=(O.parent/'Super90MotionR7_20261008/import_motion.py').read_text()
code=code.replace('R7','R8').replace('ContactFlowR8-20261008','ContactR8-20261008')
# Geometry did not change in R8; only animation sequences and grip deltas save.
start=code.index('    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False')
end=code.index('    for clip in manifest[\'clips\']:')
code=code[:start]+code[end:]
code=code.replace('support arm clearance, outside regrip path and pressure-shaped motion','continuous elbow transport, fitted support palm and outside thumb-release approach')
(O/'import_motion.py').write_text(code,encoding='utf-8')
shutil.copy2(O.parent/'Super90MotionR7_20261008/import_background.ps1',O/'import_background.ps1')
code=(review/'read_saved.py').read_text().replace("O=Path(__file__).parent;P=O.parents[1];O.mkdir(parents=True,exist_ok=True)","O=Path(__file__).parent/'Diagnostics';P=O.parents[2];O.mkdir(parents=True,exist_ok=True)")
code=code.replace('Super90MotionR7_20261008','Super90ContactR8_20261008').replace('R7','R8')
(O/'read_saved.py').write_text(code,encoding='utf-8')
shutil.copy2(review/'read_background.ps1',O/'read_background.ps1')
code=(review/'check_motion.py').read_text().replace("O=Path(__file__).parent;P=O.parents[1]","O=Path(__file__).parent/'Diagnostics';P=O.parents[2]")
(O/'check_motion.py').write_text(code,encoding='utf-8')
code=code.split("data=json.loads((O/'saved_assets.json').read_text())")[0]
code+="\n(O/'source_motion.json').write_text(json.dumps(out,indent=2))\nprint('SOURCE_MOTION_CHECKED',len(out['clips']),flush=True)\n"
(O/'check_source.py').write_text(code,encoding='utf-8')
code=(review/'render_saved.py').read_text().replace("O=Path(__file__).parent;P=O.parents[1]","O=Path(__file__).parent/'Diagnostics';P=O.parents[2]")
(O/'render_saved.py').write_text(code,encoding='utf-8')
print('R8_TOOLS_PREPARED')
