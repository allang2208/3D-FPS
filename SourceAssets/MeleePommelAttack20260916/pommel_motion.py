"""Fourth normal attack: drive the counterweight (柄尾配重) forward.

Reference: user-specified BV1hCJFzQEyR, 1:40-1:41 ("#6 柄捅"), read 2026-09-16.
The demo turns the sword over so the butt leads, then jabs it forward at chest
height. Two adaptations are deliberate, not observations:

* The demo lets most of the blade sweep through the middle of the screen. Here
  the blade turns over *above and behind* the shoulder (the accepted heavy-cut
  style keeps the blade out of the aiming area), and the hilt stays on the right
  so the counterweight reads in the lower-right.
* The counterweight only reaches about one pommel-length past the hands, so the
  drive stays short of a thrust (the thrust moves the guard 37 cm). It still
  spends 0.29 m of counterweight travel by cocking the butt down near the hip and
  swinging it up into the target, rather than translating the hilt alone.

Ergonomics used to pick the path:
* Both hands keep the accepted hilt contacts. The left hand sits 17.2 cm and the
  right hand 7.3 cm behind the guard, so the left wrist is the limiting joint;
  every pose keeps it inside the two-bone reach of its shoulder rather than
  sliding the shoulder out of the body.
* The turn-over is a shaft rotation, not a wrist flick: the grasp roll and the
  elbow planes are solved along the whole path, and the blade stays outside the
  camera near plane (sweeping up on the right of the head).
* Frame 0 and the last frame are the accepted default idle pose, so the clip is
  entered from idle and leaves it again without a pose jump.
"""
import math

from mathutils import Matrix, Vector

from diagonal_motion import IDLE_FACE, READY, arc_frame, blend_pair, smooth

FPS = 480
# Timing is deliberately not uniform (accepted melee rhythm: load slowly, spend
# the strike fast, arrest, then let the weight draw back):
#   turnover  0.40 s  slow rise and turn-over, zero speed at both ends
#   draw      0.18 s  hilt drawn back to the chest, butt aimed forward
#   raise     0.14 s  the arm lifts the hilt up (the charge beat the user asked for)
#   aim hold  0.12 s  held, no drift, so the next thing read is the strike
#   strike    0.08 s  counterweight spends 0.26 m; fast start, hard landing
#   arrest    0.06 s  short stop, no extra damage
#   withdraw  0.32 s  decisive start, decelerating pull-back
#   settle    0.30 s  ease into the default idle
TURN_END = 0.40
DRAW_END = 0.58
RAISE_END = 0.72
CONTACT_START = 0.84
EXTENSION_END = 0.92
CONTACT_END = 0.92
ARREST_END = 0.98
RETURN_CORNER = 1.30
ATTACK_END = 1.60
BUTT_M = 0.27         # counterweight face behind the guard, rune sword mesh

IDLE = (READY, READY @ IDLE_FACE)

_idle_grip, _idle_blade = arc_frame(1, 0, (0, 0, 0))
BLADE_ROLL = _idle_grip.inverted() @ _idle_blade   # hilt channel vs blade channel


def shaft(blade_direction, position, roll_deg, face_deg=0.0):
    """Hilt frame with local +Z on the blade, built exactly like the arc frames.

    ``roll_deg`` sets the hilt channel the hands are placed against; ``face_deg``
    rolls only the sword mesh about its own axis, which is how the blade is shown
    edge-on instead of presenting its wide face to the camera.
    """
    z = Vector(blade_direction).normalized()
    yaw = math.atan2(-z.x, z.y)
    tilt = -math.acos(max(-1.0, min(1.0, z.z)))
    grip = (Matrix.Translation(Vector(position)) @ Matrix.Rotation(yaw, 4, 'Z')
            @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Rotation(math.radians(roll_deg), 4, 'Z'))
    return grip, grip @ Matrix.Rotation(math.radians(face_deg), 4, 'Z') @ BLADE_ROLL


def butt_frame(position, roll_deg, butt_direction, face_deg=0.0):
    """Pose authored by the striking end: local -Z is the counterweight direction."""
    return shaft(-Vector(butt_direction), position, roll_deg, face_deg)


# The butt turns from down-and-back (idle) through straight down to forward-right;
# the blade mirrors it from up-forward through vertical to back-left over the shoulder.
# face_deg stays 0 on all four: the sword keeps the accepted arc-frame roll, which
# showed the blade thinner in the review renders than an extra 90-degree roll did.
# This is the first delivered version's pose family, kept deliberately: the butt
# turns to face forward at chest height and the blade rides up and back over the
# left shoulder. Only the stroke is enlarged (draw further back, drive further
# forward, and let the butt rotate a little more on the way out), so the read
# stays the accepted one instead of becoming a raised-hammer smash.
TURNED = butt_frame((.21, .36, -.05), 58, (-.06, .24, -.97))
DRAWN = butt_frame((.21, .22, -.03), 66, (.18, .84, -.51))    # first version's butt angle, drawn in
RAISED = butt_frame((.20, .20, .06), 66, (.18, .84, -.51))    # same aim, hilt lifted 9 cm
EXTENDED = butt_frame((.14, .40, -.10), 68, (.17, .95, -.28))
CORNER = butt_frame((.19, .30, -.07), 62, (-.06, .06, -.99))


def snap(u):
    """Fast start, hard landing: the strike curve, not a symmetric ease."""
    return 1.0 - (1.0 - u) ** 2.2


def poses(t):
    if t < TURN_END:
        return blend_pair(IDLE, TURNED, smooth(t / TURN_END))
    if t < DRAW_END:
        return blend_pair(TURNED, DRAWN, smooth((t - TURN_END) / (DRAW_END - TURN_END)))
    if t < RAISE_END:
        return blend_pair(DRAWN, RAISED, smooth((t - DRAW_END) / (RAISE_END - DRAW_END)))
    if t <= CONTACT_START:
        return RAISED
    if t < EXTENSION_END:
        return blend_pair(RAISED, EXTENDED, snap((t - CONTACT_START) / (EXTENSION_END - CONTACT_START)))
    if t <= ARREST_END:
        return EXTENDED
    if t < RETURN_CORNER:
        # Start the withdrawal decisively and decelerate before turning upright.
        u = (t - ARREST_END) / (RETURN_CORNER - ARREST_END)
        return blend_pair(EXTENDED, CORNER, 1 - (1 - u) ** 3)
    return blend_pair(CORNER, IDLE, smooth((t - RETURN_CORNER) / (ATTACK_END - RETURN_CORNER)))


def counterweight(pose, metres=BUTT_M):
    """Counterweight face in author space for a weapon pose."""
    blade = pose
    return blade @ Vector((0, 0, -metres))
