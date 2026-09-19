"""Read-only palette and live drawer snapshot for the requested UI audit."""
import json
from pathlib import Path
import unreal as u

out=Path(u.Paths.project_dir())/'Saved'/'BuildingPanelAudit20260919'
out.mkdir(parents=True,exist_ok=True)
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
def path(value):return value.get_path_name() if value else None
def vec(value):return [value.x,value.y,value.z]
materials=[];components=[]
for m in palette.get_editor_property('materials'):
    materials.append({'id':str(m.id),'name':str(m.display_name),'mesh':path(m.example_mesh),'surface':path(m.surface)})
ids={m['id'] for m in materials}
for c in palette.get_editor_property('components'):
    mesh=c.mesh
    components.append({'id':str(c.id),'name':str(c.display_name),'group':str(c.material),
                       'group_valid':str(c.material)=='None' or str(c.material) in ids,
                       'mesh':path(mesh),'surface':path(c.surface),'actor':path(c.actor_class),
                       'footprint':vec(c.footprint),'mount':str(c.mount),
                       'mesh_materials':[path(mesh.get_material(i)) for i in range(len(mesh.static_materials))] if mesh else []})
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
widgets=[]
if world:
    for widget in u.WidgetBlueprintLibrary.get_all_widgets_of_class(world,u.VoxelBuildWidget,False):
        widgets.append({'path':widget.get_path_name(),'visible':widget.is_visible(),
                        'status':str(widget.get_editor_property('status').get_text()),
                        'selection':str(widget.get_editor_property('selection').get_text())})
report={'materials':materials,'components':components,'live_widgets':widgets}
(out/'catalog-before.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('BUILDING_PANEL_AUDIT_CATALOG '+json.dumps(report,ensure_ascii=False))
