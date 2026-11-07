"""Measure the installed optic contact faces for the requested rail investigation."""
from pathlib import Path
import bpy,numpy as np,json
O=Path(__file__).resolve().parent
recipe=json.loads((O.parent/'M24CommonOptics20261028/fit_recipe.json').read_text())['assets']
report={}
for key in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic','kv_scope_4x','thermal_scope','m24_custom_scope_6x','m24_palma_iron'):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(key+'.fbx')))
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data;me.calc_loop_triangles()
    v=np.array([ob.matrix_world@p.co for p in me.vertices]);f=np.array([t.vertices for t in me.loop_triangles])
    if key in recipe:
        row=recipe[key];z=row['contact_plane_local_z_cm']*.01
        on=np.all(np.abs(v[f,2]-z)<.000015,axis=1)
        ids=np.unique(f[on]);p=v[ids]
        report[key]={'contact_face_count':int(on.sum()),'local_contact_z_m':z,'mounted_contact_z_m':z+row['source_translation_cm'][2]*.01,
            'contact_forward_span_m':(np.array([p[:,0].min(),p[:,0].max()])-row['source_translation_cm'][1]*.01).tolist() if len(p) else None,
            'transform_changed':False}
    else:
        tri=v[f];mid=tri.mean(1);use=(np.ptp(tri[:,:,2],axis=1)<.000015)&(np.abs(mid[:,0])<.014)&(mid[:,1]>.10)&(mid[:,1]<.285)&(mid[:,2]>.135)&(mid[:,2]<.147)
        levels,counts=np.unique(np.round(mid[use,2],5),return_counts=True)
        report[key]={'native_frame_horizontal_mount_levels_m':dict(zip(map(str,levels),map(int,counts))),'transform_changed':False}
(O/'optic_contacts.json').write_text(json.dumps(report,indent=2))
print('M24_OPTIC_CONTACTS',report)
