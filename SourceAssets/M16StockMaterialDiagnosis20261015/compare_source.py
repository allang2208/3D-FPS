"""Separate decimation/vertex shading from the original high-mesh shading."""
from pathlib import Path
entry=Path(__file__).parent/'render_ab.py'
exec(compile(entry.read_text(encoding='utf-8').split('variants=')[0],str(entry),'exec'))
def render(name):
 scene.render.filepath=str(V/(name+'.png'));bpy.ops.render.render(write_still=True);print('SOURCE_COMPARE',name,flush=True)
mat=material('Constant',None)
old=objects[0]
for i in range(len(old.data.materials)):old.data.materials[i]=mat
bpy.context.view_layer.objects.active=old;old.select_set(True)
if old.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
for f in old.data.polygons:f.use_smooth=True
render('E_old_mesh_recalculated_normals')
old.hide_render=True
lib=P/'SourceAssets/StockRefresh20260914/TacticalTelescopic/TacticalStock_Game_Body.blend'
with bpy.data.libraries.load(str(lib),link=False) as (src,dst):
 dst.objects=['TacticalStock_Game_Body','TacticalStock_Selected_High']
for ob in dst.objects:scene.collection.objects.link(ob);ob.hide_render=True;ob.location.x+=.012
low,high=dst.objects
objects=[low]
low.data.materials.clear();low.data.materials.append(mat)
for f in low.data.polygons:f.material_index=0
low.hide_render=False;render('F_original_low_constant')
low.data.materials[0]=material('OriginalMatchedBake',P/'SourceAssets/StockRefresh20260914/TacticalTelescopic/Textures/Normal_Game.png')
render('G_original_low_matched_normal')
low.hide_render=True;high.hide_render=False
high.data.materials.clear();high.data.materials.append(mat)
render('H_original_high_constant')
