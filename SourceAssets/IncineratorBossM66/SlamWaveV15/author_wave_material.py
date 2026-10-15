"""Author and save the surface-only expanding ash pressure ring; no rendering."""
import json,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/SlamWaveV15');(ROOT/'Records').mkdir(parents=True,exist_ok=True)
DEST='/Game/Monsters/IncineratorBossM66/SlamWaveV15';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before authoring and saving the M66 wave material')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 wave material has unsaved changes')
mat=u.load_asset(DEST+'/M_M66GroundWave') if E.does_asset_exist(DEST+'/M_M66GroundWave') else None
if not mat:mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_M66GroundWave',DEST,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE)
mat.set_editor_property('two_sided',True);mat.set_editor_property('use_material_attributes',False)
def node(cls):return L.create_material_expression(mat,cls)
def wire(a,b,pin):
    if not L.connect_material_expressions(a,'',b,pin):raise RuntimeError('M66 wave wire failed: '+pin)
uv=node(u.MaterialExpressionTextureCoordinate)
opacity=node(u.MaterialExpressionScalarParameter);opacity.set_editor_property('parameter_name','Opacity');opacity.set_editor_property('default_value',1.)
radius=node(u.MaterialExpressionScalarParameter);radius.set_editor_property('parameter_name','Radius');radius.set_editor_property('default_value',400.)
ring=node(u.MaterialExpressionCustom);ring.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
inputs=[]
for name in ('UV','Fade','Radius'):
    i=u.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
ring.set_editor_property('inputs',inputs)
ring.set_editor_property('code','''
float2 p=UV*2-1; float r=length(p); float a=atan2(p.y,p.x);
float width=clamp(45.0/max(Radius,20.0),0.035,0.80);
float inner=1.0-width;
float band=smoothstep(inner,inner+width*0.32,r)*(1.0-smoothstep(0.985,1.0,r));
float grit=0.76+0.24*sin(a*31+r*73)*sin(a*53-r*49);
float crest=exp(-pow((r-0.963)/max(0.009,width*0.12),2.0));
return saturate((band*grit*0.72+crest*0.22)*Fade);
''')
wire(uv,ring,'UV');wire(opacity,ring,'Fade');wire(radius,ring,'Radius')
color=node(u.MaterialExpressionConstant3Vector);color.set_editor_property('constant',u.LinearColor(.33,.29,.23,1.))
lit=node(u.MaterialExpressionMultiply);wire(color,lit,'A');wire(ring,lit,'B')
trans=node(u.MaterialExpressionOneMinus);wire(ring,trans,'')
surface=node(u.MaterialExpressionSubstrateUnlitBSDF);wire(lit,surface,'EmissiveColor');wire(trans,surface,'TransmittanceColor')
if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('M66 wave output failed')
L.layout_material_expressions(mat);errors=list(L.recompile_material(mat))
if errors:raise RuntimeError(str(errors))
E.set_metadata_tag(mat,'M66.Wave','V15: 45 cm ash pressure band; outer UV radius exactly matches gameplay radius; normal depth testing')
if not E.save_loaded_asset(mat,False):raise RuntimeError('M66 wave material save failed')
report={'complete':True,'saved':[mat.get_path_name()],'band_width_cm':45,'radius_parameter':'Radius','fade_parameter':'Opacity','rendered':False}
(ROOT/'Records/material_install.json').write_text(json.dumps(report,indent=2))
print('M66_WAVE_MATERIAL_SAVED '+json.dumps(report))
