#pragma once
#include "CoreMinimal.h"
#include "PistolNetworkTypes.generated.h"

class APawn;

USTRUCT()
struct FPistolNetMagazine
{
    GENERATED_BODY()
    UPROPERTY() FString Instance;
    UPROPERTY() FString Ammo;
    UPROPERTY() int32 Rounds=0;
    UPROPERTY() int32 VirtualRounds=0;
    UPROPERTY() int32 Cases=0;
    UPROPERTY() bool NeedsCycle=false;
    UPROPERTY() bool EmptyCycle=true;
};

USTRUCT()
struct FPistolNetPouch
{
    GENERATED_BODY()
    UPROPERTY() FString Ammo;
    UPROPERTY() int64 Count=0;
    UPROPERTY() int64 Delta=0;
};

USTRUCT()
struct FPistolNetReload
{
    GENERATED_BODY()
    UPROPERTY() FString Instance;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() bool Active=false;
    UPROPERTY() bool Rejected=false;
};

USTRUCT()
struct FPistolNetAmmoState
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<APawn> Pawn=nullptr;
    UPROPERTY() uint32 Revision=0;
    UPROPERTY() uint32 AmmoRevision=0;
    UPROPERTY() uint32 AcknowledgedShot=0;
    UPROPERTY() int64 InventoryRevision=0;
    UPROPERTY() TArray<FPistolNetMagazine> Magazines;
    UPROPERTY() TArray<FPistolNetPouch> Pouch;
    UPROPERTY() TArray<FPistolNetReload> Reloads;
    UPROPERTY() bool Cowboy=false;
};

// Runtime-only plans. Only the committed magazine/pouch/cycle state is saved.
struct FPistolServerReload
{
    TWeakObjectPtr<APawn> Pawn;
    FString Instance,Ammo;
    uint32 Serial=0;
    int32 ActiveSlot=6,Side=0,Capacity=0,Count=0,Committed=0;
    double Started=0.;
    float EjectAt=0.f,ReadyAt=0.f,Duration=0.f;
    TArray<float> Seats;
    bool Active=false,Rejected=false,Revolver=false,Loader=false,Switching=false;
    bool CycleOnly=false,Empty=false,Cleared=false,Closed=false,DualExecutor=false;
};

struct FPistolPredictedShot
{
    uint32 Sequence=0;
    FString Instance;
    int32 Rounds=1;
};
