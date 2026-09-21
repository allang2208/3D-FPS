# Voxel building system audit (collapse / damage / meshing / solver / grounding)

Scope: `Source/FPSGAME/Building/VoxelBuildWorldCollapse.cpp`, `VoxelBuildWorldDamage.cpp`,
`VoxelCollapseFragment.{cpp,h}`, `VoxelBuildGrounding.{cpp,h}`, `VoxelBuildGeometry.{cpp,h}`,
`VoxelSurfaceMesher.{cpp,h}`, `VoxelBuildWorldMesh.cpp`, `VoxelJointStrength.h`,
`VoxelSupportGraph.{cpp,h}`. Caller context (Tick order, `ApplyChanges`, `ApplyOverloadDamage`,
`TickStructure`, persistence, `FPSBlast` adapter) is marked "(context, outside the listed files)".
Every claim below is quoted from source; numbers that I did not measure at runtime are labelled derived.

## 1. Collapse → debris

**Path:** `TickStructure` builds a `FVoxelFragmentSave` from the detached island nodes
`VoxelBuildWorldStructure.cpp:141` `{State.Cells.Add({Node.Key,Node.Min-Origin,Node.Material,Node.Damage});Keys.Add(Node.Key);}`,
calls `VoxelBuildWorldStructure.cpp:143` `EnqueueFragment(MoveTemp(State),MoveTemp(Keys),{},bProtecting);`
→ `VoxelBuildWorldCollapse.cpp:32-33` registers every source key in `Runtime->PendingCells` and stores one
`FVoxelPendingFragment` per **island** (not per body).

**Bodies per collapse.** One asynchronous prepare job at a time: `VoxelBuildWorldCollapse.cpp:46`
`if(!WorkerBusy)for(auto& E:Runtime->PendingFragments)` … `VoxelBuildWorldCollapse.cpp:68` `break;`.
Inside the worker, `VoxelBuildWorldCollapse.cpp:59`
`auto Parts=Restore?TArray<FVoxelFragmentSave>{State}:VoxelGeometry::Split(State,Broken,MaxShapes);`
and one `AVoxelCollapseFragment` actor per returned part:
`VoxelBuildWorldCollapse.cpp:78` `auto* Actor=GetWorld()->SpawnActor<AVoxelCollapseFragment>(...)`.
`MaxShapes` is `FMath::Clamp(ShapesPerBody.GetValueOnGameThread(),1,128)` (`:50`, default 64 at `:15`).

Aggregation is **per connected component, then spatially halved**: `VoxelGeometry::Split` floods the bond graph
(`VoxelBuildGeometry.cpp:99-107`) and then subdivides:
`VoxelBuildGeometry.cpp:118` `if(Collision.BoxElems.Num()<=FMath::Max(1,MaxShapes)){Result.Add(MoveTemp(Piece));continue;}`
followed by a longest-axis halving (`:120-124`). So `bodies = islands(I) × 2^k`, bounded by
`1 ≤ bodies ≤ cell count`; total compound shapes `≤ 64 × bodies` (≤128 with the cvar raised).
A solid 16³ chunk = 4096 cells can legally become 1 body (one box) or 4096 bodies (all bonds broken /
all cells disconnected), i.e. **one `UDynamicMeshComponent` + mesh per cell in the worst case**.

**Admission control (awake only).** `VoxelBuildWorldCollapse.cpp:148-149`
`if(!Sleeping&&(Runtime->AwakeBodies>=FMath::Max(1,Bodies.GetValueOnGameThread())||Runtime->AwakeShapes+Actor->ShapeCount()>FMath::Max(128,Shapes.GetValueOnGameThread()))){++I;continue;}`
with defaults `Bodies=128`, `Shapes=2048` (`:12-13`). Spawning is capped at 8 actors/frame and 1.5 ms
(`:74`, `:83`, `:108`); activation at 8/frame (`:153`). **The number of spawned actors and prepared
meshes is not capped** — only simultaneous simulation is. A 4096-piece shatter therefore creates up to
4096 actors over ≥512 frames (~8.5 s at 60 fps) while `Runtime->PendingCells` holds 4096 keys.

**Fragment-vs-fragment / fragment-vs-structure contact.** `AVoxelCollapseFragment::OnCollision`
(`VoxelCollapseFragment.cpp:96`) is bound at construction (`:18`
`Body->OnComponentHit.AddDynamic(this,&AVoxelCollapseFragment::OnCollision);`) and is **cheap**: a
unique-ID tie-break (`:104` `if(OtherFragment&&GetUniqueID()>OtherFragment->GetUniqueID())return;`), a
0.12 s per-fragment rate limit (`:105` `if(Now-LastImpactTime<.12)return;`), a speed/energy gate (`:110`
`if(Speed<.8f||Energy<20)return;`) and then two queue pushes (`:113-114`). No heavy work, but each
accepted contact pushes **two** requests (`QueueFragmentDamage` + `QueueCollapseImpact`).

