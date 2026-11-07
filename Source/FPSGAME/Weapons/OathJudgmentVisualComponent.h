#pragma once
#include "Components/DynamicMeshComponent.h"
#include "HighlandOathRune.h"
#include "OathJudgmentVisualComponent.generated.h"

enum class EOathStroke : uint8 { None, Slash, Thrust };

UCLASS(Transient)
class FPSGAME_API UOathJudgmentVisualComponent : public UDynamicMeshComponent
{
    GENERATED_BODY()
public:
    UOathJudgmentVisualComponent();
    static UOathJudgmentVisualComponent* CreateFor(AActor* Owner,bool FirstPerson);
    void Present(class UMeshComponent* Blade,const FVector& Base,const FVector& Tip,
        const FHighlandOathPresentation& State,double Now,double ImpactAt,const FVector& ImpactPoint,EOathStroke Stroke);
    bool NeedsThrustEndpoint(const FHighlandOathPresentation& State) const
    {
        return State.Phase==2 && WakeReleaseAt!=State.ReleaseAt && PendingStroke.IsEmpty();
    }
    void Hide(bool DiscardWake=true);
protected:
    virtual void OnRegister() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> LightMaterial;
    UPROPERTY(Transient) TObjectPtr<class USoundBase> ImpactSound;
    TSharedPtr<struct FStreamableHandle> MaterialLoad;
    void UpdateWake(UMeshComponent* Blade,const FVector& Base,const FVector& Tip,
        const FHighlandOathPresentation& State,double Now,EOathStroke Stroke);
    UPROPERTY(Transient) TObjectPtr<class UBeiweiSwordTrailComponent> Wake;
    TWeakObjectPtr<UMeshComponent> PreviousBlade;
    FVector PreviousBase=FVector::ZeroVector,PreviousTip=FVector::ZeroVector,PreviousSide=FVector::ZeroVector;
    struct FWakeSlice { FVector Root,Edge; double At; };
    TArray<FWakeSlice,TInlineAllocator<24>> PendingStroke;
    EOathStroke LastStroke=EOathStroke::None;
    double PreviousPoseAt=-100.,WakeReleaseAt=-100.;
    double LastPresented=0.;
    double LastImpactSound=-100.;
};
