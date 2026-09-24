import unreal
print("FACS",[x for x in dir(unreal) if "Factory" in x and not x.startswith("_")][:40])
print("MI",[x for x in dir(unreal.MaterialInstance) if not x.startswith("_") and ("param" in x.lower() or "method" in x.lower())][:20])
print("LIBS",[x for x in dir(unreal) if "MaterialInstance" in x])
