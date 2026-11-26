"""Displace stone faces with the two original scan layers, in centimetres."""
from stone_relief_geometry import (BAKERY, DEST, ED, HILLS, LIST, MASONRY, MATERIALS, RUN,
                                   Image, Path, buffers, gc, json, np, read_mesh, require, u)

REPAIR=u.GeometryScript_MeshRepair


def height_field(source):
    texture=require('/Game/UnrealNormandy/Textures/'+source)
    out=RUN/(source+'.png')
    task=u.AssetExportTask();task.object=texture;task.filename=str(out)
    task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterPNG()
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Cannot extract '+source)
    with Image.open(out) as image:
        # Use wavelengths that can be resolved by the stone geometry. Fine grain stays in the original normal map.
        pixels=np.asarray(image,dtype=float)
    if pixels.ndim==3:
        pixels=pixels[:,:,0]
    field=Image.fromarray(pixels.astype(np.float32)).resize((64,64),Image.Resampling.BOX)
    fine=np.asarray(field,dtype=float)
    broad=np.asarray(field.resize((12,12),Image.Resampling.BOX).resize((64,64),Image.Resampling.BILINEAR),dtype=float)
    detail=.60*(fine-broad)+.40*(fine-np.median(fine))
    span=np.percentile(np.abs(detail),94)
    if span<=0:
        raise RuntimeError('Empty height scan '+source)
    return np.clip(detail/span,-1.,1.)


def bilinear(field,co):
    size=len(field);xy=co*size-.5
    low=np.floor(xy).astype(int);fraction=xy-low
    x,y=(low%size).T;dx,dy=fraction.T
    return ((field[y,x]*(1-dx)+field[y,(x+1)%size]*dx)*(1-dy)
           +(field[(y+1)%size,x]*(1-dx)+field[(y+1)%size,(x+1)%size]*dx)*dy)


def triplanar(field,p,n,tile):
    q=p/tile
    axis=np.abs(n)**4
    axis/=np.maximum(axis.sum(axis=1,keepdims=True),1.e-12)
    # Match the three vertical/horizontal object-space projections onto stone faces.
    return (axis[:,0]*bilinear(field,q[:,[1,2]])+axis[:,1]*bilinear(field,q[:,[0,2]])
            +axis[:,2]*bilinear(field,q[:,[0,1]]))


def selection(dm,tri_ids):
    _,result=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(
        dm,tri_ids.tolist(),u.GeometryScriptMeshSelectionType.TRIANGLES)
    return result


def surfaces(name,p,t,ids,stone):
    cross=np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]])
    size=np.linalg.norm(cross,axis=1)
    n=cross/np.maximum(size,1.e-12)[:,None]
    side=stone[ids] & (np.abs(n[:,2])<.69) & (size>.00001)
    if 'HighPortal' in name:
        mid=p[t].mean(axis=1)
        opening=430 if 'West' in name else 330
        # The grille slides between Y=-15/+15. The jambs and bridge walking course are functional interfaces.
        side&=(np.abs(mid[:,1])>18.) & (np.abs(np.abs(mid[:,0])-opening)>2.5)
    return n,size,side


