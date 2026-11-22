from pathlib import Path
import json,hashlib,unreal as u
W=Path(__file__).resolve().parent;H=W/'SurfaceHost';R=Path('D:/FPS3D/FPSGAME');S=R/'SourceAssets/M249Orpind20261107'
assert Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()==H
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;MP=u.MaterialProperty
def kpath(name):return '/Game/Weapons/M249/Materials/M_M249_'+name
def sig(m):
 def get(obj,k):
  try:
   v=obj.get_editor_property(k)
   if isinstance(v,u.Object):return v.get_path_name()
   if isinstance(v,u.LinearColor):return [v.r,v.g,v.b,v.a]
   return str(v)
  except Exception:return None
 edges={};props={}
 def tree(node):
  if not node:return None
  cls=node.get_class().get_name()
  data={key:v for key in ('constant','r','g','b','a','texture','sampler_type') if (v:=get(node,key)) is not None}
  return [cls,data,[tree(c) for c in M.get_inputs_for_material_expression(m,node) if c]]
 for name in ('MP_BASE_COLOR','MP_METALLIC','MP_ROUGHNESS','MP_NORMAL','MP_EMISSIVE_COLOR','MP_OPACITY','MP_OPACITY_MASK','MP_AMBIENT_OCCLUSION'):
  prop=getattr(MP,name);node=M.get_material_property_input_node(m,prop)
  if node:edges[name]=[str(M.get_material_property_input_node_output_name(m,prop)),tree(node)]
 for k in ('two_sided','blend_mode','shading_model','used_with_skeletal_mesh'):props[k]=get(m,k)
 return dict(properties=props,outputs=edges)
names=('Surface','OpticHousing','Glass','Reticle','Riser')
pre={n:sig(u.load_asset(kpath(n))) for n in names}
p=S/'import_assets.py';t=p.read_text(encoding='utf-8-sig')
head=t[:t.index('textures={}')]
body=t[t.index('surface=new_mat'):t.index('donor=E.load_asset')]
env={'__file__':str(p)};exec(compile(head,str(p),'exec'),env)
env['textures']={n:u.load_asset('/Game/Weapons/M249/Textures/T_M249_'+n) for n in ('Color','ORM','Normal','Emission','Transmission')}
exec(compile(body,str(p),'exec'),env)
post={n:sig(u.load_asset(kpath(n))) for n in names}
(W/'original-surfaces.json').write_text(json.dumps({n:dict(before=pre[n],after=post[n],same=pre[n]==post[n]) for n in names},indent=2))
rs={}
for n in names:
 src=H/'Content'/(kpath(n)[6:]+'.uasset')
 if pre[n]!=post[n]:rs[kpath(n)]=dict(stage='original materials',sha256=hashlib.sha256(src.read_bytes()).hexdigest())
(W/'original-material-change.json').write_text(json.dumps(rs,indent=2))
rows={}
for k in ('/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_m249_bipod_false','/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_m249_category_bipod','/Game/ColdSteelData/Icons/ue_m249_no_bipod'):
 a=u.load_asset(k);v={'srgb':a.srgb,'ui':a.lod_group==u.TextureGroup.TEXTUREGROUP_UI,'icon_compression':a.compression_settings==u.TextureCompressionSettings.TC_EDITOR_ICON,'no_mips':a.mip_gen_settings==u.TextureMipGenSettings.TMGS_NO_MIPMAPS,'never_stream':a.never_stream}
 if '/Icons/' in k:v['native_size']=a.max_texture_size==0
 rows[k]=v
(W/'existing-icon-settings.json').write_text(json.dumps(rows,indent=2))
print('M249_BASE_MATERIALS',list(rs),'M249_ICONS',rows,flush=True)
