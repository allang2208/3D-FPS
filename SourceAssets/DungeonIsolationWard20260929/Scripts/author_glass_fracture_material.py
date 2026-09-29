"""Author the bounded whole-pane shard material. Original WPO flight, no external plugin."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'Config/room.json').read_text(encoding='utf-8'))
path=CFG['glass_breakage']['fracture_material'];folder,name=path.rsplit('/',1)
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
 raise RuntimeError('Preserve unsaved fracture material '+path)
m=u.load_asset(path) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
m.modify();L.delete_all_material_expressions(m)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
m.set_editor_property('two_sided',False);m.set_editor_property('tangent_space_normal',False)
m.set_editor_property('screen_space_reflections',True)

def node(kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(src,dst,pin):
 n,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(n,out,dst,pin):raise RuntimeError('Cannot connect '+pin)
def custom(code,inputs,width=1):
 n=node('Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
 pins=[]
 for key in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
 n.set_editor_property('inputs',pins)
 for key,value in inputs.items():wire(value,n,key)
 return n
def scalar(key,value):return node('ScalarParameter',parameter_name=key,default_value=value)
def vector(key,value):return node('VectorParameter',parameter_name=key,default_value=u.LinearColor(*value,1))

clock=node('Time');born=scalar('Born',0)
common={'Position':node('WorldPosition',world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),
 'Normal':node('VertexNormalWS'),'CenterUV':node('TextureCoordinate',coordinate_index=1),
 'Shard':node('TextureCoordinate',coordinate_index=2),'Clock':clock,'Born':born,'FloorZ':scalar('FloorZ',0),
 'PaneSize':vector('PaneSize',(142,250,1.2)),'PaneOrigin':vector('PaneOrigin',(0,0,0)),
 'PaneY':vector('PaneY',(0,1,0)),'PaneZ':vector('PaneZ',(0,0,1)),
 'HitPoint':vector('HitPoint',(0,0,0)),'ShotDirection':vector('ShotDirection',(1,0,0))}
code=(ROOT/'Scripts/GlassFragmentsV5.hlsl').read_text(encoding='utf-8')
wpo=custom(code,dict(common,Mode=node('Constant',r=0)),3)
normal=custom(code,dict(common,Mode=node('Constant',r=1)),3)
edge=(node('VertexColor'),'R')
opacity=custom('float f=pow(1-saturate(abs(dot(normalize(N),normalize(V)))),3); return (.12+f*.42+Edge*.36)*(1-smoothstep(2.8,4,Clock-Born));',
 {'N':normal,'V':node('CameraVectorWS'),'Edge':edge,'Clock':clock,'Born':born})
rough=custom('return lerp(.085+Seed.x*.08,.32,Edge);',{'Seed':common['Shard'],'Edge':edge})
slab=node('SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
for value,pin,prop in ((vector('GlassTint',(.64,.76,.73)),'BaseColor','BASE_COLOR'),
 (rough,'Roughness','ROUGHNESS'),(node('Constant',r=.5),'Specular','SPECULAR'),
 (opacity,'Opacity','OPACITY'),(normal,'Normal','NORMAL')):
 wire(value,slab,pin);L.connect_material_property(value,'',getattr(u.MaterialProperty,'MP_'+prop))
if not L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Cannot connect glass surface')
if not L.connect_material_property(wpo,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET):raise RuntimeError('Cannot connect shard motion')
errors=L.recompile_material(m)
if errors:raise RuntimeError('Glass fragment material authoring failed '+str(errors))
L.layout_material_expressions(m)
if not E.save_loaded_asset(m,False):raise RuntimeError('Cannot save glass fragment material')
(ROOT/'Receipts/glass-material-v5.json').write_text(json.dumps(dict(stage='fracture_material_saved',material=path,
 tests_run=False,rendered=False),indent=2),encoding='utf-8')
print('WARD_FRACTURE_MATERIAL_SAVED',flush=True)
