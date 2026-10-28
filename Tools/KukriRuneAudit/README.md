# Kukri completion audit

Run only for an explicitly requested audit. `run.ps1` acquires the shared UE MCP
mutex and preserves any existing editor/build process. It builds the editor DLL,
runs `KukriNetworkAudit`, then starts a hidden NullRHI listen host and client on
UDP port 19963 with 60 ms lag and 3% loss configured on each peer. Profiles use
unique `SkillNetworkAudit_` identities and isolated user directories.

- `-IsolatedOnly`: build and authority cases, without the two network processes.
- `-SkipBuild`: use the current DLL after a known successful matching build.
- `check_assets.py`: read-only enumeration of the merged Kukri/common catalogs,
  icon PNG/Texture presence, and saved module/material references.

The isolated suite exercises accepted attack receipts, per-knife costs, both
legendary rune cycles, cold/freeze rules, and canine bleed through actual common
hit settlement. It is not a UDP attack/RPC replay.

`KukriRuneWireAudit` exercises the real production replicated rune components
with deterministic fixture profiles. The fixture calls authority hit confirmation
to charge them; it does not simulate player input or upload inventory. Six phases
cover mixed equipment, simultaneous activations, switching away/back, another
activation, and death. Each phase checks the client owner, client observer of the
host, and host observer of the client. Gauges remain private to their owner.

NullRHI checks replicated state and presentation component routing, not pixels,
material appearance, particle density, full combat gameplay, reconnect, dedicated
servers, or packaged builds. Output logs/JSON are retained under
`SourceAssets/KukriFrostRaven20261028/CompletionAudit/<timestamp>/`.
