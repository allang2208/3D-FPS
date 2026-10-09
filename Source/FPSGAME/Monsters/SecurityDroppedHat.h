#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SecurityDroppedHat.generated.h"

class UStaticMesh;
class UStaticMeshComponent;

/** One physical hat, independent of the guard's corpse lifetime. */
UCLASS(NotBlueprintable)
class FPSGAME_API ASecurityDroppedHat : public AActor
{
    GENERATED_BODY()
public:
    ASecurityDroppedHat();
    void SetHatMesh(UStaticMesh* Mesh);
    void Launch(const FVector& IncomingDirection, const FVector& HitLocation, const FVector& InheritedVelocity);
protected:
    virtual void BeginPlay() override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> HatBody;
    UPROPERTY(ReplicatedUsing=OnRep_HatMesh) TObjectPtr<UStaticMesh> HatMesh;
    UFUNCTION() void OnRep_HatMesh();
    void ConfigureBody();
};
