# Staff release anatomy — 2026-10-01

Revision `2026100101` contains four grips and six complete local-pose rows: Idle, Raised, Windup, Release, Follow, Run. Idle and Run are retained from the prior cast table. The complete Raised right chain is the charge-flow `RaisedSettled` revision `2026100102` endpoint, with no additional camera offset.

The three release control contacts include the runtime presentation offsets exactly once: Windup `(47,27,-7)`, Release `(55,21,-12)`, Follow `(53,19,-16)` camera cm. Hand-in-grip, fingers and native bindings are retained.

The native arm lengths are retained. The shoulder remains `(-9,16,-14)` for Windup and moves to `(0,16,-14)` for Release, then `(-1,16,-14)` for Follow. This makes the preserved target contact reachable with roughly 47–55 degrees of flexion instead of stretching or reversing the elbow.

The accepted carry wrist seeds each elbow circle. The horizontal release shaft exposes an anatomical branch ambiguity: using that seed without resolving the native hinge plane gives an upper-arm change of about 125 degrees and a wrist change of about 139 degrees. The author resolves swivel on that same native elbow circle by minimizing actual wrist change and upper-arm change from the previous control together. There is no fixed camera pole. The resulting upper-arm changes between controls are about 4–9 degrees; native-helper local transforms remain intact, and forearm pronation is limited to 45 degrees.

`authored-parameters.json` records the resulting shoulders, elbows, wrists, flexion, pronation and orientation changes. These are authoring parameters, not gameplay validation results.

`Staff_ReleaseAnatomy20261001.blend` is actually saved by background Blender. Its four `A_Staff_ReleaseAnatomy20261001_*` actions cover `.28` seconds of release, `.10` seconds of hold and `.42` seconds of recovery at 120 Hz. Complete local transform weights match runtime; lower-arm flexion and pronation are interpolated as scalars, with carry/run entry blended once. The staff grip follows whole-arm FK and inverse hand-in-grip.

No UE package import is necessary for this C++ pose-table path. No UE launch, render, PIE or gameplay test was performed by this authoring step.
