"""Separate the root-mounted reserve from the animated loose reload cartridge."""
import bpy

MOUNTED_SLOT='12gauge_mounted'

def separate_mounted_shell(parts):
    material=bpy.data.materials.get(MOUNTED_SLOT)
    if material is None:
        material=bpy.data.materials['12gauge'].copy();material.name=MOUNTED_SLOT
    changed={}
    for ob in parts:
        selected=[]
        for face in ob.data.polygons:
            if ob.data.materials[face.material_index].name!='12gauge':continue
            if all(any(ob.vertex_groups[g.group].name=='WPN_root' and g.weight>.99
                       for g in ob.data.vertices[vi].groups) for vi in face.vertices):
                selected.append(face)
        if selected:
            index=ob.data.materials.find(MOUNTED_SLOT)
            if index<0:ob.data.materials.append(material);index=len(ob.data.materials)-1
            for face in selected:face.material_index=index
            changed[ob.name]=len(selected)
    return changed
