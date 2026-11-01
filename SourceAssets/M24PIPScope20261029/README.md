# M24 independent optical scene

The factory M24 main 6x optic now captures the aimed scene into a circular render target. The main camera retains normal ADS framing and remains visible around the eyepiece. The old opaque outer mask and full-screen lens post-process are disabled for this optic. Upper 1x sight, wheel transitions, other scope implementations, HUD layering and existing recoil/shot direction remain on their existing paths.

`UI/M24ScopeScene.inl` is included by `LPVOScopeWidget.cpp`. It updates after the world's actor/camera ticks, using the firing camera transform. For aperture radius R, main-view focal length F and displayed power P, capture horizontal FOV is `2 atan(R / (F P))`. This compensates for the smaller lens image instead of magnifying the entire viewport. Mil spacing uses the capture projection.

The capture runs only during local first-person M24 main-scope ADS. It stops on exit, upper-sight switching and UI/third-person modes; switching away from the factory optic or destroying the widget releases resources. The owning pawn is excluded from the capture. The opaque LDR scene is drawn with texture alpha ignored and a feathered vertex-alpha edge.

Default capture resolution: 1024 square. `fps.M24.ScopeResolution` is clamped to 512..1536. This adds an extra scene render while using the main scope; performance has not been measured. No persistent Content asset is needed; the component and render target are created at runtime.

Build with `build_editor.ps1`: existing UE batch mutex, full UBT dependency graph, standard Editor DLL names, no editor/game launch. A successful build writes `build-receipt.json`. `-CompileOnly` produces isolated object files while the editor remains open; it does not link or publish and does not replace the required full build. Runtime appearance, scope transitions and performance are left for the user to test.
