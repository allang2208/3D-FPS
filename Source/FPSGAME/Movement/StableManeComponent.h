#pragma once
#include "Components/SkeletalMeshComponent.h"
#include "StableManeComponent.generated.h"

UCLASS()
class FPSGAME_API UStableManeComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    UStableManeComponent();
    void UpdateMotion(float Dt);
    void SetHairStyle(uint8 Style);
    UPROPERTY(EditAnywhere, Category="Mane Physics",meta=(ClampMin="0.5",ClampMax="10.0")) float FrequencyHz=3.2f;
    UPROPERTY(EditAnywhere, Category="Mane Physics",meta=(ClampMin="0.1",ClampMax="2.0")) float DampingRatio=.72f;
    UPROPERTY(EditAnywhere, Category="Mane Physics",meta=(ClampMin="0.0")) float AirDrag=.0065f;
    UPROPERTY(EditAnywhere, Category="Mane Physics",meta=(ClampMin="0.0")) float MaximumTipTravelCm=5.5f;
protected:
    void BeginPlay() override;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> HairMaterial;
    UPROPERTY() TArray<TObjectPtr<USkeletalMesh>> Styles;
    TWeakObjectPtr<class AFPSWeatherManager> Weather;
    double NextWeatherLookup=0.;
    FVector Offset=FVector::ZeroVector,Velocity=FVector::ZeroVector,LastRoot=FVector::ZeroVector;
    bool bSampled=false;
};
