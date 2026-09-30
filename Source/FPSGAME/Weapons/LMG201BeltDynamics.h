#pragma once
#include "CoreMinimal.h"
#include "PKMSoftBeltDynamics.h"

class USkeletalMesh;
class USkeletalMeshComponent;

// Cosmetic indexing and constrained secondary motion for the 201 cloth feed.
// Owned by the viewmodel; it never writes ammunition, reload or inventory state.
struct FLMG201BeltDynamics
{
    void Configure(bool Enabled,bool Reloading,bool Empty,float ReloadSourceTime,
        int32 Rounds,bool Firing,float FireSourceTime,double ShotWorldTime,bool Inspection);
    void Apply(USkeletalMeshComponent& Mesh,TArray<FTransform>& Pose);
private:
    bool bEnabled=false,bReloading=false,bEmpty=false,bInspection=false,bInitialized=false;
    bool bIndexedMesh=false,bHadOutput=false,bLastReloading=false,bFeedShot=false;
    int32 PreviousRounds=0,FedCells=0,Root=INDEX_NONE,BoneCount=0;
    int32 OldSection=INDEX_NONE,NewSection=INDEX_NONE;
    float Feed=0.f,ReloadTime=0.f,FireRippleTime=-1.f;
    double PreviousShot=-1.;
    TWeakObjectPtr<USkeletalMesh> SourceMesh;
    TArray<int32> Bones[2];
    TArray<FTransform> LastInput[2],LastOutput[2];
    FPKMSoftChain Chains[2];
};