def move_stone(dm,name,slots,fields,scales):
    original_tris=dm.get_triangle_count()
    # Old authored high walls store a private vertex for every face corner. Stitch coincident
    # boundary pairs first so that selectively inserted edge samples never leave a T-crack.
    REPAIR.weld_mesh_edges(dm,u.GeometryScriptWeldEdgesOptions(tolerance=.00005,only_unique_pairs=True))
    REPAIR.compact_mesh(dm)
    p,t,ids=buffers(dm)
    stone=np.array([slot in MATERIALS for slot in slots],dtype=bool)
    n,area2,side=surfaces(name,p,t,ids,stone)
    chunk='StoneChunk' in name
    edge=np.maximum.reduce([np.linalg.norm(p[t[:,k]]-p[t[:,(k+1)%3]],axis=1) for k in range(3)])
    altitude=area2/np.maximum(edge,1.e-9)
    large=np.flatnonzero(side & (altitude>(1.7 if chunk else 6.5)) & (area2>(13. if chunk else 180.)))
    # A 512 cm scan filtered to 64 samples resolves at 8 cm. Add one linear ring
    # only on its broadest unsupported patches; dense imported stone is already sampled.
    budget=max(12,int(original_tris*.09))
    if len(large)>budget:
        coverage=area2[large]*np.minimum(altitude[large],20.)
        large=large[np.argsort(-coverage,kind='stable')[:budget]]
    if len(large):
        u.GeometryScript_MeshSubdivide.apply_selective_tessellation(dm,selection(dm,large),
            u.GeometryScriptSelectiveTessellateOptions(),1)
        REPAIR.compact_mesh(dm)
        p,t,ids=buffers(dm)
        n,area2,side=surfaces(name,p,t,ids,stone)

    # Where one coincident point has several UV seams, all its copies must move together.
    _,joined=np.unique(np.rint(p*10000).astype(np.int32),axis=0,return_inverse=True)
    joined=joined.reshape(-1);joined_faces=joined[t];count=int(joined.max())+1
    normal=np.zeros((count,3));prohibited=np.zeros(count,dtype=bool)
    for k in range(3):
        np.add.at(normal,joined_faces[:,k],n*area2[:,None])
        prohibited[joined_faces[~side,k]]=True
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1.e-9)
    alignment=np.ones(count)
    for k in range(3):
        np.minimum.at(alignment,joined_faces[:,k],np.sum(n*normal[joined_faces[:,k]],axis=1))
    # Pin all remaining open borders (door and window returns, cut modules and unmatched seams).
    edges=np.vstack((t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]));edges.sort(axis=1)
    unique,counts=np.unique(edges,axis=0,return_counts=True)
    prohibited[joined[unique[counts!=2].ravel()]]=True
    vertex_weight=np.clip((alignment[joined]-.48)/.43,0,1)
    vertex_weight[prohibited[joined]]=0
    if name.startswith(('SM_HighWall','SM_VillageWall','SM_ChapelYardWall')):
        # The original wall kit joins on its 3 m module end planes, even on the wall-space break pieces.
        vertex_weight*=np.clip((np.abs(np.abs(p[:,0])-150.)-1.)/2.,0,1)
    vertex_slot=np.zeros(len(p),dtype=np.int32)
    for k in range(3): vertex_slot[t[:,k]]=ids
    _,colors,have_colors,_=u.GeometryScript_VertexColors.get_mesh_per_vertex_colors(dm,True)
    red=np.fromiter((c.r for c in LIST.convert_color_list_to_array(colors)),dtype=float) if have_colors else np.full(len(p),.5)
    # Equalize the paint used for physical displacement only, leaving the existing split render colors intact.
    red=np.bincount(joined,weights=red,minlength=count)[joined]/np.bincount(joined,minlength=count)[joined]
    normals=normal[joined];depth=np.zeros(len(p))
    for slot in range(len(slots)):
        if not stone[slot]:continue
        active=(vertex_slot==slot) & (vertex_weight>0.)
        if not active.any():continue
        key=slots[slot];s0,s1=scales[key];f0,f1=fields[key]
        basalt=triplanar(f0,p[active],normals[active],s0)
        stone02=triplanar(f1,p[active],normals[active],s1)
        # TS01 is the red vertex-paint layer over the TS00 basalt base.
        blend=np.clip(red[active],0,1)
        amplitude=(.62 if chunk else .95 if 'Gray' in key else 1.45)
        depth[active]=((1.-blend)*basalt+blend*stone02)*amplitude*vertex_weight[active]
    # Keep coincident pieces identical even at a junction between two stone variants.
    depth=np.bincount(joined,weights=depth,minlength=count)[joined]/np.bincount(joined,minlength=count)[joined]
    displaced=np.clip(p+depth[:,None]*normals,p.min(axis=0),p.max(axis=0))
    delta=np.linalg.norm(displaced-p,axis=1)
    if delta.max()<.01:
        raise RuntimeError('No resolved height relief on '+name)
    values=[u.Vector(float(x),float(y),float(z)) for x,y,z in displaced]
    u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,LIST.convert_array_to_vector_list(values))
    triangles=np.flatnonzero(side & np.any(delta[t]>.00001,axis=1))
    u.GeometryScript_Normals.recompute_normals_for_mesh_selection(dm,selection(dm,triangles),u.GeometryScriptCalculateNormalsOptions())
    return dict(input_triangles=original_tris,triangles=dm.get_triangle_count(),refined_faces=len(large),
                moved_positions=int(np.count_nonzero(delta>.001)),max_cm=float(delta.max()),
                rms_cm=float(np.sqrt(np.mean(delta[delta>.001]**2))))


def bake(scan):
    fields={};scales={};cache={}
    for name,data in scan.items():
        pair=[];tile=[]
        for layer in ('TS00','TS01'):
            base=data['textures'][layer+'_BaseColor']
            height=base.rsplit('_',1)[0]+'_Height'
            if height not in cache:cache[height]=height_field(height)
            pair.append(cache[height]);tile.append(data['scales'][layer+'_Triplanar_TileSize'])
        fields[name]=pair;scales[name]=tile
    ED.make_directory(DEST.rstrip('/'))
    paths=[MASONRY+p.stem for p in sorted((RUN/'Content/WorldGeneration/TemperateHills/VillageMasonry').glob('SM_*.uasset'))]+[BAKERY]
    receipt=dict(scans=list(cache),scales=scales,meshes=[])
    for source in paths:
        parent=require(source);name=parent.get_name();destination=DEST+name
        obj=ED.duplicate_asset(source,destination)
        if not obj:raise RuntimeError('Cannot create '+destination)
        slots=[s.material_interface.get_name() if s.material_interface else '' for s in parent.static_materials]
        dm=read_mesh(parent)
        stats=move_stone(dm,name,slots,fields,scales)
        collision=parent.get_editor_property('complex_collision_mesh') or parent
        obj.set_editor_property('complex_collision_mesh',collision)
        opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=False)
        _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,obj,opts,u.GeometryScriptMeshWriteLOD())
        def collision_record(mesh):
            body=mesh.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom')
            return [str(body.get_editor_property('collision_trace_flag')),
                    [len(agg.get_editor_property(key)) for key in ('box_elems','convex_elems','sphere_elems','sphyl_elems')]]
        native_collision=collision_record(parent)
        if collision_record(obj)!=native_collision or obj.get_editor_property('complex_collision_mesh')!=collision:
            raise RuntimeError('Original collision setup was not retained: '+name)
        if outcome!=u.GeometryScriptOutcomePins.SUCCESS or not ED.save_loaded_asset(obj,False):
            raise RuntimeError('Could not save '+destination)
        receipt['meshes'].append(dict(source=source,destination=destination,complex_collision=collision.get_path_name(),simple_collision=native_collision,**stats))
        (RUN/'progress.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
        u.log('STONE_RELIEF_GEOMETRY '+name+' '+str(stats))
        del parent,obj,dm,collision
        gc.collect();u.SystemLibrary.collect_garbage()
    (RUN/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