The static-building callback is heavier: `VoxelBuildWorldDamage.cpp:189`
`if(!Runtime->ContactLoads.ContainsByPredicate([&](const auto& E){return E.Body==OtherComponent;}))` — a
linear scan of `ContactLoads` per contact event — and `:190`
`FName(*FString::Printf(TEXT("VoxelContact_%u"),OtherComponent->GetUniqueID()))` — string formatting plus
an `FName` construction per newly tracked body.

**Destruction / accumulation.** Fragments are destroyed on exactly four paths: kill-Z
(`VoxelBuildWorldCollapse.cpp:116-118`), rest-recycling (`:134-138`), replacement after partial damage
(`VoxelBuildWorldDamage.cpp:121` `else if(Targets.IsEmpty()){Fragments.Remove(Fragment->Id());Fragment->Destroy();}`
and `:99-100`), and explicit `RemoveFragment` (`:18-25`). Everything else accumulates.
Two accumulation facts:
* waiting (never-activated) fragments are classified as settled: `VoxelCollapseFragment.cpp:51`
  `bool AVoxelCollapseFragment::IsMoving() const {return bStarted&&!bReplacing&&Body->IsAnyRigidBodyAwake();}`
  is false while `bStarted==false`, so `VoxelBuildWorldCollapse.cpp:126`
  `if(!IsValid(Fragment)||!Fragment->AccrueRestSeconds(FrameDelta,2.f))continue;` keeps accruing rest time
  from spawn. Debris that waits >2 s in the activation queue is destroyed **without ever simulating**.
* `Runtime->ContactLoads` (`VoxelBuildRuntime.h:75`) and `AVoxelBuildWorld::Fragments` entries are only
  removed when the body dies (`VoxelBuildWorldDamage.cpp:138-141`) / by the four paths above; the
  `Fragments` loop skips but never erases stale entries (`VoxelBuildWorldCollapse.cpp:113` `if(IsValid(E.Value))`).

## 2. `QueueFragmentDamage` / `QueueCollapseImpact`

One queue: `VoxelBuildRuntime.h:73` `TArray<FVoxelDamageRequest> DamageQueue;`, appended with no cap and
no dedup (`VoxelBuildWorldDamage.cpp:33`, `:39`, `:45`, `:197`).

Drain: once per frame from `Tick` (`VoxelBuildWorld.cpp:419` `TickDamage();TickMeshes();TickFragments();TickStructure();TickPersistence();`),
`VoxelBuildWorldDamage.cpp:129` `if(++Processed>=4||FPlatformTime::Seconds()-Start>.0015)break;` → ≤4 entries
per frame. Per-entry cost:
* static: `VoxelBuildWorldDamage.cpp:65` `for(const auto& Key:SupportGraph->Within(Point,FMath::Max(.5f,Request.Radius)))`
  → `VoxelSupportGraph.cpp:42-44` bucket walk, or a **full `Nodes` scan** when
  `Range.X*Range.Y*Range.Z>Nodes.Num()`; then per cell `:68` `FindChecked`, `:82` FBox distance,
  `:93` `Palette->Physical(Cell.Material)` (linear `FindByPredicate`, `VoxelBuildPalette.cpp:37`),
  `:99-105` three hash containers.
* fragment: `VoxelBuildWorldDamage.cpp:76` `FragmentState=Fragment->Snapshot();Targets=FragmentState.Cells;` —
  **two full copies** of the fragment cell array (`VoxelCollapseFragment.cpp:60` `auto Result=State;`), then
  `:82` distance per cell. O(cells) per request, no dedup, no radius early-out for `Radius<=0`.

Defects in the drain loop: `VoxelBuildWorldDamage.cpp:59`
`const auto Request=Runtime->DamageQueue[0];Runtime->DamageQueue.RemoveAt(0,1,EAllowShrinking::No);` — an
O(n) memmove per pop (O(n²) to drain), and the `continue` paths at `:75`, `:78`, `:88` bypass the
`Processed`/time check entirely, so one `TickDamage()` call can pop an unbounded number of
no-op entries in a single frame. `Runtime->PendingFragments` is scanned per request (`:74`
`bool Replacing=false;for(const auto& E:Runtime->PendingFragments)`).

## 3. Damage path

* `DamageBuilding` (`VoxelBuildWorldDamage.cpp:30-34`): O(1) enqueue only.
* `TickDamage`: ≤4 entries/frame (see §2). It **does** drive edit + remesh + re-solve: `:113`
  `if(!Removed.IsEmpty())ApplyChanges(Removed);` else `:114` `{++Revision;Runtime->NextIterations=256;}`.
  `ApplyChanges` (`VoxelBuildWorld.cpp:333-365`) per removed cell does `SupportGraph->Remove` (`:343`),
  re-add for added cells (`:352`), a scan of the whole broken-bond set (`:348`
  `for(auto It=SupportGraph->Broken.CreateIterator();It;++It)if(It->A==Key||It->B==Key)It.RemoveCurrent();`
  → O(|Broken|) per added cell) and one batched `RebuildAffected(Edit)` + `VerifyPrefabSupport(Edit)`,
  then `:361` `++Revision;Runtime->NextIterations=256;Runtime->StructureAt=GetWorld()->GetTimeSeconds()+.08;`.
  `RebuildAffected` (`VoxelBuildWorldMesh.cpp:23-25`) expands each edited cell to 27 chunk keys and marks
  up to 8 render chunks fully dirty.
