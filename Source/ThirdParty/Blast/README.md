# NVIDIA Blast stress kernel

Source: https://github.com/NVIDIA-Omniverse/PhysX/tree/4f2103c3a9052906296defb12166753450ef787c/blast

Version: Blast 5.0.6, pinned at revision above. Original files and SHA-256 values are recorded in upstream.json. Upstream source is retained unmodified.

FPSGAME compiles the internal six degree-of-freedom StressProcessor and its own plain C ABI adapter. It does not embed PhysX rigid-body simulation, the UE4 Blast plugin, authoring tools, or ExtStressSolver's family-wide material thresholds. UE Chaos remains responsible for rigid bodies and contact collision. This internal API is deliberately isolated and pinned.

Build on Windows with Visual Studio C++ tools installed:

```powershell
python Tools/Building/build_blast.py
```

The script restores the selected source files if their manifest is absent and builds Lib/Win64/FPSBlast.lib. The generated library stays local; the adapter, pinned source, licenses and build script are published. No tests are invoked. No NVIDIA GPU is required; the kernel selects supported CPU SIMD instructions or its scalar path.

BSD-3-Clause distribution terms are in SDK/LICENSE.md and the original source headers. The build stages the license and notices with packaged binaries.
