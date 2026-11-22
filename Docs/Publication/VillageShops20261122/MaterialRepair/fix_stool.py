import unreal as u
from pathlib import Path
import json
run=Path(r'F:/FPSGAMEData/ArtProduction/HillsVillageShops/ShopNetworkAndDistance-20261122')
assert Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()==(run/'Collision/Host').resolve()
p='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakStool'
m=u.load_asset(p); body=m.get_editor_property('body_setup'); geom=body.get_editor_property('agg_geom')
boxes=list(geom.get_editor_property('box_elems'))
def coords(b):
    c=b.get_editor_property('center')
    return [round(float(v),3) for v in (c.x,c.y,c.z,b.get_editor_property('x'),b.get_editor_property('y'),b.get_editor_property('z'))]
old=[coords(b) for b in boxes]
top=[i for i,v in enumerate(old) if v in ([0,-10,44,46,19.6,4],[0,10,44,46,19.6,4])]
assert len(top)==2,old
merged=u.KBoxElem()
merged.set_editor_property('center',u.Vector(0,0,44))
for axis,n in zip(('x','y','z'),(46.,39.6,4.)):merged.set_editor_property(axis,n)
m.modify();body.modify()
final=[b for i,b in enumerate(boxes) if i not in top]+[merged]
geom.set_editor_property('box_elems',final);body.set_editor_property('agg_geom',geom)
assert u.EditorAssetLibrary.save_loaded_asset(m,False)
(run/'Collision/collision.json').write_text(json.dumps({'package':p,'before':old,'after':[coords(b) for b in final]},indent=2))
