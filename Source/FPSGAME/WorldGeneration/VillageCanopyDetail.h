#pragma once

#include "Components/ActorComponent.h"
#include "VillagePresentationView.h"
#include "VillageCanopyDetail.generated.h"

class ATemperateHillsWorld;
class UPCGComponent;
class UPrimitiveComponent;

UCLASS()
class UVillageCanopyDetail : public UActorComponent
{
    GENERATED_BODY()
public:
    UVillageCanopyDetail();
    static UVillageCanopyDetail* For(ATemperateHillsWorld& Hills);
    void SetForest(UPCGComponent* TreeLayer);
    void AddTree(UPrimitiveComponent* Tree);
    void WatchForestCell(UPCGComponent* Cell);
    void RemoveTree(UPrimitiveComponent* Tree);
protected:
    virtual void TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    struct FTreeDetail
    {
        TWeakObjectPtr<UPrimitiveComponent> Tree;
        float NormalScale = 1.f;
        bool bReduced = false;
        void Apply(bool bReduce);
    };
    TWeakObjectPtr<UPCGComponent> Forest;
    using FTreeKey = TWeakObjectPtr<UPrimitiveComponent>;
    using FCellKey = TWeakObjectPtr<UPCGComponent>;
    TMap<FTreeKey, FTreeDetail> Trees;
    TMap<FCellKey, TSet<FTreeKey>> CellTrees;
    TSet<FCellKey> PendingCells;
    VillagePresentationView::FCanopyView PreviousView;
    double NextMovingUpdate = 0.;
    bool bTreesChanged = true;
    bool bPendingView = true;
    bool bDiscoverExisting = false;
    void QueueCell(UPCGComponent* Cell);
    void ReleaseCell(UPCGComponent* Cell);
    void ReleaseForest();
    void RefreshCells();
    void ForgetTree(FTreeKey Tree);
};