* `Revision` bumps invalidate an in-progress gather (`VoxelBuildWorldStructure.cpp:179`
  `if(Runtime->GatherRevision!=Revision||Runtime->GatherQueue.IsEmpty())`), so a stream of damage events
  restarts the incremental gather (`:219-246`, 512 nodes / 1 ms per frame) and can starve solves.
* No direct full-structure iteration per damage event, **but** every scheduled solve seeds from
  `Runtime->LoadRatios`, which grows to one entry per cell ever evaluated and is scanned in full:
  `VoxelBuildWorldStructure.cpp:202` `for(const TPair<FVoxelBuildKey,float>& Entry:Runtime->LoadRatios)`.
* `ApplyOverloadDamage` (`VoxelBuildWorldStructure.cpp:35-58`, context): O(overloaded cells) with hash ops
  per cell, `:55` `if(!Removed.IsEmpty()){History.Reset();ApplyChanges(Removed);}` and `:57`
  `if(bChanged)Runtime->StructureAt=...OverloadTickCVar...` (default 0.5 s, `:19`) → during sustained
  overload a solve (up to 4096 nodes) is re-run twice a second.
* `SetAppliedLoad` (`VoxelBuildWorldDamage.cpp:156-184`) ends with `:183` `++Revision;Runtime->NextIterations=256;`
  so moving loads also invalidate gathers; the per-frame load sampler does ≤32 traces / 0.25 s (`:134-152`).

## 4. Geometry / meshing

**`FVoxelGeometry::Split`** (`VoxelBuildGeometry.cpp:93-141`): builds a support graph from the cells
(`:96-97`, one `Add` + `Indices.Add` per cell), floods islands (`:99-107`, O(N+E)), then per island
`:108` `FVoxelFragmentSave Part=Source;` — **a full copy of the source fragment (all cells + all broken
bonds) per island**, O(N·I) — `:109` `Part.Cells.Add(Source.Cells[Indices.FindChecked(K)])` (hash lookup per
cell), then the subdivision loop `:113-125` recomputes `Volumes(...)` + `Boxes(...)` for the growing/shrinking
piece at every level (O(M log M) hashing per level, allocations per level: `TMap<FGuid,FVolume>`,
`TMap<FIntVector,int32>`, `TSet<FIntVector>`, `TArray<FIntVector> Ordered`). Re-keying at `:129-140` allocates
two `TMap`s per part and re-tests every broken bond (`:138`).

**Greedy box merge** (`VoxelBuildGeometry.cpp:11-28`): `void Boxes(TSet<FIntVector> Remaining,...)` takes the
set by value (all call sites use `MoveTemp`, so no copy), then `:13` `TArray<FIntVector> Ordered=Remaining.Array();`
+ `:14` sort, and for each box grows W, then H via `Row` (`:20-21`) and D via `Layer` (`:22-23`), re-verifying
whole rows/layers at every step → O(W·H·D) `Contains` calls per box plus O(W·H·D) removals ⇒
O(M log M + M) hashes per call with a TSet/array allocation. Called per chunk, per fragment volume, and per
`Split` subdivision level.

**Surface extraction** (`VoxelSurfaceMesher.cpp`): a smooth-occupancy field sampled on a
`Steps=Side*Subdivisions=80`, `Nodes=81` grid (`:10`, `:105`). Sampling reads the one-cell halo
(`:90-99`, 18³ = 5832 slots), early-outs on empty/full (`:100`
`if(Occupied==0||Occupied==Field.Slots.Num())return;`), clamps the evaluated range to the occupied bbox
(`:103-104`), fills `:113` `TArray<float> Values;Values.SetNumUninitialized(Nodes*Nodes*Nodes);` =
**531,441 floats ≈ 2.03 MB per `Build` call** (per source chunk) and then does marching tets over the
non-planar cubes (`:146-182`, `:171-181`, ≤6 tets, ≤2 triangles per tet) with the flat-face fast path
`:145-166` (`FlatMasks`, merged greedily at `:184-205`). Every triangle appends **3 vertices plus 3 normal
and 3 UV attribute elements and one material ID** (`:126-136`) — no vertex sharing.

*Complexity / counts (derived).* Cost is O(evaluated cubes) = O(bbox subcell volume) ≤ 80³ = **512,000 cubes
per chunk**, each with 8 field reads; triangle bound is 12 per non-flat boundary cube = **≤6.14 M triangles /
18.4 M vertices per 16³ chunk** in a pathological (checkerboard-like) occupancy. Typical grid-aligned flat
faces are merged by `FlatMasks` into a few quads. I did not measure real vertex/index counts at runtime —
"unverified" for actual scenes.

