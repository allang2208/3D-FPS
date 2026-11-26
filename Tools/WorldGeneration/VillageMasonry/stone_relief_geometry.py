"""Bake local triplanar scan relief into village-only copies of the stonework."""
import gc
import json
import os
from pathlib import Path
import sys

import unreal as u

sys.path.append(os.environ['STONE_RELIEF_NUMPY'])
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image
from stone_reference import read_mesh, require

HILLS='/Game/WorldGeneration/TemperateHills/'
MASONRY=HILLS+'VillageMasonry/'
BAKERY=HILLS+'VillageBakery/Architecture/SM_Bakery_AbandonedHouseMasonry'
DEST=MASONRY+'ReliefMeshes/'
MATERIALS=('MI_Main_StoneWall_00A','MI_Main_StoneWall_00B_Gray','MI_StoneWall_Pieces_00A')
RUN=Path(os.environ['STONE_RELIEF_GEOMETRY_WORK'])
LIB=u.MaterialEditingLibrary
LIST=u.GeometryScript_List
QUERY=u.GeometryScript_MeshQueries
ED=u.EditorAssetLibrary


def scan_parameters():
    result={}
    for name in MATERIALS:
        m=require('/Game/UnrealNormandy/MaterialInstances/'+name)
        scales={str(k):LIB.get_material_instance_scalar_parameter_value(m,k) for k in LIB.get_scalar_parameter_names(m) if 'TileSize' in str(k)}
        textures={}
        for k in LIB.get_texture_parameter_names(m):
            texture=LIB.get_material_instance_texture_parameter_value(m,k)
            if texture and ('StoneSurface_' in texture.get_name() or 'BaseColor' in str(k) or 'Albedo' in str(k)):
                textures[str(k)]=texture.get_name()
        result[name]=dict(scales=scales,textures=textures)
    return result


def buffers(mesh):
    _,verts,_=QUERY.get_all_vertex_positions(mesh,False)
    _,faces,_=QUERY.get_all_triangle_indices(mesh,False)
    _,sections,_=u.GeometryScript_Materials.get_all_triangle_material_i_ds(mesh)
    p=np.array([(v.x,v.y,v.z) for v in LIST.convert_vector_list_to_array(verts)],dtype=np.float64)
    t=np.array([(v.x,v.y,v.z) for v in LIST.convert_triangle_list_to_array(faces)],dtype=np.int32)
    ids=np.asarray(list(LIST.convert_index_list_to_array(sections)),dtype=np.int32)
    return p,t,ids


def main():
    scan=scan_parameters()
    (RUN/'parameters.json').write_text(json.dumps(scan,indent=2),encoding='utf8')
    if os.environ.get('STONE_RELIEF_GEOMETRY_SURVEY')=='1':
        examples=[]
        for path in [MASONRY+'SM_VillageWallRepairedA',MASONRY+'SM_HighPortalGalleryEast',BAKERY]:
            obj=require(path);dm=read_mesh(obj)
            p,t,ids=buffers(dm)
            examples.append(dict(source=path,vertices=len(p),faces=len(t),ids=list(map(int,np.unique(ids))),bounds=[p.min(0).tolist(),p.max(0).tolist()]))
        (RUN/'saved.json').write_text(json.dumps(examples,indent=2),encoding='utf8')
        return
    from stone_relief_geometry_bake import bake
    bake(scan)


if __name__=='__main__':
    main()
