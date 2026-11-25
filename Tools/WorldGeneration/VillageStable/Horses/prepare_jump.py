"""Bake the Quaternius jumping horse onto the Warhorse bind skeleton, in place."""
import numpy as np
from scipy.spatial.transform import Rotation as Rot

from prepare_horse import Horse, SOURCE


def bake():
    donor = Horse((SOURCE / "Originals/QuaterniusHorse.glb").read_bytes())
    horse = Horse((SOURCE / "Originals/WarhorseLite.glb").read_bytes())
    # Original sample 6 already has the hind limbs moving into support. Use the
    # recovery to idle so a stationary jump also has a four-footed finish.
    count = 46
    times = np.arange(count) / 30.
    _, motion = donor.sample(donor.clips["Jump_toIdle"], (np.arange(count)+6)/51.)
    _, idle = horse.sample(horse.clips["idle_loop"], np.zeros(count))
    correspondence = {
        "pelvis":"Back", "spine_01":"Torso", "spine_02":"Torso2", "spine_03":"Torso3",
        "neck_01":"Neck1", "neck_02":"Neck2", "neck_03":"Neck3", "head":"Head",
        "tail_01":"Tail2", "tail_02":"Tail3", "tail_03":"Tail4", "tail_04":"Tail5", "tail_05":"Tail7",
    }
    for s in "LR":
        for target, source in [("scapula","FrontShoulder"),("upperarm","FrontShoulder"),
                ("forearm","FrontUpperLeg"),("hand","FrontLowerLeg"),("finger","FF"),
                ("thigh","BackLeg"),("calf","BackUpperLeg"),("foot","BackLowerLeg"),("toe","FFB"),
                ("ear","Ear3")]:
            correspondence[target+"_"+s] = source+"."+s
    tracks = {}
    for name, source in correspondence.items():
        t, d = horse.index[name], donor.index[source]
        # Use bind-world changes of direction. The two skeletons have different
        # parent counts and local bone rolls, including the IK-driven donor feet.
        world = donor.world_rot(d,motion,count)*donor.world_rot(d,{},1).inv()*horse.world_rot(t,{},1)
        local = horse.world_rot(horse.parent[t],tracks,count).inv()*world
        tracks[t,"rotation"] = local.as_quat()
    # Ease the outside ends into the native standing pose. Source samples 15,
    # 24 and 36 (export frames 9, 18 and 30) mark push-off, apex and contact.
    w = np.minimum(np.clip(np.arange(count)/4.,0,1),np.clip((count-1-np.arange(count))/7.,0,1))
    w = w*w*(3-2*w)
    for (node, key), values in list(tracks.items()):
        base = Rot.from_quat(horse.local(node,key,idle,count))
        tracks[node,key] = (base * Rot.from_rotvec((base.inv()*Rot.from_quat(values)).as_rotvec()*w[:,None])).as_quat()
    # Match the supporting shoe to the ground. In flight the capsule supplies
    # the ballistic arc; only blend the relative pelvis offset between contacts.
    soles = []
    rest = {(n,"translation"):horse.local(n,"translation",{},1).copy() for n in range(len(horse.nodes))}
    for n in range(len(horse.nodes)):
        tracks[n,"translation"] = horse.local(n,"translation",{},count).copy()
    for name in ("finger_L","finger_R","toe_L","toe_R"):
        node = horse.index[name]
        sole_in_bind = horse.world_rot(node,{},1).inv().apply([0,-horse.world_pos(node,rest,1)[0,1],0])
        soles.append((horse.world_pos(node,tracks,count)+horse.world_rot(node,tracks,count).apply(sole_in_bind))[:,1])
    height = -np.min(soles,axis=0)
    mix = np.linspace(0.,1.,22)
    height[9:31] = height[9]+(height[30]-height[9])*mix*mix*(3-2*mix)
    pelvis = horse.index["pelvis"]
    base = horse.local(pelvis,"translation",{},count).copy()
    offset = np.zeros_like(base)
    offset[:,1] = height
    tracks[pelvis,"translation"] = base + horse.world_rot(horse.parent[pelvis],{},1).inv().apply(offset)
    # The FBX needs only animated joints; do not export constant node/object tracks.
    tracks = {k:v for k,v in tracks.items() if k[1]=="rotation" or k==(pelvis,"translation")}
    horse.doc["animations"] = []
    horse.save_clip("HurdleJump",times,tracks)
    out = SOURCE.parent / "JumpR13"
    out.mkdir(exist_ok=True)
    horse.write(out/"Warhorse_Jump.glb")


if __name__ == "__main__":
    bake()
