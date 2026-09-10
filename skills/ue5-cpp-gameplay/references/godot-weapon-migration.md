# Godot → UE first-person weapon migration

Historical AKM reference. Current FPSGAME weapons follow [UE5 weapon workflow](../../ue5-weapon-workflow/SKILL.md); the durations and offsets below are not current M4 defaults.

Use source runtime state, not only serialized weapon settings. The AKM case is a partial migration in D:/FPS3D/FPSGAME; its fixed offsets are specific to that exported mesh.

## Coordinate and ADS contract

- Godot camera-local (right, up, back) metres converts to UE (forward, right, up) centimetres as (-z, x, y) * 100. Transform rotations as bases/quaternions; do not reuse an Euler-axis mapping without validation.
- Godot vertical FOV 75/55 degrees corresponds to UE horizontal 107.512/85.566 degrees at 16:9. Check actual aspect-axis constraints and another viewport ratio.
- Inspect the exported skeleton for RearSight/FrontSight. A source scene node is not automatically an FBX bone/socket. The AKM report retained WPN_SOCKET_* but omitted both sights.
- Source ADS solves a transform from the current animated sights, aligns front-minus-rear to the camera axis, and places the rear at the configured eye distance (AKM 0.42 m).
- Hip framing compensation is not automatically an ADS pivot correction. In this asset, carrying the hip +19 cm right shift into ADS visibly displaced the sights.
- Fixed source-probed offsets plus a centered screenshot establish one pose only. During fire, validate both sight projections and the actual shot ray; source ADS aims through the displayed front sight.

## Animation and mechanics

- Separate imported clip duration from gameplay action duration. AKM normal/empty source clips are 3.333333/4.291667 s; gameplay reload durations are 2.7/3.466667 s. Set play rate to clip duration / gameplay duration.
- Mechanical events are in source animation time; convert each with event_time * gameplay_duration / source_duration. Settle ammo once at completion.
- Source equip_charge is an idle-to-pose lead of 0.18 s then reload_empty from 1.75 s. Starting that clip at 1.57 s has similar duration but is not the same animation.
- Validate press/hold/release across equipment, reload, sprint, slide, empty magazine and inspect. Direct private-method audit calls bypass input and cannot prove those transitions.

## Feedback and evidence

- Keep kick, jitter, flip, camera kick, trauma, FOV and bloom as separate state. Godot's analytic damped springs remain stable at frame hitches; test 30/60/144 Hz and a hitch.
- Compare load multipliers on every impulse. A matched constant list does not prove the call path matches.
- Camera control rotation can override a component-relative rotation. Measure the final rendered camera and trace direction.
- Source fire audio restarts a player; spawning overlapping voices changes automatic-fire sound. Cue logs and imported assets do not prove audible synchronization.
- Record differences explicitly: fixed versus animated ADS anchor, Perlin versus simplex noise, hitscan versus projectile, missing muzzle effects, equip blend and input boundaries.
- A screenshot sequence ending in COMPLETE proves execution reached the end. Use measured assertions for parity claims.
- Before linking a native DLL, identify the editor holding it and coordinate with other active tasks. Do not repeatedly close another task's editor to win a build race.
