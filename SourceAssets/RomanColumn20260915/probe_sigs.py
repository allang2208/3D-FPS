import unreal
SV = unreal.ModelingService
for name in ("append_sweep_polyline", "rotate_mesh", "append_mesh", "append_sphere", "append_loft", "flare"):
    fn = getattr(SV, name, None)
    doc = (fn.__doc__ or "").split("\n")[0] if fn else "MISSING"
    print("[sig] %-22s %s" % (name, doc.strip()))
