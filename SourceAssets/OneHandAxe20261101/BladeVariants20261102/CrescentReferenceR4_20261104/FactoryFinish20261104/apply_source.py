"""Apply the transferred PBR to the frozen R4 source, preserving geometry and UVs."""
from pathlib import Path
import bpy,json,shutil,sys
P=Path(__file__).resolve().parent;R4=P.parent
sys.path.insert(0,str(P.parents[3]/'KukriComponentVariants20261026'))
from asset_tools import export
bpy.ops.wm.open_mainfile(filepath=str(P/'Before/SwiftCrescent_Editable.blend'))
entry=json.loads((R4/'SwiftCrescent.json').read_text('utf-8'))
obj=bpy.data.objects[entry['object']];material=obj.data.materials[0]
for key in ['BaseColor','ORM','Normal']:
    name='T_TacticalHatchet_Head_SwiftCrescent_R4_'+key+'.png'
    src=P/'Textures'/name;dst=R4/'Textures'/name;shutil.copy2(src,dst)
    image=bpy.data.images.load(str(dst),check_existing=False)
    image.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color';image.pack()
    old=next(node for node in material.node_tree.nodes if node.type=='TEX_IMAGE' and node.image and key in node.image.name)
    old.image=image
material['material_source']='Original M_TacticalHatchet body and cutting edge PBR'
obj['material_revision']='factory_finish_20261104'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R4/'SwiftCrescent_Editable.blend'))
export(obj,Path(entry['fbx']))
entry['material_revision']='factory_finish_20261104';entry['material_source']=str(P/'texture_recipe.json')
(R4/'SwiftCrescent.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'source_receipt.json').write_text(json.dumps({'saved':True,'blend':str(R4/'SwiftCrescent_Editable.blend'),
    'fbx':entry['fbx'],'geometry_modified':False,'uv_modified':False,'material_revision':entry['material_revision'],
    'runtime_tested':False},indent=2)+'\n',encoding='utf-8')
print('FACTORY_FINISH_SOURCE_SAVED',flush=True)
