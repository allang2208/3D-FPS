import unreal as u
lib = [x for x in dir(u.EditorStaticMeshLibrary) if not x.startswith('_')]
print("LIB_ALL:", lib)
print("SM_BOUND:", [x for x in dir(u.StaticMesh) if not x.startswith('_') and ("ound" in x or "imension" in x)])
