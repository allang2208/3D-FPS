import bpy, json
from pathlib import Path

base = Path(__file__).parents[1]
sources = {
    'M1911': base/'M1911CompactFit20260913/M1911_CompactFit_Assembly_Editable.blend',
    'M1911_tactical': base/'M1911CompactFit20260913/M1911_CompactTactical_Assembly_Editable.blend',
    'DW715': base/'DanWesson715Attachments20260914/DanWesson715_Attachments_Editable.blend',
    'V3': Path(__file__).parent/'VideoRefV3/M1911/r/M1911_r_QuickCombat_Editable.blend'
}
report = {}
for name, path in sources.items():
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
    except RuntimeError as e:
        if 'Missing library override hierarchy root data' not in str(e): raise
    report[name] = [{'name':o.name, 'type':o.type,
                     'parent': o.parent.name if o.parent else None,
                     'bone':o.parent_bone, 'visible':not o.hide_render,
                     'verts':len(o.data.vertices) if o.type=='MESH' else None,
                     'position':list(o.location)} for o in bpy.context.scene.objects
                    if o.type in ('ARMATURE','MESH','CAMERA')]
out = Path(__file__).parents[2]/'Saved/DualPistolQuickCombat20260920/attachment-source-layout.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
