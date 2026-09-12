# Natural weather presentation

Original procedural shader sources for the September 12, 2026 weather upgrade.
No downloaded code, water textures, scanned textures or newly purchased assets.

- `ScreenEdgeRain.hlsl`: sparse static and moving droplets, local refraction,
  viewport/buffer UV conversion, protected screen center, reduced ADS extent.
- `WeaponBeads.hlsl`: UV-anchored water normal/mask for skinned weapon materials.
- `../../Tools/Weather/build_natural_weather.py`: generates the shaders and
  duplicates existing material and Niagara graphs into `/Game/Weather/NaturalV2`.

The generated gun material instances retain the existing weapon texture and
parent-function dependencies. They are derivatives of local licensed project
assets and are not included in public source distribution. Original source
materials and Niagara assets are not saved by this generator. The data asset
`DA_WeatherPresentation` stores hard references for runtime loading and cooking;
the manager's reflected soft reference loads the library at BeginPlay.

Run the generator in an isolated editor commandlet after compiling FPSGAMEEditor.
It only saves generated packages under `/Game/Weather/NaturalV2`. Use
`Tools/Weather/run_natural_weather_audit.ps1` for a real D3D12 rendering check with
an isolated player save; it never closes the user's editor.

Presentation controls: `fps.ScreenRain` (0 disables, default 0.75),
`fps.WeaponWetness` (0 disables, default 1), and the existing weather quality
control. Screen water dries in up to 32 seconds, weapon water in up to 120 seconds
after new exposure stops. Weapon wetness is held per inventory instance during
the session. It does not change gameplay stats or the save schema.
