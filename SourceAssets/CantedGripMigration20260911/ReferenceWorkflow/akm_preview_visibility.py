import bpy,bmesh

def configure_preview(drum=False,variant='base'):
    gun=bpy.data.objects['AKM_Soviet_Native']
    magazine=bpy.data.objects.get('AKM_FactoryMagazine_Preview')
    if magazine is None:
        magazine=gun.copy();magazine.data=gun.data.copy();magazine.name='AKM_FactoryMagazine_Preview';gun.users_collection[0].objects.link(magazine)
        # Editable preview objects remain separately selectable, with their original armature/weights.
        for obj,keep_magazine in [(gun,False),(magazine,True)]:
            bm=bmesh.new();bm.from_mesh(obj.data)
            bmesh.ops.delete(bm,geom=[f for f in bm.faces if (f.material_index==1)!=keep_magazine],context='FACES')
            loose=[v for v in bm.verts if not v.link_faces]
            if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
            bm.to_mesh(obj.data);bm.free();obj.data.update()
    magazine.hide_render=drum;magazine.hide_set(drum)
    for obj in bpy.context.scene.objects:
        if obj.name.startswith('SM_AKM_'):
            visible=obj.name=='SM_AKM_'+variant or (drum and obj.name=='SM_AKM_drum')
            obj.hide_render=not visible;obj.hide_set(not visible)
    return magazine
