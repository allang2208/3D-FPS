"""Keep bright paint and warning ink separate from the private metal coating."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KClosure20261018');L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
R=json.loads((O/'Reports/accessories-repair.json').read_text())
code='''float lo=min(Base.r,min(Base.g,Base.b)),hi=max(Base.r,max(Base.g,Base.b));
float paint=max(smoothstep(.38,.65,lo),smoothstep(.25,.55,hi-lo));
float weight=saturate(Metal.r)*(1-paint);
float3 finish=Coat.rgb*(.9+.1*saturate(dot(Base.rgb,float3(.21,.72,.07))*3));
return lerp(Base.rgb,finish,weight);'''
for path,row in R['mixed_materials'].items():
 m=u.load_asset(path)
 for n in L.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')=='Clean Saiga metal only':n.set_editor_property('code',code)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 if not E.save_loaded_asset(m,False):raise RuntimeError('Coating save failed '+path)
 row['bright_neutral_and_colored_paint_protected']=True
(O/'Reports/accessories-repair.json').write_text(json.dumps(R,indent=2))
print('PRIVATE_COATING_PAINT_PRESERVED')
