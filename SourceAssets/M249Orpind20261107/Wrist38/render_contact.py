"""Render actual newly exported UE skin for contact inspection, not pose synthesis."""
import ast,json
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector

HERE=Path(__file__).resolve().parent
capture=HERE.parent/'Wrist34/geometry_wrist_thirty_eight_clearance'
out=HERE/'contact_clearance';out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=800;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.color=(.075,.075,.075)
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
tree=ast.parse((HERE.parent/'Wrist37/render_final.py').read_text())
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef)],type_ignores=[]),'helpers','exec'))
skin=mat('Skin',(.58,.34,.22));metal=mat('Gun',(.14,.19,.23));brass=mat('Belt',(.56,.38,.13))
inventory=[]
for folder in sorted(capture.glob('box_*_base')):
    meta=json.loads((folder/'geometry.json').read_text());rows=json.loads((folder/'review.json').read_text())['frames']
    dominant=np.fromfile(folder/'dominant.bin',np.uint32);names=meta['bones'];slots=meta['slots']
    offset=.9 if 'empty' in folder.name else 0
    for i,row in enumerate(rows):
        if row['source']<4.19-offset:continue
        stem=folder/Path(row['file']).stem
        p=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3)*[1,-1,1]
        faces=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3)
        materials=np.fromfile(stem.with_suffix('.materials'),np.uint32)
        center=p[dominant==names.index('hand_r')].mean(0)
        for view,delta in [('palm',[-60,-20,18]),('outside',[60,10,25])]:
            for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
            visible=np.isin(materials,row['visible_materials'])
            sk=np.array([s.startswith('Skin_') for s in slots])[materials]
            right=np.array([n.endswith('_r') for n in names])[dominant]
            belt=np.array(['Belt' in s for s in slots])[materials]
            glass=np.array(['Glass' in s or 'Reticle' in s for s in slots])[materials]
            mesh('Skin',p,faces[visible&sk&right[faces].any(1)],skin)
            mesh('Gun',p,faces[visible&~sk&~belt&~glass],metal)
            mesh('Belt',p,faces[visible&~sk&belt],brass)
            for part in folder.glob(stem.name+'_*.vertices'):
                mesh(part.stem,np.fromfile(part,np.float32).reshape(-1,3)*[1,-1,1],np.fromfile(part.with_suffix('.indices'),np.uint32).reshape(-1,3),metal)
            cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);scene.collection.objects.link(co);scene.camera=co
            co.location=center+np.array(delta);co.rotation_euler=(Vector(center)-co.location).to_track_quat('-Z','Y').to_euler()
            cam.type='ORTHO';cam.ortho_scale=25;cam.clip_start=.1
            name=f'{folder.name}_{i:03d}_{view}.png';scene.render.filepath=str(out/name);bpy.ops.render.render(write_still=True)
            inventory.append(dict(image=name,case=folder.name,view=view,source=row['source']))
        # Remove orphan data blocks as this review makes many temporary meshes.
        for data in [bpy.data.meshes,bpy.data.cameras]:
            for block in list(data):
                if block.users==0:data.remove(block)
(HERE/'contact_clearance_inventory.json').write_text(json.dumps(inventory,indent=2))
