"""Read the V3 import and active outfit bindings without modifying the game."""
import collections,json
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/Saved/M4RefinedSkinRepair20260924');out.mkdir(parents=True,exist_ok=True)
report={'assets':[],'components':[]}
for path in ('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
 '/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4RefinedV3/SK_M4_OriginalShape_BareHands'):
    asset=u.load_asset(path)
    dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    names={b.index:str(b.name) for b in bones}
    _,triangles,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
    ts=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    counts=collections.Counter();samples=[]
    for i,t in enumerate(ts):
        mat,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
        if valid:counts[mat]+=1
    _,positions,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
    ps=u.GeometryScript_List.convert_vector_list_to_array(positions)
    stats=collections.Counter();sums=[]
    for i,p in enumerate(ps):
        _,ws,valid=u.GeometryScript_BoneWeights.get_vertex_bone_weights(dm,i)
        if not valid:continue
        sums.append(sum(w.weight for w in ws))
        for w in ws:stats[names.get(w.bone_index,str(w.bone_index))]+=w.weight
        if i%500==0:samples.append({'id':i,'p':[p.x,p.y,p.z],'weights':{names.get(w.bone_index,str(w.bone_index)):w.weight for w in ws}})
    row={'path':path,'materials':[str(m.material_interface.get_path_name()) if m.material_interface else None for m in asset.materials],
      'triangles':len(ts),'material_counts':dict(counts),'vertices':len(ps),'bone_total_weights':dict(stats),
      'weight_sum_range':[min(sums),max(sums)],'samples':samples,
      'bones':[{'index':b.index,'name':str(b.name),'parent':b.parent_index,'local':str(b.local_transform)} for b in bones]}
    report['assets'].append(row)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['playing']=bool(world)
report['candidate_cvar']=u.SystemLibrary.get_console_variable_int_value('fps.Outfit.BareArmsCandidate')
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Pawn):
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=c.get_editor_property('skeletal_mesh_asset')
            if not mesh:continue
            report['components'].append({'actor':actor.get_name(),'component':c.get_name(),'mesh':mesh.get_path_name(),
                'visible':c.is_visible(),'tags':[str(t) for t in c.component_tags],
                'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
(out/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('REFINED_SKIN_DIAGNOSIS',json.dumps({**report,'assets':[{k:v for k,v in r.items() if k not in ('samples','bones')} for r in report['assets']]},ensure_ascii=False))
