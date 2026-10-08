import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
r={}
for k in ['r.DiffuseColor.Min','r.DiffuseColor.Max','r.DiffuseColor.Override','r.SpecularColor.Min','r.SpecularColor.Max','r.Roughness.Min','r.Roughness.Max','r.EyeAdaptationQuality','r.UsePreExposure','r.ExposureOffset','r.Substrate']:
    r[k]=u.SystemLibrary.get_console_variable_float_value(k)
r['world_methods']=[x for x in dir(u.World) if any(s in x for s in ['spawn','create','destroy','level'])]
r['editoractor_methods']=[x for x in dir(u.EditorActorSubsystem) if any(s in x for s in ['spawn','world'])]
r['worldfactory_methods']=[x for x in dir(u.WorldFactory) if any(s in x for s in ['world','create'])] if hasattr(u,'WorldFactory') else []
r['captures']=[{'path':c.get_path_name(),'target':c.texture_target.get_path_name() if c.texture_target else None} for c in u.ObjectIterator(u.SceneCaptureComponent2D)]
(P/'render_state.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r))
