"""Read imported cabinet collision metadata only; no scene changes."""
import unreal as u,json
from pathlib import Path
mesh=u.load_asset('/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet')
body=mesh.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom')
result={'shape_counts':{key:len(agg.get_editor_property(key)) for key in ('box_elems','convex_elems','sphere_elems','sphyl_elems')},'convex':[]}
for hull in agg.get_editor_property('convex_elems'):
    result['convex'].append(hull.export_text())
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
