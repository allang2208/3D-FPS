"""Read native Groom rendering scale for the requested male/female fit audit."""
import unreal as u,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1')
cap=json.loads((R/'capture.json').read_text(encoding='utf-8'));result={}
for rig,style in [('Jason','curly_fade'),('Kaitlin','long_straight')]:
    path=cap['profiles'][rig]['hair_styles'][style][0]['recipe']['asset']
    asset=u.load_asset(path)
    result[rig]={'asset':path,'rendering':[x.export_text() for x in asset.get_editor_property('hair_groups_rendering')]}
(R/'rendering.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('HELMET_HAIR_RENDERING_CAPTURED',flush=True)
