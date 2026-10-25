import sys,importlib.util
import unreal as u
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/WorkwearSet')
from workwear_common import *
import workwear_materials as materials
def module(name,path):
    s=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
io=module('workwear_static','Tools/ChainmailPants/save_assets.py');io.DEST=DEST
dynamic=module('workwear_dynamic','Tools/BlueMageRobe/save_assets.py')
mats=materials.create();mats.append(mats[2]);editable=read(R/'editable.json');d=read(editable['display'])
# The shared geometry reader accepts a weights field even for static displays;
# no skeletal reference or bone-weight layer is created for this pickup.
d['weights']=[{} for _ in d['positions']];dm=dynamic.dynamic(d)
center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)];u.GeometryScript_MeshTransforms.translate_mesh(dm,u.Vector(*[-x for x in center]));pickup=io.static(dm,DEST+'/Pickups/SM_WorkJacket',mats)
task=u.AssetImportTask();task.filename=editable['icon'];task.destination_path=DEST+'/Icons';task.destination_name='T_WorkJacket_Icon';task.automated=True;task.replace_existing=True;task.save=False;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(DEST+'/Icons/T_WorkJacket_Icon')
for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():tex.set_editor_property(k,v)
materials.save(tex);write(R/'display_assets.json',dict(completed=True,pickup=pickup,texture=tex.get_path_name(),runtime_tested=False));print('WORK_JACKET_DISPLAY_SAVED',flush=True)
