#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ProductionHarvestSubsystem.generated.h"

struct FStreamableHandle;
struct FProductionResource;
struct FTemperatePlacement;
class AColdSteelPickup;
class AProductionBreakEffect;
class ATemperateHillsWorld;
struct FProductionTreeGrowthPresentation;

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
    /** 树桩被劈开（2026-09-28）：标记树桩表脏，让下一次刷新收走渲染与碰撞；不动幼树。 */
    void InvalidateStumps(const FProductionResource& Resource);
private:
    TSharedPtr<FStreamableHandle> WoodLoad,StoneLoad;
    TSharedPtr<FStreamableHandle> FallLoads[4];
    TMap<FString,TWeakObjectPtr<AColdSteelPickup>> Pickups;
    TMap<FString,double> VisibleAfter;
    TArray<TWeakObjectPtr<AProductionBreakEffect>> Effects;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    UPROPERTY(Transient) TArray<TObjectPtr<class UInstancedStaticMeshComponent>> Stumps;
    /** 树桩隐形碰撞盒（组件带 HarvestStump 标签；ResolveProductionResource 据此解析成可劈的桩）。 */
    UPROPERTY(Transient) TObjectPtr<class UInstancedStaticMeshComponent> StumpTrunks;
    FIntPoint StumpCell=FIntPoint(MAX_int32,MAX_int32);
    bool bStumpsDirty=true;
    double NextStumpRefresh=0;
    void UpdateStumps(const FVector& Eye,double Now);
    /** 树桩隐形碰撞盒重建（与树桩渲染同表同节拍）。 */
    void UpdateStumpTrunks(const TArray<FTemperatePlacement>& Places);
    void UpdateGrowingTrees(const FVector& Eye,double Now);
    void RemoveGrowingTree(uint64 Candidate);
    void ClearGrowingTrees();
    TSharedPtr<FProductionTreeGrowthPresentation> GrowingTrees;
    UPROPERTY(Transient) TArray<TObjectPtr<class UInstancedSkinnedMeshComponent>> GrowthMeshes;
    UPROPERTY(Transient) TObjectPtr<class UInstancedStaticMeshComponent> GrowthTrunks;
    float ScanCountdown=0;
};
