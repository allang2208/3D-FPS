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
    bool bSaveDirty=false,bSaveFailed=false,bStressApproximate=false;
    double SaveAt=0,StructureAt=0,LoadSampleAt=0,MotionSaveAt=0;
    int32 AwakeBodies=0,AwakeShapes=0;
};
