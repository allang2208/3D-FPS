#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "BeiweiSwordTrailComponent.generated.h"

enum class ESwordTrailPalette : uint8 { Gold, Crimson, Cyan };

/** A short-lived, world-space ribbon through the rendered blade's actual path. */
UCLASS()
class FPSGAME_API UBeiweiSwordTrailComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UBeiweiSwordTrailComponent();
    void SetView(bool OwnerOnly,bool HideFromOwner);
    void Feed(const FVector& Base,const FVector& Tip,bool Emitting,ESwordTrailPalette Palette=ESwordTrailPalette::Gold);
    void Clear();
    virtual void BeginPlay() override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    struct FSample {FVector Base,Tip;double Time;bool Start;};
    TArray<FSample> Samples;
    FVector Origin=FVector::ZeroVector;
    bool bContinuous=false,bOwnerOnly=false,bHideOwner=false;
    ESwordTrailPalette ActivePalette=ESwordTrailPalette::Gold;
    class UMaterialInterface* TrailMaterial() const;
    UPROPERTY(Transient) TObjectPtr<class UDynamicMeshComponent> Ribbon;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> Material;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> CrimsonMaterial;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> CyanMaterial;
    TSharedPtr<struct FStreamableHandle> MaterialLoad;
};
