"""Extract manufactured geometry; no gameplay, screenshot or acceptance run."""
from pathlib import Path
import unreal as u,json,collections
R=Path(__file__).resolve().parent
BASE='/Game/NativeNearBank20261028'

def export(world):
    rows=[];required=set();spline_count=0
    def path(obj):
        if not obj:return None
        p=obj.get_path_name();required.add(p.split('.')[0]);return p
    def tr(t):return dict(p=list(t.translation.to_tuple()),q=list(t.rotation.to_tuple()),s=list(t.scale3d.to_tuple()))
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if not c.static_mesh:continue
            row=dict(actor=a.get_actor_label(),component=c.get_name(),mesh=path(c.static_mesh),materials=[path(m) for m in c.get_materials()],transforms=[])
            if isinstance(c,u.InstancedStaticMeshComponent):
                row['transforms']=[tr(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())]
                row['custom_stride']=c.get_editor_property('num_custom_data_floats')
                if row['custom_stride']:row['custom_data']=list(c.get_editor_property('per_instance_sm_custom_data'))
            else:row['transforms']=[tr(c.get_world_transform())]
            if isinstance(c,u.SplineMeshComponent):
                spline_count+=1
                row['spline']=dict(start=list(c.get_start_position().to_tuple()),end=list(c.get_end_position().to_tuple()),start_tangent=list(c.get_start_tangent().to_tuple()),end_tangent=list(c.get_end_tangent().to_tuple()),start_scale=list(c.get_start_scale().to_tuple()),end_scale=list(c.get_end_scale().to_tuple()),start_roll=c.get_start_roll(),end_roll=c.get_end_roll(),axis=str(c.get_forward_axis()))
            if row['transforms']:rows.append(row)
        for i,c in enumerate(a.get_components_by_class(u.DynamicMeshComponent)):
            mesh=c.get_dynamic_mesh()
            if not mesh or not mesh.get_triangle_count():continue
            name=f'SM_BakedSurface_{len(rows):05d}'
            options=u.GeometryScriptCreateNewStaticMeshAssetOptions();options.enable_collision=True;options.collision_mode=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            result=u.GeometryScriptLibrary_CreateNewAssetFunctions.create_new_static_mesh_asset_from_mesh(mesh,BASE+'/Meshes/'+name,options)
            sm=result[0] if isinstance(result,tuple) else result
            if not sm:raise RuntimeError('Cannot bake generated surface '+name)
            for j,m in enumerate(c.get_materials()):sm.set_material(j,m)
            u.EditorAssetLibrary.save_loaded_asset(sm,False)
            rows.append(dict(actor=a.get_actor_label(),component=c.get_name(),mesh=path(sm),materials=[path(m) for m in c.get_materials()],transforms=[tr(c.get_world_transform())]))
    manifest=dict(stage='native_output_extracted',rows=rows,counts=dict(components=len(rows),instances=sum(len(r['transforms']) for r in rows),meshes=len({r['mesh'] for r in rows}),spline_components=spline_count),required_roots=sorted(required))
    (R/'native_manifest.json').write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    ar=u.AssetRegistryHelpers.get_asset_registry()
    ar.search_all_assets(True)
    options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
    closure={};pending=list(required)
    while pending:
        p=pending.pop()
        if p in closure or p.startswith(('/Engine/','/Script/')):continue
        deps=[str(d) for d in ar.get_dependencies(p,options)]
        closure[p]=deps;pending.extend(deps)
    (R/'native_dependencies.json').write_text(json.dumps(closure,indent=2),encoding='utf8')
    print('NATIVE_MANIFEST_SAVED',manifest['counts'],'packages',len(closure),flush=True)

if __name__=='__main__':
    world=u.EditorLoadingAndSavingUtils.load_map(BASE+'/AuthoringState')
    export(world)
