#pragma once
#include "Async/Future.h"
#include "VoxelSupportGraph.h"
#include "VoxelBuildGeometry.h"

class AVoxelCollapseFragment;
class ACharacter;
class UPrimitiveComponent;
struct FVoxelMeshJob
{
    FVoxelBuildKey Key;
    uint64 Revision=0;
    TFuture<TSharedPtr<FVoxelGeometry>> Future;
};
struct FVoxelPreparedFragment
{
    FVoxelFragmentSave State;
    TSharedPtr<FVoxelGeometry> Geometry;
};
struct FVoxelPendingFragment
{
    FVoxelFragmentSave State;
    TArray<FVoxelBuildKey> Sources;
    FGuid Replaces;
    /** Spawned as failed-placement debris: it falls, but it does not damage the standing building. */
    bool bFailureDebris=false;
    TFuture<TArray<FVoxelPreparedFragment>> Future;
    TArray<FVoxelPreparedFragment> Prepared;
    TArray<TWeakObjectPtr<AVoxelCollapseFragment>> Spawned;
    int32 NextSpawn=0;
    bool bPrepared=false;
};
struct FVoxelActivation
{
    TWeakObjectPtr<AVoxelCollapseFragment> Actor;
    TSharedPtr<TMap<FVoxelBuildKey,uint64>> MeshBarrier;
    bool bCollisionReady=false;
};
struct FVoxelDamageRequest
{
    TWeakObjectPtr<AVoxelCollapseFragment> Fragment;
    FVector Position;
    float Amount=0,Radius=0,Energy=0;
    bool bStatic=true;
};
struct FVoxelExternalLoad {FVoxelBuildKey Key;float Mass=0;};
struct FVoxelContactLoad
{
    TWeakObjectPtr<UPrimitiveComponent> Body;
    FName Id;
    FVector LocalContact;
};

struct FVoxelBuildRuntime
{
    TSet<FVoxelBuildKey> DirtySupport,PendingCells;
    /** 本次收集的 BFS 深度；配合 SolveRegionHops 把求解限制在改动附近。 */
    TMap<FVoxelBuildKey,int32> GatherHops;
    TMap<FVoxelBuildKey,uint64> NodeEpoch,JobEpoch;
    TArray<FVoxelBuildKey> GatherQueue;
    TSet<FVoxelBuildKey> GatherSeen,JobKeys;
    FVoxelStressInput Gather;
    int32 GatherRead=0,NextIterations=256;
    uint64 GatherRevision=0;
    TFuture<FVoxelStressResult> Stress;
    TMap<FVoxelBuildKey,float> LoadRatios;
    TSet<FVoxelBuildKey> DirtyChunks;
    TMap<FVoxelBuildKey,TSet<FVoxelBuildKey>> MeshGroups;
    TMap<FVoxelBuildKey,uint64> MeshRevisions,AppliedRevisions;
    TArray<FVoxelMeshJob> MeshJobs;
    TMap<FGuid,TSharedPtr<FVoxelPendingFragment>> PendingFragments;
    TArray<FVoxelActivation> Activation;
    TArray<FVoxelDamageRequest> DamageQueue;
    TMap<FName,FVoxelExternalLoad> Loads;
    TArray<FVoxelContactLoad> ContactLoads;
    int32 LoadRead=0;
    TFuture<bool> SaveJob;
    /** 求解观测：面板与验收用它报告"每次解算的耗时/规模"。 */
    double SolveStartedAt=0,LastFullSolveAt=0;
    float LastSolveSeconds=0;
    int32 LastSolveNodes=0,LastSolveBoundary=0;
    bool bGatherFullSolve=true;
    // Weakest joint of the last published solve, and the one that killed the last placement.
    FVoxelBondStress WorstBond,FailureBond;
    bool bSaveDirty=false,bSaveFailed=false,bStressApproximate=false;
    double SaveAt=0,StructureAt=0,LoadSampleAt=0,MotionSaveAt=0;
    /** 上次结算过载损伤的时间；过载期间以固定步长持续累积。 */
    double OverloadAt=0;
    int32 AwakeBodies=0,AwakeShapes=0;
    // Build-failure isolation (Docs/Building/voxel-build-workflow.md 3.6). FreshCells holds the
    // cells added by the most recent accepted placement batch and FreshAt is when it was committed.
    // While that window is open the stress result may destroy the batch, but never the structure that
    // was already standing; bFreshRolledBack only feeds the on-screen status line.
    TSet<FVoxelBuildKey> FreshCells;
    double FreshAt=0;
    bool bFreshRolledBack=false;
};
