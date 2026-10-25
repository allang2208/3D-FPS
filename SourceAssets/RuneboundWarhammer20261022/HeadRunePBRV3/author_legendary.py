"""Reuse each retained construction, refine its materials and bake true normals."""
import bpy,sys,types,json
from pathlib import Path
P=Path(__file__).resolve().parent;FAMILY=P.parent
sys.path.insert(0,str(P))
from surface_authoring import refine_metal,transfer_runes,engrave_native
kind=sys.argv[sys.argv.index('--')+1]
source=FAMILY/('StarOathHammerHeadV1' if kind=='star_oath' else 'FinalTollHammerHeadV2')/'author_model.py'
job=P/kind;job.mkdir(exist_ok=True)
code=source.read_text('utf-8')
code=code.replace("P.parent/'ModulesV1/RuneboundWarhammer_Modular_Editable.blend'",repr(str(FAMILY/'ModulesV1/RuneboundWarhammer_Modular_Editable.blend')))
old='StarOathHammerHeads_V1' if kind=='star_oath' else 'FinalTollHammerHeads_V2'
new='StarOathHammerHeads_PBRV3' if kind=='star_oath' else 'FinalTollHammerHeads_PBRV3'
code=code.replace(old,new).replace('scene.cycles.samples=16','scene.cycles.samples=32').replace('scene.render.bake.margin=8','scene.render.bake.margin=16')
(job/'construction_source.py').write_text(code,encoding='utf-8')
module=types.ModuleType('retained_construction');module.__file__=str(job/'construction_source.py')
exec(compile(code,module.__file__,'exec'),module.__dict__)
module.initialize()
for material in list(bpy.data.materials):
    if material.name.startswith('AUTHOR_') or 'FineInlay' in material.name:refine_metal(material)
module.build_head(-1);module.build_head(1)
old_bake=module.bake_maps
def bake_with_native(obj):
    image=transfer_runes(obj,job/'Textures'/('T_'+('StarOath' if kind=='star_oath' else 'FinalToll')+'_NativeRune.png'))
    for mat in obj.data.materials:engrave_native(mat,image)
    return old_bake(obj)
module.bake_maps=bake_with_native
# Fine inlays retain their own UV density and get actual maps too; UE must not
# replace the source's brushed brass with an untextured constant material.
prefix='StarOath' if kind=='star_oath' else 'FinalToll'
inlay_code=code[code.index('def bake_maps('):code.index('\ndef finalize(')]
inlay_code=inlay_code.replace('def bake_maps(', 'def bake_inlay_maps(').replace('4096','1024')
inlay_code=inlay_code.replace('T_'+prefix+'_','T_'+prefix+'_Inlay_').replace('M_'+prefix+'_PBR_Surface','M_'+prefix+'_FineInlay_Brass')
exec(compile(inlay_code,'<inlay_material_bake>','exec'),module.__dict__)
old_unwrap=module.unwrap
def unwrap_and_bake_inlay(obj):
    old_unwrap(obj)
    if obj.name.endswith('Fine_Inlay'):module.bake_inlay_maps(obj)
module.unwrap=unwrap_and_bake_inlay
module.finalize()
receipt=json.loads((job/'production_receipt.json').read_text('utf-8'))
receipt['native_rune_texture']=str(job/'Textures'/('T_'+('StarOath' if kind=='star_oath' else 'FinalToll')+'_NativeRune.png'))
receipt['rune_uv_channel']=0;receipt['refinement']='Real tangent normal bake, anisotropic machining, forge pores, original rune incisions'
(job/'production_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
