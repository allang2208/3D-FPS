"""Hunt/work short-glove thickness stamps. Offsets are centimetres."""
import numpy as np

FINGERS = ("index", "middle", "ring", "pinky")
CONTACT_CM = 0.015
BACK_CM = 0.320
CUFF_LIP_CM = 0.450
CUFF_GROOVE_CM = 0.060
STRAP_CM = 0.240
KNUCKLE_CM = 0.550
PLATE_CM = 0.160
THUMB_CM = 0.280
FINGER_BACK_CM = 0.140
THICKNESS_CAP_CM = 0.900


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def smooth(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def stamp_weights(weights):
    n = len(weights)
    knuckle = np.zeros(n)
    plate = np.zeros(n)
    thumb = np.zeros(n)
    finger_back = np.zeros(n)
    for i, w in enumerate(weights):
        k = 0.0
        p = 0.0
        t = 0.0
        fb = 0.0
        for side in ("l", "r"):
            hand = float(w.get("hand_" + side, 0.0))
            for finger in FINGERS:
                meta = float(w.get(finger + "_metacarpal_" + side, 0.0))
                w01 = float(w.get(finger + "_01_" + side, 0.0))
                w02 = float(w.get(finger + "_02_" + side, 0.0))
                joint = 4.0 * meta * w01 if meta > 1e-6 else 4.0 * hand * w01
                joint *= max(0.0, 1.0 - w02)
                if joint > k:
                    k = joint
                p += meta if meta > 1e-6 else hand * 0.45
                fb += w01 * max(0.0, 1.0 - w02)
            t01 = float(w.get("thumb_01_" + side, 0.0))
            t02 = float(w.get("thumb_02_" + side, 0.0))
            t += t01 * max(0.0, 1.0 - t02)
        knuckle[i] = k
        plate[i] = p
        thumb[i] = t
        finger_back[i] = fb
    return knuckle, plate, thumb, finger_back


def hunt_thickness(normals, dorsal, edge_distance, weights):
    back = smooth(-0.12, 0.55, (normals * dorsal).sum(1))
    thickness = CONTACT_CM + (BACK_CM - CONTACT_CM) * back
    thickness *= smooth(0, 0.70, edge_distance)
    thickness += CUFF_LIP_CM * np.exp(-((edge_distance - 0.34) / 0.16) ** 2) * smooth(0, 0.22, edge_distance)
    thickness -= CUFF_GROOVE_CM * np.exp(-((edge_distance - 0.62) / 0.07) ** 2) * smooth(0.14, 0.30, edge_distance)
    thickness += STRAP_CM * np.exp(-((edge_distance - 1.10) / 0.12) ** 2) * smooth(0.70, 0.95, edge_distance) * back
    knuckle, plate, thumb, finger_back = stamp_weights(weights)
    pad = smooth(0.26, 0.54, knuckle) ** 2.4
    thickness += KNUCKLE_CM * pad * back
    thickness += PLATE_CM * smooth(0.22, 0.55, plate) * back * smooth(0.80, 1.40, edge_distance)
    thickness += THUMB_CM * smooth(0.28, 0.58, thumb) * back
    shaft = smooth(0.30, 0.65, finger_back) * (1.0 - pad)
    thickness += FINGER_BACK_CM * shaft * back
    return np.minimum(np.maximum(thickness, 0), THICKNESS_CAP_CM)
