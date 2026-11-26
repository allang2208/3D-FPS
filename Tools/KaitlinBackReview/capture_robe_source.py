import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/KaitlinBackReview20261117'
(R/'Inputs').mkdir(exist_ok=True)
helper=(P/'Tools/ChapelNun/capture_sources.py').read_text(encoding='utf-8-sig')
block=helper[helper.index('G=u.GeometryScript'):helper.index('head=capture(')]
exec(compile(block,'<native robe read>','exec'))
source='/Game/Characters/ModularOutfit20260924/KaitlinPlayer20261023/World/SK_Kaitlin_BlueMageRobe_aa551454'
mesh=capture('female_robe',source)
donor=u.load_asset('/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe')
def cloth_data(asset):
    result=[]
    for c in asset.mesh_clothing_assets:
        result.append(dict(kind=c.get_class().get_name()))
    return result
source_cloth=cloth_data(mesh);donor_cloth=cloth_data(donor)
report=dict(source=mesh.get_path_name(),donor=donor.get_path_name(),cloth_asset_classes_match=source_cloth==donor_cloth,
            physics_asset_matches=mesh.physics_asset==donor.physics_asset,
            source_cloth_count=len(source_cloth),donor_cloth_count=len(donor_cloth),source_materials=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name()) for m in mesh.materials])
(R/'Inputs/donor_contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('KAITLIN_ROBE_DONOR_CONTRACT',report['cloth_asset_classes_match'],report['physics_asset_matches'],flush=True)
