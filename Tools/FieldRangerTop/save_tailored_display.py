"""Save pickup and equipment display with the same PBR and edge tint as worn mesh."""
import importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020/TailoredFinish20261021'
DEST='/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020/TailoredFinish20261021'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def module(name,path):
    s=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def dynamic(d):
    ps=[];ns=[];uv=[];cs=[];fs=[];lookup={}
    for fi,tri in enumerate(d['triangles']):
        row=[]
        for ci,vi in enumerate(tri):
            n=d['normals'][fi][ci];tex=d['uv'][fi][ci];color=d['colors'][vi];key=(vi,*[round(x,7) for x in n+tex+color])
            if key not in lookup:
                lookup[key]=len(ps);ps.append(u.Vector(*d['positions'][vi]));ns.append(u.Vector(*n));uv.append(u.Vector2D(*tex));cs.append(u.LinearColor(*color))
            row.append(lookup[key])
        fs.append(u.IntVector(*row))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uv,vertex_colors=cs,triangles=fs),0,True)
    for i,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,slot,True)
    return dm
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End play before saving tailored display assets')
io=module('tailored_static_io','Tools/ChainmailPants/save_assets.py');io.DEST=DEST
mats=[u.load_asset(p) for p in read(R/'materials.json')['materials']];mats.append(mats[2]);editable=read(R/'editable.json')
d=read(R/'Authored/ue_field_sweater/Jason.json');dm=dynamic(d);center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)];T=u.GeometryScript_MeshTransforms
T.translate_mesh(dm,u.Vector(*[-x for x in center]));T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90));pickup=io.static(dm,DEST+'/Pickups/SM_FieldRangerTop',mats)
dm=dynamic(read(Path(editable['display'])));T.inverse_transform_mesh(dm,u.Transform(rotation=u.Rotator(pitch=0,yaw=-90,roll=0)));icon=io.static(dm,DEST+'/Icons/SM_FieldRangerTop_Icon',mats)
task=u.AssetImportTask();task.filename=editable['icon'];task.destination_path=DEST+'/Icons';task.destination_name='T_FieldRangerTop_Icon';task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(DEST+'/Icons/T_FieldRangerTop_Icon')
for key,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():tex.set_editor_property(key,value)
io.save(tex);(R/'display_assets.json').write_text(json.dumps(dict(completed=True,pickup=pickup,icon=icon,texture=tex.get_path_name(),runtime_tested=False),indent=2),encoding='utf-8');print('TAILORED_DISPLAY_SAVED',flush=True)
