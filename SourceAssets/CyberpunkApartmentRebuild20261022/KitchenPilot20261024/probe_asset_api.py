"""Read-only existing kitchen assets; never modify or save a map or asset."""
from pathlib import Path
import json,traceback
import unreal as u
R=Path(__file__).resolve().parent
B='/Game/Props/CyberpunkApartmentKitchen20261024'
try:
    out={'stage':'asset_api_read','saved':False,'map_modified':False,'map_load_called':False,'game_run':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'methods':{},'materials':{}}
    names=[('MaterialEditingLibrary','get_material_property_input_node'),('MaterialEditingLibrary','get_material_expressions'),('StaticMeshEditorSubsystem','set_lod_build_settings'),('EditorLoadingAndSavingUtils','save_map'),('Object','modify'),('StaticMeshComponent','get_mobility'),('StaticMeshComponent','set_relative_transform'),('StaticMeshComponent','set_collision_enabled')]
    for cls,name in names:
        fn=getattr(getattr(u,cls),name,None);out['methods'][cls+'.'+name]=str(fn.__doc__) if fn else None
    counter=u.load_asset(B+'/Meshes/SM_KP_Counter')
    body=counter.get_editor_property('body_setup')
    out['body_modify']=str(body.modify.__doc__)
    geom=body.get_editor_property('agg_geom')
    box=u.KBoxElem()
    box.set_editor_property('center',u.Vector(1,2,3))
    for axis,v in zip(('x','y','z'),(4,5,6)):box.set_editor_property(axis,v)
    out['box_assignment']=str(box)
    receipt=json.loads((R/'assets_saved.json').read_text())
    for role,entry in receipt['normal_bindings'].items():
        m=u.load_asset(B+'/Materials/M_'+role)
        out['materials'][role]={}
        for pin in ['BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AMBIENT_OCCLUSION']:
            prop=getattr(u.MaterialProperty,'MP_'+pin)
            node=u.MaterialEditingLibrary.get_material_property_input_node(m,prop)
            out['materials'][role][pin]=node.get_path_name() if node else None
    out['status']='complete'
except Exception:
    out={'stage':'failed','error':traceback.format_exc()}
(R/'probe-asset-api.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out))
