import unreal as u
print("STATICMESH_LIB:", [x for x in dir(u.EditorStaticMeshLibrary) if "tri" in x.lower() or "vert" in x.lower() or "bound" in x.lower()])
print("SM:", [x for x in dir(u.StaticMesh) if "bound" in x.lower() or "tri" in x.lower()])
