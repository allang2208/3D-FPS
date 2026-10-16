"""Transfer the authored detail UVs into the channel used by UE tangents."""
DETAIL_MATERIALS={'ManualAntiqueBrass','ManualLeatherBinding'}

def repair_binding_uv(obj):
    mesh=obj.data
    # Joined primitives carried Blender's localized UV layer name. Their main
    # UVMap was consequently filled with zeroes; the actual unwrap is intact.
    primary=mesh.uv_layers['UVMap'].data
    authored=mesh.uv_layers['UV贴图'].data
    changed_faces=changed_loops=0
    for face in mesh.polygons:
        if mesh.materials[face.material_index].name not in DETAIL_MATERIALS:continue
        changed=False
        for index in face.loop_indices:
            if primary[index].uv!=authored[index].uv:
                primary[index].uv=authored[index].uv
                changed_loops+=1;changed=True
        if changed:changed_faces+=1
    mesh.uv_layers.active_index=0
    mesh.uv_layers[0].active_render=True
    mesh.update()
    return dict(faces=changed_faces,loops=changed_loops,source_uv='UV贴图',destination_uv='UVMap')
