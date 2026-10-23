"""Backpack-specific response. Keep garment fits, fixed harness zones and mesh topology."""
PROFILES = {
    'ue_portable_backpack': dict(frequency_hz=3.3, damping=.86, max_angle_degrees=2.5,
                                max_bounce_cm=.36, response_scale=2.3, max_displacement_cm=2.2),
    'ue_mountain_backpack': dict(frequency_hz=3.0, damping=.82, max_angle_degrees=3.0,
                               max_bounce_cm=.45, response_scale=2.6, max_displacement_cm=2.5),
    'ue_expedition_backpack': dict(frequency_hz=2.6, damping=.98, max_angle_degrees=1.8,
                                 max_bounce_cm=.24, response_scale=1.9, max_displacement_cm=1.8),
}

if __name__ == '__main__':
    import json
    from pathlib import Path
    root = Path('D:/FPS3D/FPSGAME/SourceAssets/BackpackMotion20261022')
    (root/'response_profiles_r2.json').write_text(json.dumps(PROFILES, indent=2), encoding='utf-8')