Allocations per rebuild: `Field.Slots` 5832 int32 (~23 KB), `Values` ~2.03 MB, `Coordinates`/`Blends`,
`TMap<FIntVector,TArray<int32>> FlatMasks` with `:164` `if(Mask.IsEmpty())Mask.Init(0,Steps*Steps);`
(6400 int32 ≈ 25.6 KB per distinct plane), the incremental `FDynamicMesh3` growth, a `TSet<FIntVector>
Occupied` and its `Ordered` array, plus (in `Batch`) a second mesh copy through
`VoxelBuildGeometry.cpp:59` `Editor.AppendMesh(&Part->Mesh,Maps,...)`.

**Threading / granularity.** Meshing is off the game thread: `VoxelBuildWorldMesh.cpp:88-89`
`Job.Future=Async(EAsyncExecution::ThreadPool,[Inputs=MoveTemp(Inputs),Radius]() mutable{return VoxelGeometry::Batch(MoveTemp(Inputs),Radius);});`
(2 in-flight jobs, `:11`). The game thread still does `VoxelBuildWorldMesh.cpp:120-121`
`Component->SetMesh(MoveTemp(Geometry->Mesh));Component->SetSimpleCollisionShapes(Geometry->Collision,true);`
— a full mesh copy plus box-shape creation, 1 apply/frame (`:12`). Rebuild granularity is the **whole 16³
chunk** (`VoxelGeometry::Chunk` → `VoxelSurface::Build(...,Origin,16,Radius,...)` at `VoxelBuildGeometry.cpp:45`),
and a single-cell edit dirties up to 8 render chunks (`VoxelBuildWorldMesh.cpp:24-25`), each of which is
re-meshed from all of its accumulated source chunks (`:61` `for(const auto& Source:Runtime->MeshGroups.FindChecked(Key))`,
never region-limited).

## 5. Support solver

`VoxelStress::Solve` (`VoxelSupportGraph.cpp:97-206`):
1. rebuilds a graph from the node array: `:101` `for(const auto& Node:Input.Nodes){Graph.Add(Node);Result.Evaluated.Add(Node.Key);}` —
   `FVoxelSupportGraph::Add` (`:48-59`) calls `Near()` per node (`:10-16`, 125 buckets, **a `TArray`
   allocation per node**) and `Contact()` per neighbour;
2. `SolveConnectivity` BFS (`:77-87`), then a second component BFS (`:103-120`);
3. builds AoS `FPSBlastNode` copies (`:122-129`, one `Indices` `TMap` insert per node),
4. builds bonds, recomputing `FVoxelSupportGraph::Contact` for every edge (`:143-145`
   `if(Indices.FindChecked(Key)<Indices.FindChecked(Other)){FVoxelContact C;if(FVoxelSupportGraph::Contact(...))AddBond(...);}`),
5. `:147-148` `TArray<FPSBlastForce> Forces;Forces.SetNumZeroed(Bonds.Num()); const bool Converged=FPSBlastSolve(Nodes.GetData(),...,Input.Iterations,Forces.GetData());`
6. one linear stress pass over all bonds (`:150-203`) with `Result.LoadRatios` hash inserts.

Iterations: `Input.Iterations` comes from `Runtime->NextIterations` (256, `VoxelBuildRuntime.h:63`), doubled
on non-convergence up to 2048 (`VoxelBuildWorldStructure.cpp:86-87`). The adapter sets
`params.maxIter=iterations; params.tolerance=0.001f;` (`FPSBlast.cpp:31`, context) and the inner CGNR loop
(`cgnr.h:124-136`) does two O(bonds) sparse mat-vecs plus O(nodes) vector ops per iteration ⇒
**per solve ≈ iterations × O(N_nodes + N_bonds)**, i.e. ~256 × 15k coupling ops ≈ 3.8 M AngLin6 ops for
4096 nodes (~11k bonds).

Multithreading: **single-threaded**. There is no OpenMP/parallel construct in `cgnr.h`, `stress.cpp` or the
adapter; only SIMD is used (`stress.cpp:230` `const int result = s_use_simd ? CGNR_SIMD().solve(...)`). The
whole `Solve` runs on one thread-pool thread (`VoxelBuildWorldStructure.cpp:254-255`, context).

Allocations per solve: 4 `std::vector`s in the adapter (`FPSBlast.cpp:10-13`: nodes, bonds, velocity, impulse),
`StressProcessor::prepare` resizing 5 buffers (`stress.cpp:62-66`), plus the UE-side graph (`Nodes`, `Edges`,
`Buckets` per bucket, `Supported`), `Indices`, `Nodes`, `Links`, `Bonds`, `Forces`, `TArray` from every
`Near()` call, and the `Result` sets/maps. Nothing is pooled across solves.

Cost per node: documented offline baseline in `Docs/Building/voxel-build-workflow.md:53` —
"**200 格 → 1.2 ms；2 000 格 → 11.0 ms；20 000 格 → 95.8 ms**，约 **4.8 µs/节点/次**（线性）" (single-threaded,
256 iterations, same solver). I did not re-measure; treat 4.8 µs/node/solve as the project's own measurement.
**Dominant cost = the 256-iteration CGNR loop over bonds**, followed by the per-solve graph rebuild + copies.

