#pragma once
#include "CoreMinimal.h"
#include "SlagBlackMist.h"
#include "Engine/NetSerialization.h"
#include "M66BackMist.generated.h"

USTRUCT()
struct FM66SmokePuff
{
    GENERATED_BODY()
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double Born=-10000.;
    UPROPERTY() FVector_NetQuantize10 Origins[4];
    UPROPERTY() FVector_NetQuantize10 Drift;
    UPROPERTY() float Floors[4]{};
};

/** Four vent-born black plumes which settle, sharing Slag's in-smoke blindness. */
UCLASS()
class FPSGAME_API AM66BackMist : public ASlagBlackMist
{
    GENERATED_BODY()
public:
    AM66BackMist();
    virtual void BeginPlay() override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    const TArray<FM66SmokePuff>& SmokeHistory() const {return History;}
    UPROPERTY(EditDefaultsOnly,Category="M66|BackSmoke") TSoftObjectPtr<class UNiagaraSystem> DescendingSmoke;
protected:
    virtual void UpdateWake() override;
    virtual double WakeClock() const override;
    virtual bool ShouldEmit() const override;
    virtual void GetEmissionSources(FVector (&Origins)[4],FVector& Drift) const override;
    virtual int32 GetEmissionSourceCount() const override { return 4; }
    virtual float GetEmissionRate() const override { return 12.f; }
    virtual float GetDiffusionSpeed() const override { return 1.7f; }
    virtual float CoreRadiusFraction(float NormalizedAge) const override;
    virtual void CapturePuffFloors(const FVector (&Origins)[4],float (&Floors)[4]) const override;
    virtual FVector PuffCenter(const FVector& Origin,const FVector& Drift,float Age,float FloorZ) const override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_History) TArray<FM66SmokePuff> History;
    UPROPERTY(ReplicatedUsing=OnRep_History) FVector_NetQuantize10 HistoryOrigin;
    UFUNCTION() void OnRep_History();
    uint32 NextPuffSerial=0;
    bool bHistoryDirty=true;
};
