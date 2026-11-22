"""Headless production authoring of the fitted mill-lane bakery meshes."""
import hashlib
import json
import os
import sys
from pathlib import Path

import unreal as u

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bakery_shell import PACK
from shell_geometry import models


HILLS='/Game/WorldGeneration/TemperateHills/'
CHAPEL=HILLS+'OldChapel/Materials/M_Chapel'
HEARTH='/Game/WorldGeneration/VillageTavern/KitchenHearth/M_TavernHearth'
SURFACES={
    'Mortar':CHAPEL+'Limewash', 'Fieldstone':CHAPEL+'Wall', 'Plaster':CHAPEL+'Limewash',
    'Oak':HILLS+'VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak',
    'Sawn':HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterSawn', 'DarkWood':CHAPEL+'Timber',
    'Iron':HILLS+'VillageCarpenter/Props/Surfaces/M_CarpenterIron',
    'Glass':CHAPEL+'Glass','Slate':CHAPEL+'Slate','Lead':CHAPEL+'Lead','Flags':CHAPEL+'Flagstone',
    'Hearth':HILLS+'VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_HearthStone',
    'Soot':HILLS+'VillageBlacksmith/ChimneyR8/Materials/M_ChimneyFlueSoot',
    'Firebrick':HILLS+'VillageBlacksmith/LoftR3/Materials/M_LoftFirebrick',
    'Ash':HEARTH+'Ash','Coal':HEARTH+'Coal','Ember':HEARTH+'Ember',
}

def main():
    materials={m:u.load_asset(path) for m,path in SURFACES.items()}
    for key,obj in materials.items():
        if obj is None:
            raise RuntimeError('Missing bakery surface '+SURFACES[key])
    digest=hashlib.sha256((HERE/'shell_geometry.py').read_bytes()+Path(__file__).read_bytes()).hexdigest()
    editor=u.EditorAssetLibrary
    editor.make_directory(PACK)
    receipt={}
    selected={part for part in os.environ.get('BAKERY_ARCHITECTURE_PARTS','').split(',') if part}
    for part,model in models().items():
        if selected and part not in selected:
            continue
        path=PACK+'/SM_Bakery_'+part
        asset=editor.load_asset(path) if editor.does_asset_exist(path) else None
        faces=sum(len(row[3]) for row in model.slots.values())
        if asset and editor.get_metadata_tag(asset,'BakeryArchitectureSource')==digest:
            receipt[part]=dict(mesh=path,triangles=faces)
            continue
        dm=u.DynamicMesh()
        names=list(model.slots)
        for idx,name in enumerate(names):
            vertices,normals,uvs,indices=model.slots[name]
            buf=u.GeometryScriptSimpleMeshBuffers()
            buf.vertices=[u.Vector(*p) for p in vertices]
            buf.normals=[u.Vector(*p) for p in normals]
            buf.uv0=[u.Vector2D(*p) for p in uvs]
            buf.triangles=[u.IntVector(*p) for p in indices]
            u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buf,material_id=idx)
        collision=part!='Flashing'
        if not asset:
            opts=u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=True,enable_collision=collision,enable_nanite=False)
            asset,outcome=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,opts)
            if not asset or outcome!=u.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError('Failed to author '+path)
        nanite=asset.get_editor_property('nanite_settings')
        # Keep window glazing on the conventional raster path. The uncut
        # collision surface retains both storeys, roof penetration and openings.
        nanite.enabled=part in ('HouseShell','Roof','Floors','TimberFrame','Oven')
        nanite.fallback_percent_triangles=1.
        nanite.fallback_relative_error=0.
        options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,
            enable_recompute_tangents=True,replace_materials=True,new_materials=[materials[n] for n in names],
            new_material_slot_names=names,apply_nanite_settings=True,new_nanite_settings=nanite)
        _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
        if outcome!=u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Could not fit '+path)
        if collision:
            body=asset.get_editor_property('body_setup')
            if part.startswith('Casement') or part=='WindowPintles':
                sign=1. if part=='CasementLeft' else -1.
                boxes=[((-2.8,sign*37.15,0),(5.2,72.75,162.))]
                if part=='WindowPintles':
                    boxes=[((-8.,y,z),(17,8,14)) for y in (-74,74) for z in (-51,51)]
                    boxes.append(((-34,0,-77),(10,8.5,16)))
                shapes=[]
                for center,size in boxes:
                    shape=u.KBoxElem()
                    shape.set_editor_property('center',u.Vector(*center))
                    for axis,length in zip(('x','y','z'),size):
                        shape.set_editor_property(axis,length)
                    shapes.append(shape)
                geometry=body.get_editor_property('agg_geom')
                geometry.set_editor_property('box_elems',shapes)
                geometry.set_editor_property('convex_elems',[])
                body.set_editor_property('agg_geom',geometry)
                body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
            else:
                body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        editor.set_metadata_tag(asset,'BakeryArchitectureSource',digest)
        if not editor.save_loaded_asset(asset,False):
            raise RuntimeError('Could not save '+path)
        u.log('BAKERY_ARCHITECTURE_SAVED '+path)
        receipt[part]=dict(mesh=path,triangles=faces,materials={n:SURFACES[n] for n in names})
    if not selected or 'HouseShell' in selected:
        from author_bakery_masonry import publish
        receipt['ExteriorMasonry']=publish()
    Path(os.environ['BAKERY_ARCHITECTURE_RECEIPT']).write_text(json.dumps(receipt,indent=2),encoding='utf8')


main()