Extra solver-side cost: `:192` `if(FVoxelOverloadCell* Existing=Result.Overload.FindByPredicate([&](const FVoxelOverloadCell& E){return E.Key==Key;}))`
is a linear scan **inside** the bond loop → O(bonds × |Overload|), worst case O(N²) for a fully overloaded
structure; `:166-167` does two hash lookups per endpoint per bond.

## 6. Grounding

Traces per query: `VoxelGrounding::Sample` runs **up to 5 vertical traces** — `VoxelBuildGrounding.cpp:34`
`const FVector2D Samples[]={{.5,.5},{19.5,.5},{.5,19.5},{19.5,19.5},{10,10}};` with `:38-39` one
`LineTraceSingleByChannel` each (early-out on first failure). `Query()` additionally iterates all pawns per
call (`:18` `for(TActorIterator<APawn> It(World);It;++It)Params.AddIgnoredActor(*It);`).

Call frequency:
* `IsGroundAnchor` = one `Sample` = ≤5 traces; called per uncovered support node at load
  (`VoxelBuildWorld.cpp:226` `E.Value.bAnchor=!Covered&&(IsGroundAnchor(E.Value.Min)||PrefabSupportAt(E.Value.Min));`)
  and per added cell in `ApplyChanges` (`:350` `const bool Anchor=IsGroundAnchor(Min)||PrefabSupportAt(Min);`).
* `ScenePlacementAllowed` = 1 `Sample` (≤5) + 3 axis traces (`:133-136`) + a full `ACharacter` iterator
  (`:108`); called per cell in `CanPlaceAt` (`:243`) and `CanCommit` (`:317`).
