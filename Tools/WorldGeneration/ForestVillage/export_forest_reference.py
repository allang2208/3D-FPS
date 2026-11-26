import json,os,struct,unreal as u
from pathlib import Path
out=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_ForestPathVillage')
scene=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
land=next(a for a in scene if isinstance(a,u.Landscape))
L=u.MaterialEditingLibrary
mi=land.get_editor_property('landscape_material')
master=mi.get_base_material()
report={'material':mi.get_path_name(),'master':master.get_path_name(),
        'lighting':[(a.get_class().get_name(),a.get_name(),a.get_level().get_outermost().get_name() if hasattr(a,'get_level') else a.get_path_name().split(':')[0]) for a in scene if isinstance(a,(u.Light,u.SkyLight,u.ExponentialHeightFog,u.SkyAtmosphere,u.VolumetricCloud,u.PostProcessVolume))],
        'nodes':[],'grass':[],'pcg':{}}
for node in L.get_material_expressions(master):
    row=[node.get_name(),str(node.get_editor_property('desc'))]
    if isinstance(node,u.MaterialExpressionLandscapeLayerBlend):
        row.append([(str(e.get_editor_property('layer_name')),str(e.get_editor_property('blend_type'))) for e in node.get_editor_property('layers')])
    if isinstance(node,u.MaterialExpressionMaterialFunctionCall):
        fn=node.get_editor_property('material_function');row.append(fn.get_path_name() if fn else '')
    report['nodes'].append(row)
grass=u.load_asset('/Game/Landscape/Materials/LandscapeGrass/LG_A')
for g in grass.get_editor_property('grass_varieties'):
    mesh=g.get_editor_property('grass_mesh')
    if mesh: report['grass'].append([mesh.get_path_name(),g.get_editor_property('grass_density').get_editor_property('default'),str(g.get_editor_property('scaling')),str(g.get_editor_property('scale_x')),str(g.get_editor_property('scale_y')),str(g.get_editor_property('scale_z')),g.get_editor_property('align_to_surface'),g.get_editor_property('end_cull_distance').get_editor_property('default')])
(out/'reference.json').write_text(json.dumps(report,indent=2))
report['footprints']={}
for a in scene:
    if isinstance(a,u.PCGVolume):
        groups={}
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=c.static_mesh
            if not mesh:continue
            name=mesh.get_name()
            box=mesh.get_bounding_box()
            center=(box.min+box.max)*.5
            half=(box.max-box.min)*.5
            report['footprints'][name]=[center.x*.01,center.y*.01,max(half.x,half.y)*.01]
            data=bytearray()
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,world_space=True)
                data.extend(struct.pack('<8f',t.translation.x,t.translation.y,t.translation.z,t.rotation.rotator().yaw,t.scale3d.x,t.scale3d.y,t.scale3d.z,t.rotation.rotator().pitch))
            (out/(name+'.f32')).write_bytes(data)
            groups[name]=[c.get_instance_count(),mesh.get_path_name()]
        report['pcg'][a.get_actor_label()]=groups
(out/'reference.json').write_text(json.dumps(report,indent=2))
