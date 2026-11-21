#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "Subsystems/WorldSubsystem.h"
#include "VillageDefenseState.generated.h"

class APawn;

/** Stored before touching the wallet. The profile receipt decides whether to replay the repair. */
USTRUCT()
struct FVillagePendingRepair
{
    GENERATED_BODY()
    UPROPERTY() int32 Section=INDEX_NONE;
    UPROPERTY() FGuid PlacedId;
    UPROPERTY() FString PlayerSlot;
    UPROPERTY() int64 ProfileRevision=0;
    UPROPERTY() bool bGuest=false;
};

UCLASS()
class UVillageDefenseSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FGuid WorldId;
    UPROPERTY() int32 Version=1;
    UPROPERTY() FGuid Generation;
    UPROPERTY() TMap<int32,float> DamagedSections;
    UPROPERTY() TMap<FGuid,float> DamagedPlacedSections;
    UPROPERTY() FVillagePendingRepair PendingRepair;
};

UCLASS()
class UVillageDefenseState : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    void SelectGeneration(const FGuid& Id,const FGuid& Generation);
    float Restore(const FGuid& Id,int32 Section,float Default,const FGuid& PlacedId={});
    void Record(const FGuid& Id,int32 Section,float Health,const FGuid& PlacedId={});
    bool PurchaseRepair(const FGuid& Id,int32 Section,APawn* Payer,int32 Cost,FText& Failure,const FGuid& PlacedId={});
    void ForgetPlaced(const FGuid& Id,const TSet<FGuid>& Removed);
    void Flush();
    virtual void Deinitialize() override;
private:
    UVillageDefenseSave* Load(const FGuid& Id);
    void RecoverRepair(UVillageDefenseSave& Save);
    bool WriteNow(UVillageDefenseSave& Save);
    bool bPurchasing=false;
    UPROPERTY() TMap<FGuid,TObjectPtr<UVillageDefenseSave>> Saves;
    TSet<FGuid> Dirty;
    FTimerHandle SaveTimer;
};
