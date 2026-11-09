# M249 Feedback31 scoped review — 2026-11-09

Conclusion: retain the saved Feedback31 receiver-motion layer. No new action, timing, wrist twist, contact slip or idle-handoff defect was found in this offline review. No production assets or gameplay code were changed by Review32.

## Coverage

- Fresh file hashes match all five saved Feedback31 profiles, both side-reload base sequences, both box-reload base sequences and the current M249 skeletal mesh (`input_hashes.json`).
- `full/receipt.json`: 20 native animation-graph cases, comprising 30/45-round magazines, normal/empty reloads and base/vertical/canted/prism/angled grips. The graph, mounted parts, camera feedback and arm correctives were evaluated at 60 Hz through the complete action and 0.3 seconds of idle. 5,965 pose frames and 758 engine images were written.
- `audit.json`: finite transforms for all cases; receiver motion remains continuous. Maximum receiver displacement per 60 Hz frame is under 0.40 cm and rotation under 0.63 degrees. The action-to-idle boundary is below 0.01 cm and 0.01 degrees. These are measured results for these captures, not generic animation acceptance thresholds.
- Twelve cases have matching Insert30 full-clip captures: their playback clocks remain identical and both hands, elbows, magazine socket and charging-handle transforms relative to the receiver remain unchanged within floating-point precision. The other eight cases additionally cover 30-round magazines with all four aftermarket grip families.
- Player-view stage sheets were inspected for normal/empty factory reloads and insertion/recovery across all five grip families. Additional neutral-material views of actual engine-skinned surfaces were inspected at approach, insertion, recovery and charging stages for the 45-round canted-grip case.

## Findings

The receiver now transfers weight while the magazine is removed, retrieved, docked and seated, and reacts during the empty-reload charging sequence. The prior retrieval pause, 30/45 timing difference, original finger/arm action and compact return remain intact. The root layer is zero before the existing arm-to-idle handoff, so it introduces no second return or residual roll.

The near-camera geometry probe reports some arm vertices within 10 cm during early approach/retrieval (nearest candidate depth 7.30 cm). This is a proximity flag, not a penetration test or an occlusion-aware pixel result. The corresponding player and surface renders were inspected; no visible near-plane cut or new arm expansion was found. Insertion/recovery samples retain the prior clearance improvement. No claim of zero penetration over every mesh triangle is made from bone-relative equality alone.

All work ran in background commandlets and Blender. No editor GUI, PIE, gameplay session, multiplayer session or audio listening test was started. The conclusion covers the current receiver-feedback change and its neighboring animation states; live gameplay feel remains separate from this offline assessment.

Production inputs and all existing animation timings were left unchanged. `run.ps1` is a read-only review launcher; do not reuse prior full-profile import scripts to restore assets.
