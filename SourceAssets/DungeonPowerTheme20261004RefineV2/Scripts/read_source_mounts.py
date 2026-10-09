import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(R/'Authored/Reused_Original_Assets.blend'))
for name in ['SM_Facility_PowerCabinet','SM_Archive_DispatchConsole_V2','SM_Staff_Desk','SM_Staff_Chair','SM_TileFracture_EntryEnd']:
 o=bpy.data.objects[name];ps=o.data.polygons;print('SOURCE_MOUNTS',name,'y<0',sum(p.center.y<0 for p in ps),'y>0',sum(p.center.y>0 for p in ps),'negative_extreme',sum(p.center.y<-.28 for p in ps),'positive_extreme',sum(p.center.y>.28 for p in ps),'slots',{m.name:sum(p.material_index==i for p in ps) for i,m in enumerate(o.data.materials)},flush=True)
