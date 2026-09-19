import bpy,json,sys
from pathlib import Path
O=Path(__file__).parent;S=O.parent;sys.path.insert(0,str(S/'ExtMagPattern20260919'));from export_tangents import export
bpy.ops.wm.open_mainfile(filepath=str(S/'ASH12ExtendedMagazine20260919/ASH12_ExtMag30_Editable.blend'));ob=bpy.data.objects['SM_ASH12_ExtMag30'];m=ob.data;attr=m.color_attributes['SurfaceRegions'];changed=0
for c in attr.data:
 if any(v>.001 for v in c.color[:3]):c.color=(0,0,0,1);changed+=1
m.color_attributes.active_color=attr
ob.name='SM_ASH12_ExtMag30_Finish';bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
export(m,O/(ob.name+'.fbx'));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'ASH12_ExtMag30_Finish_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(dict(changed_corners=changed,mask=[0,0,0,1],geometry_unchanged=True,uv_unchanged=True,normals_unchanged=True,reason='New BM faces default white enabled all receiver region masks, including dark bore'),indent=2))
