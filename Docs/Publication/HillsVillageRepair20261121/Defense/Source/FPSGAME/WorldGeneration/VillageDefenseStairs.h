#pragma once

#include "VillageDefenseSection.h"
#include "VillageDefenseStairs.generated.h"

/** A switchback and its landings share a single generated or player-built defense ledger entry. */
UCLASS()
class FPSGAME_API AVillageDefenseStairs : public AVillageDefenseSection
{
    GENERATED_BODY()
public:
    static const FSoftObjectPath& StairMeshPath();
    bool IsPlayerBuilt() const {return PlacedId.IsValid();}
    virtual FVector TargetPoint(const FVector& From) const override;
    /** Local boxes of the authored treads and landings, also available after collision is disabled. */
    void GetRepairBounds(TArray<FBox>& OutBounds) const;
protected:
    virtual void PostInitializeComponents() override;
    virtual void Destroyed() override;
    virtual bool IsRepairSiteClear() const override;
    virtual void PresentCollapse(const FVector& Direction,int32 Seed,float LiftCm) override;
};
