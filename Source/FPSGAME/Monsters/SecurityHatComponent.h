#pragma once

#include "CoreMinimal.h"
#include "Components/StaticMeshComponent.h"
#include "SecurityHatComponent.generated.h"

class UDamageType;

/** Opt-in guard accessory. Point damage owns the one-time detach event. */
UCLASS(ClassGroup=(Monster), meta=(BlueprintSpawnableComponent))
class FPSGAME_API USecurityHatComponent : public UStaticMeshComponent
{
    GENERATED_BODY()
public:
    USecurityHatComponent();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Security|Hat") FName HeadBone = TEXT("head");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Security|Hat") FTransform HeadAttachmentTransform;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Dropped) bool bDropped = false;
    UFUNCTION() void OnRep_Dropped();
    UFUNCTION() void OnOwnerPointDamage(AActor* DamagedActor, float Damage, AController* InstigatedBy,
        FVector HitLocation, UPrimitiveComponent* HitComponent, FName BoneName, FVector ShotFromDirection,
        const UDamageType* DamageType, AActor* DamageCauser);
};
