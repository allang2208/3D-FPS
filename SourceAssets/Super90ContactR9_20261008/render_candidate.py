from pathlib import Path
O=Path(__file__).parent;old=O.parent/'Super90ContactR8_20261008/render_saved.py';ns={'__file__':str(old)}
exec(compile(old.read_text().split('items=[]')[0],str(old),'exec'),ns)
bpy=ns['bpy'];s=ns['s'];Matrix=ns['Matrix'];scene=ns['scene']
driver='WPN_SOCKET_Magazine';transform=s['rest'][driver]@Matrix.Diagonal((*s['hand_fit'].get('loader_bar_scale',[1,1,1]),1))@s['rest'][driver].inverted()
for ob in ns['groups']['props']:
    for v in ob.data.vertices:
        if any(ob.vertex_groups[g.group].name==driver and g.weight>.99 for g in v.groups):v.co=ob.matrix_world.inverted()@transform@ob.matrix_world@v.co
# Replace the old embedded yoke and add the fitted link in native bind space.
for ob in ns['groups']['props']:
 bm=ns['bmesh'].new();bm.from_mesh(ob.data)
 doomed=[f for f in bm.faces if 'Rod' in ob.data.materials[f.material_index].name]
 ns['bmesh'].ops.delete(bm,geom=doomed,context='FACES');bm.to_mesh(ob.data);bm.free()
ge={};exec(compile((O/'prop_geometry.py').read_text(),str(O/'prop_geometry.py'),'exec'),ge)
cv,cf=ge['connector_mesh']();mesh=bpy.data.meshes.new('R9 fitted slider');mesh.from_pydata([s['rest'][driver]@v for v in cv],[],cf);ob=bpy.data.objects.new('R9 slider link',mesh);scene.collection.objects.link(ob)
mat=bpy.data.materials.new('R9 link blue');mat.diffuse_color=(.08,.35,.65,1);mesh.materials.append(mat)
rig=ns['rigs']['props'];ob.parent=rig;vg=ob.vertex_groups.new(name=driver);vg.add(list(range(len(cv))),1,'REPLACE');mod=ob.modifiers.new('Native link','ARMATURE');mod.object=rig
# Match this mesh's native bind coordinates to the imported skeleton.
ob.data.transform(ns['binds']['props'][driver]@s['rest'][driver].inverted());ns['groups']['props'].append(ob)
frames=O/'Diagnostics/Frames';frames.mkdir(exist_ok=True)
for empty,selected in ((False,(0,74,87,100,114,118,122,128,138,146)),(True,(134,146,158,170,182))):
 for f in selected:
    ns['apply'](s['pose'](f,7,empty)[0])
    for ob in ns['groups']['props']:ob.hide_render=not(74<=f<127)
    scene.render.filepath=str(frames/f'{"empty" if empty else "normal"}_{f:03d}.png');bpy.ops.render.render(write_still=True)
