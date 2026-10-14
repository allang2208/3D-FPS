import sys,json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/DragonBreath20261013/JetFixR4'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import build_dragon_breath as a
mat=u.load_asset(a.DEST+'/M_DragonFlame');system=u.load_asset(a.DEST+'/NS_DragonBreath')
lib=u.MaterialEditingLibrary
assert not lib.recompile_material(mat)
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
module=u.EditorAssetLibrary.get_metadata_tag(system,'Fireball.Assignments.Flame-Smoke.ParticleSpawnScript')
birth={k:u.RainAssetEditor.read_input(system,'Flame-Smoke','ParticleSpawnScript',module,k) for k in ['Particles.SpriteSize','Particles.SpriteRotation','Particles.SpriteUVScale']}
assert 'float2(6,10)' in birth['Particles.SpriteSize'],birth
assert 'HlslExpression="0"' in birth['Particles.SpriteRotation'],birth
result={'revision':revision,'connected_textures':textures,'saved_birth_expressions':birth,'material_compile_errors':[],'gameplay_tested':False,'rendered':False}
(OUT/'saved-asset-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('DRAGON_JET_SAVED_ASSET_CHECKS_PASSED '+json.dumps(result))
