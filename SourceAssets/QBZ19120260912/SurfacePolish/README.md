# QBZ-191 surface polish — 2026-09-12

Source: ../QBZ191_Editable.blend, original supplied OBJ and 4K maps; original provenance applies.

- Sharp edges over 38 degrees retain split shading. Four-segment, overlap-clamped bevels: 0.15 mm on iron sights and 0.25 mm on the body. Weighted normals stabilize broad machined faces.
- Sight aperture and post positions, skeleton, skin weights and existing animation assets are retained. This is edge/surface refinement, not a replacement high-poly source model.
- FBX carries face smoothing and custom normals; Unreal imports normals and computes MikkTSpace tangents.
- Separate body, magazine and iron-sight materials retain original base colour/metal masks. Roughness uses clamp(source * 0.8 + 0.06, 0.28, 0.78); sights have a 0.38 minimum. Normal detail strength is 0.85 on the gun, 0.65 on the sights.
- build.py writes the editable blend and mesh FBX here. import.py updates the existing /Game/Weapons/QBZ191/Calibrated/SK_QBZ191_Manny runtime mesh and assigns new /Game/Weapons/QBZ191/SurfacePolish materials. Existing seven animations remain in use.

No gameplay test, screenshot or rendered acceptance was performed, per user instruction. User visual/gameplay acceptance remains pending.
