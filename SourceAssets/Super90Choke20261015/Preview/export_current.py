"""Read-only export of the installed gun and choke for the requested preview."""
import unreal as u
import json
from pathlib import Path
O=Path(__file__).parent
L=u.MaterialEditingLibrary
R={'assets':{},'materials':{},'textures':{},'engine_assets_modified':False}
for key,path in {
    'super90':'/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',
    'choke':'/Game/Weapons/CommonShotgun/Choke20261015/Meshes/SM_ShotgunChoke_Box01',
}.items():
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    task=u.AssetExportTask();task.object=obj;task.filename=str(O/(key+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.options=u.FbxExportOption();task.options.level_of_detail=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError(str(task.errors))
    slots=obj.materials if key=='super90' else obj.static_materials
    R['assets'][key]={'path':path,'fbx':task.filename,'slots':[]}
    for slot in slots:
        mat=slot.material_interface
        if not mat:continue
        mp=mat.get_path_name()
        R['assets'][key]['slots'].append({'slot':str(slot.material_slot_name),'material':mp,'name':mat.get_name()})
        if mp in R['materials']:continue
        row={'name':mat.get_name(),'scalars':{},'vectors':{},'textures':{}}
        R['materials'][mp]=row
        if not isinstance(mat,u.MaterialInstanceConstant):continue
        row['scalars']={str(n):L.get_material_instance_scalar_parameter_value(mat,n) for n in L.get_scalar_parameter_names(mat)}
        row['vectors']={str(n):[getattr(L.get_material_instance_vector_parameter_value(mat,n),c) for c in ('r','g','b','a')] for n in L.get_vector_parameter_names(mat)}
        for name in ('SurfaceNormal','SourceBaseColor','SourceColor','SourceRoughness','SurfaceMask'):
            tex=L.get_material_instance_texture_parameter_value(mat,name)
            if not tex:continue
            tp=tex.get_path_name();row['textures'][name]=tp
            if tp in R['textures']:continue
            target=O/'Textures'/(tex.get_name()+'.png');target.parent.mkdir(exist_ok=True)
            et=u.AssetExportTask();et.object=tex;et.filename=str(target)
            et.automated=True;et.prompt=False;et.replace_identical=True;et.exporter=u.TextureExporterPNG()
            if not u.Exporter.run_asset_export_task(et):raise RuntimeError('Texture export failed '+tp)
            R['textures'][tp]={'file':str(target),'flip_green':bool(tex.get_editor_property('flip_green_channel'))}
(O/'capture.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('SUPER90_CHOKE_PREVIEW_INPUTS_EXPORTED',flush=True)
