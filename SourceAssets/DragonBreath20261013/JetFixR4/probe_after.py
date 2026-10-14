from pathlib import Path
exec(compile(Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/JetFixR4/read_saved.py').read_text(encoding='utf-8'),'dragon-material-probe','exec'))
probe_output='particles-after.json'
exec(compile(Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/JetFixR4/particle_probe.py').read_text(encoding='utf-8'),'dragon-jet-probe','exec'))
# Birth size, rotation and bilateral coverage are the reported regressions.
assert len(report)==9
for row in report:
    for p in row['youngest']:
        assert abs(p['rotation'])<.01, p
        if p['age']==0:
            assert p['size']==[6.,10.], p
    if row['count']>30:
        assert row['left']>10 and row['right']>10,row
        assert abs(row['left']-row['right'])<=3,row
        assert row['min_angle']<-40 and row['max_angle']>40,row
    assert row['max_size']<=234.01,row
print('DRAGON_JET_BIRTH_AND_BILATERAL_CHECKS_PASSED')
mat=u.load_asset('/Game/Skills/DragonBreath20261013/M_DragonFlame')
lib=u.MaterialEditingLibrary
errors=lib.recompile_material(mat)
assert not errors, errors
assert mat.get_editor_property('blend_mode')==u.BlendMode.BLEND_ALPHA_COMPOSITE
pending=[lib.get_material_property_input_node(mat,p) for p in [u.MaterialProperty.MP_EMISSIVE_COLOR,u.MaterialProperty.MP_OPACITY]]
assert all(pending)
nodes={}
while pending:
    n=pending.pop()
    if not n or n.get_path_name() in nodes:continue
    nodes[n.get_path_name()]=n
    pending.extend(lib.get_inputs_for_material_expression(mat,n))
textures=[n.get_editor_property('texture').get_path_name() for n in nodes.values() if isinstance(n,u.MaterialExpressionTextureSample)]
assert textures==['/Game/_SplineVFX/_GenericSource/Texture/T_Vfx_Stamp_FireFlame_88.T_Vfx_Stamp_FireFlame_88'],textures
assert len([n for n in nodes.values() if isinstance(n,u.MaterialExpressionEyeAdaptationInverse)])==1
assert any(isinstance(n,u.MaterialExpressionPixelDepth) for n in nodes.values())
assert any(isinstance(n,u.MaterialExpressionParticleRelativeTime) for n in nodes.values())
revision=u.EditorAssetLibrary.get_metadata_tag(system,'DragonBreath.Revision')
assert revision=='DragonBreathJetFixR4_20261013'
(OUT/'saved-checks.json').write_text(json.dumps({'revision':revision,'birth_size_cm':[6,10],'birth_rotation':0,'bilateral_cases':3,'connected_textures':textures,'particle_probe_passed':True,'gameplay_tested':False,'rendered':False},indent=2),encoding='utf-8')
print('DRAGON_JET_MATERIAL_BINDING_CHECKS_PASSED')
