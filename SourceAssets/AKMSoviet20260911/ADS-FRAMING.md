# AKM camera framing and sight calibration

AKM SovietFab hip framing moves the complete hands/weapon assembly +6 cm along camera forward relative to the M4 hip baseline: (6,7,-7) cm instead of (0,7,-7). ADS remains independently calibrated, without adding the hip offset to its pose. Existing hands and animation assets are unchanged.

The prior SourceMatched front-sight bone was 6.644 mm above and 22.529 mm behind the actual new mesh front-sight tip in WPN_root space. The previous firing path used that old marker. Source geometry measurements are retained in sight_landmarks.json; probe_ue_sights.py verified the FBX local Y reflection and inherited 100x scale. AKMSovietCalibration.h supplies measured front tip, rear notch at blade-top height, and muzzle bore position to the camera calibration, shot direction and effective muzzle location. Only SovietFab matches this calibration.

Build ads-build-v2.log succeeded. The isolated run runtime-akm-soviet-ads-v2.log completed with failures=0. The audit fired real projectiles against temporary targets at 5, 25 and 100 metres, checked damage and recorded the actual collision point. Perpendicular impact errors from the visible front-sight ray were 0.021335, 0.003758 and 0.000919 cm (all below 0.3 mm). Front and rear projected within 0.003 pixels of the 960x540 image centre in the stationary ADS samples. This checks the current straight, zero-gravity projectile implementation; recoil still moves the sight and shot direction during firing.

The first audit used an insufficient fixed 0.5-second wait for the 100 m projectile. It was corrected to range/projectile speed +0.3 seconds before the passing rerun; gameplay projectile speed was not changed. Normal/empty reload, M4 switch/back, inventory, warehouse and save regression also passed in the rerun.

framing_comparison.png compares the actual M4 equip-end reference frame, previous AKM, and current AKM. compare_framing.py selects the penultimate M4 frame because the final stage-7 screenshot captures the subsequent AKM switch in the same tick. Images show distinct captures, not a controlled performance benchmark.
