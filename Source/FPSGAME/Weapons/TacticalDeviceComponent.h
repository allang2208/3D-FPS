#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "TacticalDeviceComponent.generated.h"

UCLASS()
class FPSGAME_API UTacticalDeviceComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTacticalDeviceComponent();
    void Configure(const FString& Family,const FString& Variant,class USkeletalMeshComponent* Rifle,bool Enabled);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    FString Kind,AssetPath;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Body;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Dot;
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> Beam;
    UPROPERTY(Transient) TObjectPtr<class USpotLightComponent> Light;
    UPROPERTY(Transient) TObjectPtr<class USkeletalMeshComponent> Host;
    void HideEffects();
};
