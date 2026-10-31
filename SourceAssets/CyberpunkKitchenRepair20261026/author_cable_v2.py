"""Only re-export the cable hardware and edge contact bend; retain all other FBX."""
from pathlib import Path
import bpy,json,sys,runpy
R=Path(__file__).resolve().parent;K=R.parent/'CyberpunkApartmentRebuild20261022/KitchenPilot20261024'
sys.path.insert(0,str(K));import model as g
bpy.ops.wm.open_mainfile(filepath=str(R/'KitchenRepair.blend'))
g.G.clear();g.M={'Rubber':bpy.data.materials['KP_Rubber']}
route=runpy.run_path(str(R/'cable_route.py'))
old=bpy.data.objects.get('KIT_CoffeeEdgeBend')
if old:bpy.data.objects.remove(old,do_unlink=True)
route['add_edge_geometry'](g);rows=g.finish(g.M,R)
hardware=bpy.data.objects['KIT_PowerHardware'];oldz=hardware.get('CoffeePortHeight',1.022);dz=.977-oldz
for v in hardware.data.vertices:
    if abs(v.co.x-14.89)<.05 and 19.90<v.co.y<20.0:v.co.z+=dz
hardware['CoffeePortHeight']=.977;hardware.data.update()
bpy.ops.object.select_all(action='DESELECT');hardware.select_set(True);bpy.context.view_layer.objects.active=hardware
fbx=R/'FBX/SM_KP_PowerHardware.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE',add_leaf_bones=False)
G=json.loads((R/'geometry.json').read_text(encoding='utf8'));G['meshes']=[r for r in G['meshes'] if r['key']!='CoffeeEdgeBend']+rows
route['annotate'](G)
(R/'geometry.json').write_text(json.dumps(G,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'KitchenRepair.blend'))
print('CABLE_V2_SOURCE_SAVED',len(rows),dz)
