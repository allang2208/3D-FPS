import unreal as u, json, os
from pathlib import Path
run=Path(r'F:/FPSGAMEData/ArtProduction/HillsVillageShops/ShopNetworkAndDistance-20261122'); stage=run/'Materials'; project=stage/'Host'
assert Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()==project.resolve()
paths=json.loads((run/'material-candidates.json').read_bytes())
grass='/Game/WorldGeneration/TemperateHills/WetForest/ScannedGrass/M_SoftWildGrass'
readback=os.getenv('SHOP_MATERIAL_READBACK')=='1'
details={}; changed=[]
for p in paths:
    m=u.load_asset(p)
    assert m,p
    if isinstance(m,u.MaterialInstance):
        parent=m.get_editor_property('parent');assert parent.get_path_name().split('.')[0] in paths,(p,parent)
        details[p]={'parent':parent.get_path_name()};continue
    assert isinstance(m,u.Material),p
    before=m.get_editor_property('used_with_instanced_static_meshes'); edit=False
    row={'instance_flag_before':before}
    if not before:
        assert not readback,p
        m.modify();m.set_editor_property('used_with_instanced_static_meshes',True);edit=True
    if p==grass:
        exprs=[e for e in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCollectionParameter)]
        expected={'HillsWet20261111.BladeWind':'ForestWind','HillsWet20261111.RainforestWeather':'RainforestWeather'}
        assert len(exprs)==len(expected),exprs
        row['bindings']={}
        for e in exprs:
            tag=e.get_editor_property('desc'); intended=expected[str(tag)]; collection=e.get_editor_property('collection')
            assert collection and collection.get_name()=='MPC_ForestWind'
            assert intended in [str(v.get_editor_property('parameter_name')) for v in collection.get_editor_property('vector_parameters')]
            prior=str(e.get_editor_property('parameter_name'))
            if prior!=intended:
                assert not readback,(tag,prior)
                m.modify();e.modify();e.set_editor_property('parameter_name',intended);edit=True
            row['bindings'][str(tag)]=[prior,str(e.get_editor_property('parameter_name'))]
            assert row['bindings'][str(tag)][1]==intended
    if edit:
        u.MaterialEditingLibrary.recompile_material(m)
        assert u.EditorAssetLibrary.save_loaded_asset(m,False),p
        changed.append(p)
    row['instance_flag_after']=m.get_editor_property('used_with_instanced_static_meshes')
    assert row['instance_flag_after'],p
    details[p]=row
(stage/('readback.json' if readback else 'edits.json')).write_text(json.dumps({'changes':changed,'materials':details},indent=2))
