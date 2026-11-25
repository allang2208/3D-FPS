"""Fit the taproom's original scanned panels to the existing openings, carrying their UVs, paint and material slots."""
from dining_walls import (u,materials,source_walls,wall_bays,whole_stones,frame,depth_scale,
                          SOLID,WINDOW,DOOR,KIT,FACADE,ROOMS,OLD_FACADE,OLD_ROOMS,OWNER,GUEST)
from author_shop_house_modules import read,register_slots,clip,save_piece,opening_template
from inn_masonry import cut
from suite_geometry import bedroom_ceiling
from shell_geometry import Mesh

EDIT=u.GeometryScript_MeshEdits
IDENTITY=u.Transform()

def copy_mesh(src):
    dm=u.DynamicMesh()
    EDIT.append_mesh(dm,src,IDENTITY)
    return dm

def append_opening(dm,bay,template):
    xs,zs,cells=template
    a,b,sill,head=bay.opening
    # The native stone reveal stops outside the existing timber frame / moving leaf.
    dx=(bay.left,a-1.5,b+1.5,bay.right)
    dz=(bay.floor,sill if sill==bay.floor else sill-1.5,head+1.5,bay.top)
    for i,j,src in cells:
        if dz[j+1]<=dz[j]:continue
        sx=(dx[i+1]-dx[i])/(xs[i+1]-xs[i])
        sz=(dz[j+1]-dz[j])/(zs[j+1]-zs[j])
        ox=dx[i]-xs[i]*sx
        oz=dz[j]-zs[j]*sz
        part=src
        cuts=[]
        if i!=1 and sx<1.25:
            # Cut the remote edge of tight bays, keeping the dressed jamb stones at their natural size.
            sx=1.25
            edge=1 if i==0 else 2
            ox=dx[edge]-xs[edge]*sx
            cuts.append((0,(dx[0 if i==0 else 3]-ox)/sx,-1 if i==0 else 1))
        if j==2 and sz<1:
            sz=1
            oz=dz[2]-zs[2]
            cuts.append((2,dz[3]-oz,1))
        if cuts:
            part=copy_mesh(src)
            for axis,at,direction in cuts:clip(part,axis,at,direction)
        t=u.Transform(location=(ox,0,oz),scale=(sx,depth_scale(bay),sz))
        EDIT.append_mesh(dm,part,u.MathLibrary.compose_transforms(t,frame(bay)))

def append_short_solid(dm,bay,solid):
    # Use the central slice of a real stone course for infill shorter than one bay.
    width=bay.right-bay.left
    count=max(1,round(width/410))
    step=width/count
    for i in range(count):
        part=copy_mesh(solid)
        fit=max(1.36,step/300.)
        half=step/(2*fit)
        clip(part,0,-half-.25,-1)
        clip(part,0,half+.25,1)
        t=u.Transform(location=(bay.left+(i+.5)*step,0,(bay.floor+bay.top)*.5),
                      scale=(fit,depth_scale(bay),(bay.top-bay.floor)/300))
        EDIT.append_mesh(dm,part,u.MathLibrary.compose_transforms(t,frame(bay)))

def ceiling(materials_out):
    old=u.load_asset(OLD_ROOMS)
    finishes={str(s.material_slot_name):s.material_interface for s in old.static_materials}
    model=Mesh()
    bedroom_ceiling(model)
    dm=u.DynamicMesh()
    for name,(verts,normals,uv,triangles) in model.slots.items():
        mat=finishes[name]
        if mat not in materials_out:materials_out.append(mat)
        buf=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*v) for v in verts],normals=[u.Vector(*v) for v in normals],
              uv0=[u.Vector2D(*v) for v in uv],triangles=[u.IntVector(*v) for v in triangles])
        EDIT.append_buffers_to_mesh(dm,buf,material_id=materials_out.index(mat))
    return dm

def author(site):
    donors=source_walls(site)
    walls=list(wall_bays())
    result={}
    for exterior,old,path in [(True,OLD_FACADE,FACADE),(False,OLD_ROOMS,ROOMS)]:
        palette=[]
        if exterior:
            dm,old_slots=read(old)
            clip(dm,2,GUEST,1)
            register_slots(dm,old_slots,palette)
        else:
            dm=ceiling(palette)
        solid,_=read(KIT+SOLID)
        register_slots(solid,materials(donors[SOLID]),palette)
        door=not exterior
        template=opening_template(door,palette,materials(donors[DOOR if door else WINDOW]))
        for bay in walls:
            if bay.outside!=exterior or whole_stones(bay):continue
            section=u.DynamicMesh() if bay.slope else dm
            if bay.opening:append_opening(section,bay,template)
            else:append_short_solid(section,bay,solid)
            if bay.slope:
                # The two garden-side wall ends follow the existing lean-to roof.
                cut(section,(0,423,969),(0,97./405.,1))
                EDIT.append_mesh(dm,section,IDENTITY)
        result[path]=save_piece(path,dm,palette,old)
    return result
