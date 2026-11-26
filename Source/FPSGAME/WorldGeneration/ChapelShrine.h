#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "ChapelShrine.generated.h"

struct FStreamableHandle;
class UStaticMeshComponent;

/** One replicated shrine per hills world, sharing the dungeon's choice and blessing logic. */
UCLASS()
class FPSGAME_API AChapelShrine : public APawn
{
    GENERATED_BODY()
public:
    AChapelShrine();
    static void AddAssetPaths(TArray<FSoftObjectPath>& Paths);
    UStaticMeshComponent* GetStatueComponent() const { return Statue; }
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(ReplicatedUsing=OnRep_Identity) int32 WorldSeed=0;
    UPROPERTY(ReplicatedUsing=OnRep_Identity) FGuid WorldId;
    UPROPERTY(ReplicatedUsing=OnRep_Ward) float Durability=1800.f;
    UPROPERTY(Replicated) float MaxDurability=1800.f;
    UPROPERTY(Replicated) bool bRaidNight=false;
    bool IsDormant() const { return Durability<=0.f; }
    bool CanBeSieged() const { return bRaidNight&&!IsDormant(); }
    void SetRaidNight(bool Night,float Maximum);
    void RestoreWard(float Health,float Maximum,bool Night);
    virtual FVector GetNavAgentLocation() const override;
    /** Actual near surface of the shrine's blocking pedestal, shared by raid travel and melee. */
    FVector GetRaidTargetPoint(const FVector& From) const;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> Statue;
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> RaidPedestal;
    UPROPERTY() TObjectPtr<class UCapsuleComponent> Body;
    UFUNCTION() void OnRep_Identity();
    UFUNCTION() void OnRep_Ward();
    void BindShrine();
    void ArrangePresentation();
    TSharedPtr<FStreamableHandle> MeshLoad;
    bool bBound=false;
};
