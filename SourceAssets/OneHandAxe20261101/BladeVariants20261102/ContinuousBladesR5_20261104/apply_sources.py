"""Bind factory PBR to the newly authored R5 geometry and export the final sources."""
import bpy,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'KukriComponentVariants20261026'))
from asset_tools import export
parts=json.loads((P/'parts.json').read_text('utf-8'))
for entry in parts:
    kind=entry['kind'];bpy.ops.wm.open_mainfile(filepath=entry['source_blend'])
    obj=bpy.data.objects[entry['object']];material=obj.data.materials[0]
    for role,path in entry['textures'].items():
        image=bpy.data.images.load(path,check_existing=False)
        image.colorspace_settings.name='sRGB' if role=='BaseColor' else 'Non-Color';image.pack()
        texture=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and role in n.image.name)
        texture.image=image
    material['material_source']='Original M_TacticalHatchet body and cutting edge PBR'
    obj['material_revision']='factory_finish_20261104'
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(P/(kind+'_Editable.blend')))
    export(obj,Path(entry['fbx']))
    print('FACTORY_FINISH_SOURCE_SAVED '+kind,flush=True)
(P/'source_receipt.json').write_text(json.dumps({'saved':True,'ids':[entry['id'] for entry in parts],
    'geometry_revision':'continuous_forged_r5_20261104','geometry_modified_by_material_binding':False,
    'uv_modified_by_material_binding':False,'shape_acceptance':'new continuous R5 geometry awaiting user review',
    'runtime_tested':False},indent=2)+'\n',encoding='utf-8')
