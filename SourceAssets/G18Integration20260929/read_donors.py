import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
sources={
 'single':'M1911ReloadTiming20260913/M1911_ReloadReady_Editable.blend',
 'bare':'ModularOutfit20260925/BarePalmV7/Editable/M1911_BareArmsV7.blend',
 'dual_r':'PistolDualWield20260914/NaturalAimV3/M1911/r/M1911_r_Dual_Editable.blend',
 'dual_l':'PistolDualWield20260914/NaturalAimV3/M1911/l/M1911_l_Dual_Editable.blend',
}
out={}
for key,path in sources.items():
    if not (S/path).exists():continue
    try:bpy.ops.wm.open_mainfile(filepath=str(S/path))
    except RuntimeError as e:
        if 'Missing library override hierarchy root data' not in str(e):raise
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    r=next((o for o in rigs if 'WPN_root' in o.data.bones),rigs[0])
    root=r.data.bones.get('WPN_root');inv=root.matrix_local.inverted() if root else r.matrix_world.inverted()
    meshes=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        xf=inv@r.matrix_world.inverted()@ob.matrix_world;vv=[xf@v.co for v in ob.data.vertices]
        meshes.append({'name':ob.name,'n':len(vv),'materials':[m.name if m else '' for m in ob.data.materials], 'min':[min(v[i] for v in vv) for i in range(3)],'max':[max(v[i] for v in vv) for i in range(3)]})
    out[key]={'source':path,'rig':r.name,'bones':{b.name:[list(x) for x in inv@b.matrix_local] for b in r.data.bones if b.name.startswith('WPN')},'meshes':meshes,'actions':[{'name':a.name,'frames':list(a.frame_range)} for a in bpy.data.actions if a.name.startswith(('M1911','Dual_','A_Dual'))]}
(O/'donor_geometry.json').write_text(json.dumps(out,indent=2))
print('DONOR_READ_COMPLETE')
