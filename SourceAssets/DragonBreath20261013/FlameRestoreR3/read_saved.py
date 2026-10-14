"""Read back only the flame material/renderer involved in the reported defect."""
import json,re,sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import build_dragon_breath as a
mat=u.load_asset(a.DEST+'/M_DragonFlame')
system=u.load_asset(a.DEST+'/NS_DragonBreath')
assert mat and system
emission=a.LIB.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
assert isinstance(emission,u.MaterialExpressionEyeAdaptationInverse)
assert mat.get_editor_property('shading_model')==u.MaterialShadingModel.MSM_UNLIT
nodes=a.LIB.get_material_expressions(mat)
textures={str(n.get_editor_property('parameter_name')):n.get_editor_property('texture').get_path_name() for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter)}
assert textures['FlameTexture']==a.SOURCE+'/Essentials/Textures/T_TiledFire.T_TiledFire'
assert textures['SilhouetteAtlas']==a.SOURCE+'/Essentials/Textures/T_SmokeSubUV.T_SmokeSubUV'
assert len([n for n in nodes if isinstance(n,u.MaterialExpressionEyeAdaptationInverse)])==1
revision=u.EditorAssetLibrary.get_metadata_tag(system,'DragonBreath.Revision')
assert revision=='DragonBreathFlameRestoreR3_20261013'
renderers={}
for name in a.emitters(system):
    data=a.API.call_method('GetRendererData',(a.ref(system,name,renderer=0),)).export_text()
    raw=re.search(r'PropertyValues=("(?:[^"\\]|\\.)*")',data)[1]
    props=json.loads(json.loads(raw))
    renderers[name]={k:props[k] for k in ['Material','Alignment','SubImageSize']}
assert 'MI_DragonFlame' in str(renderers['Flame-Smoke']['Material'])
assert renderers['Flame-Smoke']['Alignment']=='VelocityAligned'
report={'revision':revision,'emissive_output':emission.get_class().get_name(),'shading':'unlit','textures':textures,'renderers':renderers,'gameplay_tested':False,'rendered':False}
(ROOT/'SourceAssets/DragonBreath20261013/FlameRestoreR3/saved-material-binding.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DRAGON_FLAME_SAVED_BINDING '+json.dumps(report))
