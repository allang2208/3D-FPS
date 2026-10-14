"""Deterministic tabletop placement in the source kit frame (centimetres).

Used by author_standalone.py before final joining. The table, lamp, rag, vise,
socket rail and original metal tray remain fixed; only loose props move.
"""
import json,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector

LAYOUT={
 'SM_WBK_Fab_Wall_Hammer':(38,217,0,'flat',None),
 'SM_WBK_Fab_Wall_Adjustable_Wrench':(66,215,-4,'flat',None),
 'SM_WBK_Fab_Wall_Hand_Saw':(192,199,0,'keep',None),
 'SM_WBK_Fab_Bench_Wrench':(36,106,0,'keep',None),
 'SM_WBK_Fab_Bench_Screwdriver':(87,241,0,'keep',None),
 'SM_WBK_Fab_Bench_Pliers':(78,180,0,'keep',None),
 'SM_WBK_Fab_Bench_Chisel':(54,183,90,'keep',None),
 'clutter_blueprint_a':(57,145,-8,'keep',None),
 'clutter_blueprint_b':(65,18,19,'keep',None),
 'clutter_scroll_1':(28,31,78,'keep',None),
 'clutter_scroll_2':(36,33,98,'keep',None),
 'clutter_book_1':(72,108,0,'keep',None),
 'clutter_book_2':(70,110,0,'keep',None),
 'clutter_book_3':(74,106,0,'keep',None),
 'clutter_openbook':(123,221,0,'keep',None),
 'clutter_pencil':(84,148,56,'keep',94.06),
 'clutter_tray':(66,247,0,'keep',None),
}

def apply_layout(parts,clutter,out):
    objects={o.name:o for o in parts+clutter}
    def bounds(o):
        v=[o.matrix_world@v.co for v in o.data.vertices]
        return [min(c[i] for c in v) for i in range(3)],[max(c[i] for c in v) for i in range(3)]
    original={name:bounds(o) for name,o in objects.items()}
    for name,(x,y,yaw,orientation,z_cm) in LAYOUT.items():
        ob=objects[name];me=ob.data
        me.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
        if orientation=='flat':
            xyz=np.array([v.co[:] for v in me.vertices]);center=xyz.mean(axis=0)
            values,axes=np.linalg.eigh(np.cov((xyz-center).T))
            # Put the two broad axes on the desk and the thinnest axis vertical.
            rot=np.stack((axes[:,1],axes[:,2],axes[:,0]))
            if np.linalg.det(rot)<0:rot[0]*=-1
            me.transform(Matrix(rot.tolist()).to_4x4())
        me.transform(Matrix.Rotation(math.radians(yaw),4,'Z'))
        lo,hi=bounds(ob)
        bottom=(z_cm/100) if z_cm is not None else .9392
        if name.startswith('clutter_book_'):bottom=original[name][0][2]
        me.transform(Matrix.Translation(Vector((-x/100-(lo[0]+hi[0])/2,-y/100-(lo[1]+hi[1])/2,bottom-lo[2]))))
        me.update()
    # Spread the original seven nails within the original tray, with no overlaps.
    tray_lo,tray_hi=bounds(objects['clutter_tray'])
    centers=[(-4.5,-3),(-.2,-3),(4.1,-3),(-4.5,0),(-.2,0),(4.1,0),(0,3.8)]
    for i,(dx,dy) in enumerate(centers):
        ob=objects['clutter_nail_%d'%i];me=ob.data
        # The head-supported original mesh is rotated in XY only.
        coords=np.array([v.co[:] for v in me.vertices]);values,axes=np.linalg.eigh(np.cov(coords[:,:2].T))
        direction=axes[:,1];angle=math.atan2(direction[1],direction[0])
        me.transform(Matrix.Rotation(-angle,4,'Z'))
        lo,hi=bounds(ob)
        me.transform(Matrix.Translation(Vector((-.66+dx/100-(lo[0]+hi[0])/2,-2.47+dy/100-(lo[1]+hi[1])/2,tray_hi[2]+.0002-lo[2]))));me.update()
    receipt=[]
    for name,ob in objects.items():
        lo,hi=bounds(ob)
        receipt.append({'name':name,'min_cm':[round(v*100,4) for v in lo],'max_cm':[round(v*100,4) for v in hi],'moved':name in LAYOUT or name.startswith('clutter_nail_')})
    (out/'layout_tabletop.json').write_text(json.dumps({'revision':'layout-20261004','support_z_cm':93.9,'components':receipt},indent=2),encoding='utf-8')
    # Save separately editable components, excluding unrelated objects from the kit.
    for ob in list(bpy.data.objects):
        if ob not in objects.values():bpy.data.objects.remove(ob,do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'WorkbenchLayout_Editable.blend'))

