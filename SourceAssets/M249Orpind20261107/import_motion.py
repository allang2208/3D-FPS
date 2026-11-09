"""Write fitted tracks over the donor's retained finger, helper and motion curves."""
from pathlib import Path
import gzip,json
import unreal as u

ROOT=Path(__file__).resolve().parent
DEST="/Game/Weapons/M249/Animations"
E=u.EditorAssetLibrary
mesh=E.load_asset("/Game/Weapons/M249/SK_M249_V7")
receipt=ROOT/"actions_saved.json"
saved=json.loads(receipt.read_text()) if receipt.exists() else {}
for f in sorted((ROOT/"Motion").glob("*.json.gz")):
    role=f.name.split(".")[0]
    if globals().get("only_roles") and role not in only_roles:continue
    with gzip.open(f,"rt",encoding="utf8") as inp:data=json.load(inp)
    name="A_M249_"+role
    path=DEST+"/"+name
    clip=u.load_asset(path) or E.duplicate_asset(data["source"],path)
    if not clip or not u.WeaponAnimationAuthoring.rebind_native_animation(clip,mesh.skeleton):raise RuntimeError(path)
    clip.set_preview_skeletal_mesh(mesh)
    ctl=clip.get_editor_property("controller")
    ctl.open_bracket("Fit M249 native contacts",False)
    try:
        if 'fps' in data:
            ctl.set_frame_rate(u.FrameRate(numerator=int(data['fps']),denominator=1),False)
            ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
        for bone,rows in data["tracks"].items():
            if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in rows],[u.Quat(*t[3:7]) for t in rows],[u.Vector(*t[7:]) for t in rows],False):
                ctl.add_bone_curve(bone,False)
                if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in rows],[u.Quat(*t[3:7]) for t in rows],[u.Vector(*t[7:]) for t in rows],False):raise RuntimeError(role+"/"+bone)
    finally:ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not E.save_loaded_asset(clip,False):raise RuntimeError(path)
    saved[role]={"asset":clip.get_path_name(),"duration":clip.get_play_length()}
    (ROOT/"actions_saved.json").write_text(json.dumps(saved,indent=2),encoding="utf8")
    print("M249_ACTION_SAVED",role,flush=True)
