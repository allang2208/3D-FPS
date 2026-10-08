#pragma once
#include "CoreMinimal.h"
#include "Components/StaticMeshComponent.h"
#include "SwordTasselMeshComponent.generated.h"

class FJsonObject;
class UMaterialInstanceDynamic;

/** Bounded cosmetic chain; gameplay collision and damage remain on the sword. */
UCLASS()
class FPSGAME_API USwordTasselMeshComponent : public UStaticMeshComponent
{
    GENERATED_BODY()
public:
    USwordTasselMeshComponent();
    void Configure(const TSharedPtr<FJsonObject>& Spec);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    struct FCapsule { FVector A,B; double Radius; };
    TArray<FVector> Rest,Position,Velocity;
    TArray<double> Lengths,InverseMass;
    TArray<FCapsule> Capsules;
    FTransform PreviousFrame;
    bool bInitialized=false;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> DynamicMaterials;
    void Publish();
};
