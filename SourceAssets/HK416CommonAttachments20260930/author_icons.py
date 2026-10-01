"""Five physical source images for the standard framed modification icons."""
import bpy,bmesh,ast,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1];H=O.parent/'HK416Reworked20260930';I=O/'Icons';I.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
tree=ast.parse((O.parent/'G18IconsFinal20260930/author_icons.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'scene','reset'}],type_ignores=[]),'icon studio','exec'))
R=Matrix(json.loads((H/'authoring.json').read_text())['root_matrix']);records={}
for key,part in [('magazine_false','factory_magazine'),('magazine_ext_mag','ext_mag'),('magazine_large_drum','large_drum'),('stock_false','factory_stock'),('reargrip_false','factory_grip')]:
 if '--ext-only' in sys.argv and part!='ext_mag':continue
 reset();file=O/'Meshes'/('SM_HK416_'+part+'.blend') if part in ('ext_mag','large_drum') else H/'Exports/Attachments'/('SM_HK416_'+part+'_Editable.blend')
 with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=['SM_HK416_'+part]
 ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.transform(R.inverted());ob.hide_set(False);ob.hide_render=False
 for m in ob.data.materials:
  if m.name.startswith('M_HK416_'):continue
  m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  bs.inputs['Base Color'].default_value=(.035,.035,.035,1);bs.inputs['Metallic'].default_value=.6 if 'Fastener' in m.name or 'Steel' in m.name else .12;bs.inputs['Roughness'].default_value=.45
 s,palette=scene([ob],(1,0,0),True);s.render.filepath=str(I/('ue_hk416_'+key+'.png'))
 bpy.ops.wm.save_as_mainfile(filepath=str(I/(key+'_Source.blend')));bpy.ops.render.render(write_still=True)
 records['ue_hk416_'+key]={'file':s.render.filepath,'source':str(file),'purpose':'Input for framed production icon','grayscale':True}
 (O/'icon_sources.json').write_text(json.dumps(records,indent=2))
 print('HK416_ICON_SOURCE_SAVED',key,flush=True)
