#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ProductionHarvestSubsystem.generated.h"

struct FStreamableHandle;
struct FProductionResource;
class AColdSteelPickup;
class AProductionBreakEffect;
class ATemperateHillsWorld;

/** Bounded local presentation of profile-owned, persistent harvest drops. */
UCLASS()
class UProductionHarvestSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;
    void Prepare(bool Wood);
    bool Ready(bool Wood) const;
    void PrepareFall(const FProductionResource& Resource);
    bool ReadyFall(const FProductionResource& Resource) const;
    void ReleasePreparedFall(const FProductionResource& Resource);
    void DelayDrops(const TArray<FString>& Ids,float Delay);
    void Burst(bool Wood,const FVector& At,uint32 Seed,bool Landing=false);
    void ShowStumpAtCut(const FProductionResource& Resource);
private:
    TSharedPtr<FStreamableHandle> WoodLoad,StoneLoad;
    TSharedPtr<FStreamableHandle> FallLoads[4];
    TMap<FString,TWeakObjectPtr<AColdSteelPickup>> Pickups;
    TMap<FString,double> VisibleAfter;
    TArray<TWeakObjectPtr<AProductionBreakEffect>> Effects;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    UPROPERTY(Transient) TArray<TObjectPtr<class UInstancedStaticMeshComponent>> Stumps;
    FIntPoint StumpCell=FIntPoint(MAX_int32,MAX_int32);
    bool bStumpsDirty=true;
    double NextStumpRefresh=0;
    void UpdateStumps(const FVector& Eye,double Now);
    float ScanCountdown=0;
};
