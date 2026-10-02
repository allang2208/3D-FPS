"""Read actual M16 source/render geometry for the reported missing digits."""
import json, hashlib
from pathlib import Path
import unreal as u

O = Path(__file__).parent / 'DisplayDiagnosis'
O.mkdir(parents=True, exist_ok=True)
P = Path(u.Paths.project_dir()).resolve()
C = json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
SOURCE = '/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny.SK_M16_Manny'
profile = C['profiles'][SOURCE]
G, Q, B = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_BoneWeights
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def xyz(v): return [v.x,v.y,v.z]
report = {}
for key, path in [('Gun',SOURCE),('V7',profile['base']),('Skin',profile['native_bare_skin'])]:
    a = u.load_asset(path)
    rows = []
    for kind, lod in [('Source',0)]+[('Render',i) for i in range(S.get_lod_count(a))]:
        requested = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL if kind=='Source' else u.GeometryScriptLODType.RENDER_DATA,lod_index=lod)
        dm, result = G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),requested)
        if result != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read '+path+' '+kind+str(lod))
        _, bl = B.get_all_bones_info(dm)
        names={b.index:str(b.name) for b in bl}
        _,pl,_=Q.get_all_vertex_positions(dm,False)
        ps=u.GeometryScript_List.convert_vector_list_to_array(pl)
        _,tl,_=Q.get_all_triangle_indices(dm,False)
        ts=u.GeometryScript_List.convert_triangle_list_to_array(tl)
        arm_ids=profile['hide_source_materials'] if key=='Gun' else list(range(len(a.materials)))
        faces=[]; materials=[]
        for i,t in enumerate(ts):
            mat,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
            if valid and mat in arm_ids: faces.append(xyz(t));materials.append(mat)
        ids=sorted({v for t in faces for v in t});remap={v:i for i,v in enumerate(ids)}
        ws=[];counts={}
        for vi in ids:
            _,weights,valid=B.get_vertex_bone_weights(dm,vi)
            w={names[x.bone_index]:x.weight for x in weights if x.weight>0}
            ws.append(w)
            for n,x in w.items(): counts[n]=counts.get(n,0)+1
        data=dict(path=path,lod=lod,kind=kind,positions=[xyz(ps[i]) for i in ids],weights=ws,
            triangles=[[remap[v] for v in t] for t in faces],triangle_materials=materials,
            bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
                axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bl})
        (O/(key+'_'+kind+str(lod)+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
        rows.append(dict(kind=kind,lod=lod,vertices=len(ids),triangles=len(faces),bone_vertex_counts=counts))
    report[key]=dict(path=path,skeleton=a.skeleton.get_path_name(),lod_count=S.get_lod_count(a),
        slots=[dict(slot=str(s.material_slot_name),material=s.material_interface.get_path_name() if s.material_interface else None) for s in a.materials],geometry=rows)
(O/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('CLOVEN_M16_DISPLAY_GEOMETRY_READ')
