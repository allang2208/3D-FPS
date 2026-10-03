# Food grasp revision

Ordinary bread and baguette have separate V7 native hand contact profiles in
`grip_profiles.json`. `author_grips.py` authors the bounded four-finger wrap and
opposing thumb against their saved Quixel meshes and the accepted V7 skin.
`publish_food_motion.py` writes only these food families into the runtime JSON.
Both existing food catalog scripts publish the same authored profiles.

The lift and lowering use the single left-hand drinking-action convention.
`natural_food_motion.py` is the common source for food timing and movement.
Ordinary bread lasts 2.4 seconds and baguette lasts 2.7 seconds, with contact
settlement at 1.86 and 2.12 seconds respectively. Uneven key times and spacing
use the existing cubic-Hermite position interpolation and eased rotations:
slow take-up, faster lift, gradual deceleration toward the mouth, and one
smooth withdrawal. Millimeter-scale, unequal lateral/vertical offsets and
small wrist-angle variations occur during the approach only. No shake loop,
per-frame random noise, or repeated backward/forward eating strokes are used.
The grasp remains active during visible withdrawal; pose recovery starts once
the prop releases. The catalog duration and old-instance duration migration
use these same authored times.

The authored object contact is near the short loaf's middle/lower region
(5.5 cm from its bottom) and the baguette's middle (15 cm). Publication converts
that contact into the existing bounds-center prop frame by offsetting the grip
track and palm relation together. This preserves the authored physical grasp
without changing the native drinking/food implementation or its class layout.
The held mesh follows the actual solved palm in the same frame as drinking.
Native bones, scales, weights and shared hand meshes are unchanged.

This revision updates authoring sources and runtime JSON only. The existing
binaries read the food families at BeginPlay; restart the play session to load
the new timing. No native build or asset import is needed for this revision.
No gameplay tests, editor UI, acceptance renders or screenshots were run.
