#pragma once
#include "CoreMinimal.h"
#include "PKMExitCoverDynamics.h"
#include "PKMSoftBeltDynamics.h"

class USkeletalMesh;
class USkeletalMeshComponent;

// Cosmetic leaf-bone layer. Ammo, firing and reload events remain authoritative
// in the character; none of these presentation counters alter gameplay state.
struct FPKMOutgoingBeltDynamics
{
    void Configure(bool Enabled, bool Reloading, bool Empty, float SourceTime,
        int32 Rounds, int32 Capacity, bool Firing, float FireSourceTime, bool Inspection);
    void Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose);
private:
    bool bEnabled=false, bReloading=false, bEmptyReload=false, bInspection=false, bInitialized=false;
    int32 PreviousRounds=0, FedLinks=0;
    float ReloadTime=0.f, VisibleFeed=0.f;
    TWeakObjectPtr<USkeletalMesh> SourceMesh;
    int32 BoneCount=0, Root=INDEX_NONE, Tip=INDEX_NONE, NewTip=INDEX_NONE;
    int32 Tab=INDEX_NONE, NewTab=INDEX_NONE;
    TArray<int32> Clips, Bridges;
    TArray<FTransform> BindLocal;
    bool bOutletFollowingHand=false;
    FPKMSoftChain OutletChain;
    FPKMSoftBeltDynamics ReloadBelts;
    FPKMExitCoverDynamics ExitCover;
};
