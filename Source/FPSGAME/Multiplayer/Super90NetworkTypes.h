#pragma once
#include "CoreMinimal.h"
#include "Super90NetworkTypes.generated.h"

class APawn;

USTRUCT()
struct FSuper90NetMagazine
{
    GENERATED_BODY()
    UPROPERTY() FString Instance;
    UPROPERTY() FString Ammo;
    UPROPERTY() int32 Count=0;
    UPROPERTY() int32 Virtual=0;
    UPROPERTY() bool NeedsCycle=false;
};
USTRUCT()
struct FSuper90NetAmmoState
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<APawn> SourcePawn=nullptr;
    UPROPERTY() int64 InventoryRevision=0;
    UPROPERTY() TArray<int64> PouchCounts;
    UPROPERTY() uint32 Acknowledged=0;
    UPROPERTY() uint32 Revision=0;
    UPROPERTY() TArray<FSuper90NetMagazine> Magazines;
    // Cumulative server pouch mutations, not absolute client inventory. This
    // rebases concurrent legitimate crafting/pickup and old profile uploads.
    UPROPERTY() TArray<int64> PouchDelta;
    UPROPERTY() bool Reloading=false;
    UPROPERTY() bool Rejected=false;
    UPROPERTY() FString ReloadWeapon;
    UPROPERTY() int32 ReloadCount=0;
    UPROPERTY() float ReloadRate=1.f;
    UPROPERTY() bool ReloadEmpty=false;
    UPROPERTY() bool ReloadLoader=false;
    UPROPERTY() bool ReloadCycleOnly=false;
    UPROPERTY() bool ReloadStopRequested=false;
};
struct FSuper90ServerReload
{
    TWeakObjectPtr<APawn> Pawn;
    FString Weapon,Ammo;
    double Started=0;
    float Rate=1.f,Length=0.f,Duration=0.f,Tail=0.f;
    int32 Count=0,Committed=0;
    bool Active=false,Loader=false,Empty=false,CycleOnly=false,StopRequested=false;
};
struct FSuper90PredictedShot
{
    uint32 Sequence=0;
    FString Weapon;
    int32 Rounds=1;
};
