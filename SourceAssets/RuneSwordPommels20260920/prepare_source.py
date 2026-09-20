"""Read manufacturing dimensions and retain original face-corner attributes."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
materials=P.parent/'RuneSword20260913/CompactNaturalV4/AzureRunesword_Manny_Editable.blend'
with bpy.data.libraries.load(str(materials),link=False) as (src,dst):dst.materials=['M_AzureRunesword']
stock=dst.materials[0]
source=P.parent/'RuneSwordModules20260919/Export/SM_RuneSword_Pommel_factory.fbx'
info={}
for name,path in [('FactoryPommel',source),('StockCollar',P/'Interface/StockCollar.fbx')]:
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(path))
    obj=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
    obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4);obj.name=name
    obj.data.materials.clear();obj.data.materials.append(stock)
    co=[v.co for v in obj.data.vertices]
    row={'bounds_m':[[min(v[i] for v in co) for i in range(3)],[max(v[i] for v in co) for i in range(3)]],'bands':[]}
    for depth in [0,.003,.006,.009,.012,.015,.02,.03,.045,.06,.08]:
        band=[v for v in co if abs(v.z+depth)<.002]
        if band:row['bands'].append({'z':-depth,'radius_x':max(abs(v.x) for v in band),'radius_y':max(abs(v.y) for v in band),'vertices':len(band)})
    info[name]=row;obj.hide_set(True);obj.hide_render=True
info['material_images']=[n.image.filepath for n in stock.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
(P/'source_dimensions.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Interface/SourceInterface.blend'))
print('SOURCE_DIMENSIONS',json.dumps(info))