* `ResolveGroundPlacement` = 5·Size.X·Size.Y traces (`:69-76` loops X,Y calling `Sample`), i.e. **up to 125
  traces for a 5×5 brush per call**, plus one `Query()` per call (`:65`). It is called from the aiming path
  `VoxelBuildComponent.cpp:644`, throttled to 20 Hz in snap mode (`:641` `GroundSampleAt=Now+1./20.;`) but
  **not throttled in free placement** (`:638-640` comment: "Free placement must follow the aim
  continuously, so it is never throttled").

Caching: `AnchorCache` (`VoxelBuildWorld.h:156`) is **write-only** — it is only ever written/erased
(`VoxelBuildWorld.cpp:226`, `:343`, `:351`, `VoxelBuildWorldPrefab.cpp:121`) and never read, so it saves no
traces while growing to one entry per cell. `PrefabCells`/`PrefabCellOwner` are the only real occupancy caches.

## 7. Correctness / robustness defects

* **Queue drain can run unbounded in one frame**: `VoxelBuildWorldDamage.cpp:75/78/88` `continue` before
  `:129` `if(++Processed>=4||...)break;`; combined with `:59` `RemoveAt(0,1,...)` (O(n) per pop) this is
  O(n²) memmove in a single `TickDamage` call.
* **No dedup / no cap on `DamageQueue`**: a fragment resting against 8 others can push 16 requests in a
  frame (`VoxelCollapseFragment.cpp:113-114`) against a 4/frame drain.
* **Waiting debris is recycled before it ever simulates**: `IsMoving()` is false while `bStarted==false`
  (`VoxelCollapseFragment.cpp:51`) and the recycler only requires 2 s of rest
  (`VoxelBuildWorldCollapse.cpp:126-132`), so pieces parked by the 128/2048 awake budget are turned into
  blocks and destroyed instead of falling.
* **Per-frame full-structure work in the fragment loops**: `VoxelBuildWorldCollapse.cpp:123-133` runs
  `Fragment->Snapshot()` (full cell array copy) and rebuilds `TMap<FString,int64> Blocks` with
  `FString(TEXT("voxel_block_"))+Cell.Material.ToString()` per cell for every still-settled fragment, every
  frame; if `GrantWorldBlocks` fails (its own callee returns false when
  `UI/ColdSteelAreaPickup.cpp:55` `if(P.Items.Num()>=10000)`, or on `!Created`/`!CommitState`) the fragment
  is retried forever. Three full fragment iterations per frame: `VoxelBuildWorld.cpp:418`
  (`SampleVelocity`), `VoxelBuildWorldCollapse.cpp:113-117` (`IsMoving`/`GetActorLocation`),
  `:123-126` (`AccrueRestSeconds` → `IsAnyRigidBodyAwake`) — O(F) Chaos queries per frame.
* **`SupportGraph->Broken` is never pruned on removal**: `VoxelSupportGraph.cpp:61-68`
  `FVoxelSupportGraph::Remove` deletes from `Buckets`, `Edges`, `Nodes`, `Supported` but not `Broken`; the
  set is then copied per solve (`VoxelBuildWorldStructure.cpp:214` `Runtime->Gather.Broken=SupportGraph->Broken;`),
  per fragment prepare (`VoxelBuildWorldCollapse.cpp:52` `Broken=SupportGraph->Broken`) and per `Split`
  (`VoxelBuildGeometry.cpp:95`), and scanned per added cell (`VoxelBuildWorld.cpp:348`).
* **`Runtime->LoadRatios` is never pruned** and is scanned in full on every gather seed
  (`VoxelBuildWorldStructure.cpp:202`); same for `AnchorCache` and `Runtime->MeshGroups` (empty groups are
  never erased, only their sources: `VoxelBuildWorldMesh.cpp:86`).
* **Gather starvation**: any state change bumps `Revision` (`VoxelBuildWorldDamage.cpp:114`, `:183`;
  `VoxelBuildWorld.cpp:361`; `VoxelBuildWorldStructure.cpp:125`), and a revision change discards the
  partially gathered snapshot (`VoxelBuildWorldStructure.cpp:179-185`) while the gather is incremental
  (`:245` `if(Count>=512&&FPlatformTime::Seconds()-Start>.001)break;`) — continuous damage/load churn can
  prevent a solve from ever being submitted (behavioural risk; I did not reproduce it in-game).
* **Missed settle cost after replacement**: `VoxelBuildWorldDamage.cpp:124-125`
  `Fragment->FreezeForReplacement();...EnqueueFragment(MoveTemp(FragmentState),{},Fragment->Id());` freezes
  the old body (physics off, `VoxelCollapseFragment.cpp:76`) while it keeps `BlockAll` collision and stays
  visible (`EnableWaitingCollision` sets `SetActorHiddenInGame(false)`, `:37`) until the replacement is
  spawned — an invisible-to-physics but solid obstacle for ≥1 frame.
* **Unchecked dereferences** (all low practical risk but unguarded): `VoxelCollapseFragment.cpp:26-27`
  `Body->SetPhysMaterialOverride(OwnerWorld->ContactMaterial()); ... Mass=Geometry->MassKg;`;
  `VoxelBuildWorldCollapse.cpp:116` `GetWorld()->GetWorldSettings()->KillZ`;
  `VoxelBuildWorldMesh.cpp:61` `Runtime->MeshGroups.FindChecked(Key)` (safe today only because groups are
  never erased); `VoxelBuildWorldMesh.cpp:96` `if(Geometry->Mesh.TriangleCount()==0...)` (worker always
  returns non-null today).
* **`SetCenterOfMass` argument looks wrong**: `VoxelCollapseFragment.cpp:45`
  `Body->SetCenterOfMass(DesiredCenter-GetActorTransform().InverseTransformPosition(Body->GetCenterOfMass()));`
  subtracts the current local COM (an offset) from the desired local centre; correct only while the body COM
  is still at the component origin, which is the case on the single `Activate()` path (guarded by `bStarted`).
  Semantics unverified beyond that.
* **Contact tolerance assumes an exact lattice**: `VoxelSupportGraph.cpp:23`
  `if(FMath::Abs(FMath::Abs(Delta)-20)>.2)continue;` while free volumes can be placed on arbitrary float
  origins (`VoxelBuildGrounding.cpp:80` `else Origin.Z=Highest;`) and cells are addressed as
  `VolumeOrigin(Volume)+CellMin(Cell)` (`VoxelBuildWorld.cpp:208`). Two volumes that do not line up to
  within 0.2 cm get no bond and, in `Split`, become interpenetrating rigid bodies. Unverified in-game.
* **Float/double split between probe and runtime**: the shared maths is `double`
  (`VoxelJointStrength.h:80-166`) while the runtime solver uses `float` nodes/inertia
  (`FPSBlast.h:6` `struct FPSBlastNode { float position[3]; float mass; float inertia; float acceleration[3]; };`,
  `VoxelSupportGraph.cpp:128` `Mass*.04f/6`). `Docs/Building/voxel-build-workflow.md:225` states the offline
  probe uses "512 次迭代" but `VoxelJointStrength::Ratio` defaults to 256 (`:80`) and the probe does not
  override it (`Tools/Building/voxel_stress_probe.cpp:26,47,49`) — documentation drift.
* **Missing `SetActorTickEnabled`**: `AVoxelBuildWorld` ticks unconditionally
  (`VoxelBuildWorld.cpp:46` `PrimaryActorTick.bCanEverTick=true;`) and is never disabled even with zero
  structures/zero debris; `AVoxelCollapseFragment` correctly sets `:9` `PrimaryActorTick.bCanEverTick=false;`.
* No unbounded recursion or non-terminating loop was found in the flood fills (`VoxelBuildGeometry.cpp:99-107`),
  the subdivision loop (`:113-125`, each split reaches either ≤MaxShapes boxes or a single cell) or `Boxes`.
* No dangling-pointer hazard found: fragment references are `TWeakObjectPtr`
  (`VoxelBuildRuntime.h:35,41,49`; `VoxelCollapseFragment.h:46`), futures are waited at teardown
  (`VoxelBuildWorld.cpp:429-431`), and worker lambdas capture value snapshots only.
* Physics-body leak check: parts that never activate are still recycled/destroyed by the rest path (see the
  bullet above), so `UDynamicMeshComponent` bodies do not leak indefinitely — but the actor/mesh *count* is
  unbounded between spawn and recycle.

## Performance findings (ranked by expected win)

| Finding | file:line | Why it costs | Suggested fix | Risk |
| --- | --- | --- | --- | --- |
| Settled-fragment recycle block runs per frame per fragment: full `Snapshot()` + `FName::ToString` per cell + `GrantWorldBlocks` (which itself calls `Snapshot()`/`CommitState` in the callee) | `VoxelBuildWorldCollapse.cpp:121-133` (`if(!IsValid(Fragment)||!Fragment->AccrueRestSeconds(FrameDelta,2.f))continue;` … `Model->GrantWorldBlocks(Blocks,Fragment->GetActorLocation())`) | O(F·C) string/FName allocations + a full inventory copy/save attempt **every frame** for every fragment that cannot be converted; scales with debris count × cells | One-shot: mark a fragment "recycle attempted / failed" and retry on a timer (e.g. 1 s) or on inventory change; hoist the block-name → material mapping to a precomputed `TMap<FName,FString>`; skip entirely when `GrantWorldBlocks` is known-unavailable | Low: behaviour unchanged, only retry cadence |
| `DamageQueue` drain: O(n) `RemoveAt(0)` per pop plus `continue` paths that bypass the 4-entry/1.5 ms budget | `VoxelBuildWorldDamage.cpp:59` and `:75,:78,:88` vs `:129` | Draining n requests is O(n²) memmove; no-op requests are unbounded within one frame → single-frame spikes | Use a head index (`LoadRead`-style) or a ring buffer, and move the budget check to the top of the loop so every pop counts | Low |
| No dedup / no cap on damage requests; each accepted contact enqueues two requests | `VoxelBuildWorldDamage.cpp:33,39,45`; `VoxelCollapseFragment.cpp:113-114`; drain at 4/frame `VoxelBuildWorldDamage.cpp:129` | Queue latency grows linearly with contact bursts; duplicate static requests re-scan the same neighbourhood | Coalesce by (`Key`/`Fragment`, quantised position) with an accumulated amount/energy; cap queue length and drop lowest-energy entries | Medium: aggregated damage must preserve the current post-hit subtraction |
| Fragment damage entry copies the whole fragment cell array twice and scans it per request | `VoxelBuildWorldDamage.cpp:76` `FragmentState=Fragment->Snapshot();Targets=FragmentState.Cells;`; `VoxelBuildWorldDamage.cpp:80-86` | O(C_fragment) copy + O(C) distance/`Physical()` work per request, no spatial index (no use of `Min`/`Max` bounds) | Keep a per-fragment AABB and per-cell lookup; accept an in/out cell list instead of copying the state; process damage in fragment-local batches | Low/Medium |
| Three full `Fragments` passes per frame, two with Chaos queries (`SampleVelocity`, `IsMoving`, `GetActorLocation`, `AccrueRestSeconds`→`IsAnyRigidBodyAwake`) | `VoxelBuildWorld.cpp:418`; `VoxelBuildWorldCollapse.cpp:113-117`, `:123-126` | O(F) physics queries per frame with F up to thousands after a shatter | Merge into one pass; cache the awake flag from the physics callback (`OnCollision`) instead of polling; skip fragments queued in `Activation` | Low |
| Fragment prepare is globally serial (one job at a time) and spawn is 8/frame, 1.5 ms | `VoxelBuildWorldCollapse.cpp:46` `if(!WorkerBusy)`, `:68` `break;`, `:74`, `:83`, `:108` | A 1000-piece collapse needs ≥125 frames just to spawn; `PendingCells` blocks edits the whole time; single job also under-uses the pool | Allow N concurrent prepares (fps cvar), prioritise nearest-to-view (as `TickMeshes` already does), and release `PendingCells` per part | Medium: more memory in flight, ordering of `Replaces` |
| Mesh barrier build per finished fragment is O(27 × cells) map operations outside any frame budget | `VoxelBuildWorldCollapse.cpp:87-98` (esp. `:96-97`) | For a 1000-cell island that is 27,000 `TMap` inserts in one frame, on top of the 1.5 ms spawn budget | Build the barrier from the fragment's **bounds** (one chunk AABB) instead of per cell; reuse a set | Low |
| Mesher allocates a full `81³` value grid (~2 MB) per source chunk and evaluates up to 512,000 sample cubes, for every dirty chunk (up to 8 per single-cell edit, up to 27 source chunks) | `VoxelSurfaceMesher.cpp:113` `Values.SetNumUninitialized(Nodes*Nodes*Nodes);`; `:114-115`, `:147`; `VoxelBuildWorldMesh.cpp:24-25`, `:88-89`; `VoxelBuildGeometry.cpp:45` | ~2 MB alloc + 512k×8 field reads per chunk rebuild; full 16³ remesh for one placed block; also ~25.6 KB per distinct flat plane (`:164`) | Size `Values` to the clamped bbox (`(Last-First+1)³`) instead of `Nodes³`; dirty only the chunks whose bbox actually intersects the edit; cache the field per chunk across rebuilds | Medium: index math and per-source `Batch` offsets |
| Solver solves on one thread with 256 CGNR iterations over the full node/bond set; per-solve allocations, no reuse | `VoxelSupportGraph.cpp:147-149`; `:101`; `:10-16`; adapter `FPSBlast.cpp:10-13` | ~4.8 µs/node/solve (project baseline, `Docs/Building/voxel-build-workflow.md:53`); a 4096-node solve ≈ 20 ms of one core every overload tick (0.5 s) | Lower `NextIterations` when `Ratio` is far from 1; reuse `StressProcessor`/buffers across solves; resolve converged bonds early; avoid `Near()`'s per-node `TArray` | Medium: solver accuracy/behaviour is contract-bound |
| `Result.Overload.FindByPredicate` linear scan inside the bond loop | `VoxelSupportGraph.cpp:192` | O(bonds × |Overload|), worst case ≈O(N²) on a heavily overloaded structure | Accumulate overload rates in a `TMap<FVoxelBuildKey,float>` during the loop and emit the array once | Low |
| `AnchorCache` is write-only; `IsGroundAnchor` re-traces (≤5 rays) per node/cell and is called for every uncovered node at load | `VoxelBuildWorld.h:156` (no reader); `VoxelBuildWorld.cpp:226`, `:350`; `VoxelBuildGrounding.cpp:100` | Dead memory + repeated raycasts during load and every edit (`O(N)·5` rays on load) | Either read the cache in `IsGroundAnchor`/`ApplyChanges`, or delete it; batch anchor probes per edit instead of per cell | Low |
| `ResolveGroundPlacement` performs 5·X·Y traces per call and is unthrottled in free placement; `Query()` rebuilds the ignore list via `TActorIterator<APawn>` each call | `VoxelBuildGrounding.cpp:34-39`, `:18`, `:65`, `:69-76`; caller `VoxelBuildComponent.cpp:641` (20 Hz snap) vs `:638-640` (free = unthrottled) | Up to 125 traces/frame for a 5×5 brush plus a full pawn iteration | Cache one `FCollisionQueryParams` per world/tick; sample 4 corners + centre only when the brush moved; throttle free placement to the same 20 Hz | Low/Medium: preview responsiveness |
| `FVoxelGeometry::Split` copies the whole source fragment (cells + broken bonds) per island and re-runs `Volumes`+`Boxes` at every subdivision level | `VoxelBuildGeometry.cpp:108` `FVoxelFragmentSave Part=Source;`, `:113-125` | O(N·I) copies + repeated O(M log M) hashing; the copy at `:108` is thrown away by `Part.Cells.Reset()` at `:108` | Build each part directly from its index list (skip the full copy); carry the box count through the subdivision instead of recomputing from scratch | Low |
| `SupportGraph->Broken` grows forever (not pruned by `Remove`) and is copied per solve/prepare/`Split` and scanned per added cell | `VoxelSupportGraph.cpp:61-68`; `VoxelBuildWorld.cpp:348`; `VoxelBuildWorldStructure.cpp:214`; `VoxelBuildWorldCollapse.cpp:52` | O(|Broken|) copies per solve and per fragment, plus O(|Broken|) scan per placed cell | Prune bonds touching a removed key inside `FVoxelSupportGraph::Remove`, and prune the saved set | Low |
| `VoxelJointStrength::MaxSpanMeters` fills a 2 MB static lookup table on every `Ratio()` call and runs 25 spans × 2 loads × every material at panel init | `VoxelJointStrength.h:86-87` `static long long Lookup[64*64*64]; std::fill(Lookup, Lookup + 64*64*64, -1);`, `:174-183`; caller `VoxelBuildComponent.cpp:460-461` | 25 × 2 MB memset + 50 CGNR solves per material, once, on the game thread (panel init) → tens of ms hitch | Fill the table only over the indices actually used (`Key()` range of the cells), or use a `TMap`/hash and clear just those entries | Low |
| `OnBuildingHit` scans `ContactLoads` and creates an `FName` from `FString::Printf` per contact | `VoxelBuildWorldDamage.cpp:189-191` | O(#tracked bodies) + FName pool churn on every hit event of every simulating body against the building | Key `ContactLoads` by component (`TMap<TObjectPtr<UPrimitiveComponent>,int32>`) and store the id once at registration | Low |
| Per-solve seed scan is O(all evaluated cells) and any `Revision` bump discards the in-flight gather | `VoxelBuildWorldStructure.cpp:202`, `:179-185`, `:245` | Local solves still pay a full-`LoadRatios` scan; continuous damage can restart the gather indefinitely | Keep a dirty/threshold-limited seed set instead of scanning `LoadRatios`; queue revision changes and only restart between gathers | Medium: solve region correctness |
