"""Read the canonical device material inputs needed for the M24 fitted assets."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).resolve().parent
L=u.MaterialEditingLibrary
R={'meshes':{},'materials':{},'masters':{}}
X=O/'Inputs';X.mkdir(exist_ok=True)
paths={
 'laser':'/Game/Weapons/ASH12/TacticalDevices20260920/laser/SM_ASH12_laser',
 'flashlight':'/Game/Weapons/ASH12/TacticalDevices20260920/flashlight/SM_ASH12_flashlight',
 'blessed_laser':'/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Models/SM_BlessedLaser_ASH12',
 'chassis':'/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action'}
for key,path in paths.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing source '+path)
    row={'path':path,'slots':[],'sockets':{}}
    if key!='chassis':
        fbx=X/(key+'.fbx')
        task=u.AssetExportTask();task.object=mesh;task.filename=str(fbx);task.automated=True;task.prompt=False;task.replace_identical=True
        task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Source export failed '+path)
        row['fbx']=str(fbx)
    for name in ['Emitter','AimGuide']:
        socket=mesh.find_socket(name)
        if socket:
            v=socket.get_editor_property('relative_location')
            row['sockets'][name]=[v.x,v.y,v.z]
    for s in mesh.static_materials:
        m=s.material_interface
        if not m:raise RuntimeError('Missing source material '+path)
        row['slots'].append({'slot':str(s.material_slot_name),'material':m.get_path_name()})
        p=m.get_path_name()
        if p in R['materials']:continue
        base=m.get_base_material();bp=base.get_path_name()
        data={'master':bp,'parameters':{},'class':m.get_class().get_name()}
        if isinstance(m,u.MaterialInstance):
            data['parent']=m.get_editor_property('parent').get_path_name()
            for kind in ['scalar','vector','texture']:
                values={}
                for name in getattr(L,'get_'+kind+'_parameter_names')(base):
                    v=getattr(L,'get_material_instance_'+kind+'_parameter_value')(m,name)
                    values[str(name)]=v.get_path_name() if isinstance(v,u.Object) else [v.r,v.g,v.b,v.a] if isinstance(v,u.LinearColor) else v
                data['parameters'][kind]=values
        R['materials'][p]=data
        if bp not in R['masters']:
            nodes=[]
            for n in L.get_material_expressions(base):
                r={'class':n.get_class().get_name(),'name':n.get_name()}
                if isinstance(n,u.MaterialExpressionCustom):r.update(description=n.get_editor_property('description'),code=n.get_editor_property('code'))
                elif isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter,u.MaterialExpressionTextureSampleParameter2D)):
                    r['parameter']=str(n.get_editor_property('parameter_name'))
                    if isinstance(n,u.MaterialExpressionScalarParameter):r['default']=n.get_editor_property('default_value')
                    elif isinstance(n,u.MaterialExpressionVectorParameter):
                        v=n.get_editor_property('default_value');r['default']=[v.r,v.g,v.b,v.a]
                nodes.append(r)
            R['masters'][bp]={'nodes':nodes}
    R['meshes'][key]=row
(O/'current_sources.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M24_TACTICAL_SOURCE_INPUTS_READ',len(R['meshes']),len(R['materials']),flush=True)
