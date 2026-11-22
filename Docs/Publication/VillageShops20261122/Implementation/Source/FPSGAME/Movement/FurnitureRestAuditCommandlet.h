#pragma once
#include "Commandlets/Commandlet.h"
#include "GameFramework/PlayerController.h"
#include "../FPSGAMECharacter.h"
#include "FurnitureRestAuditCommandlet.generated.h"

UCLASS(Transient, NotBlueprintable)
class AFurnitureRestAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual bool IsLocalController() const override { return false; }
    virtual void GetPlayerViewPoint(FVector& Location, FRotator& Rotation) const override
    { Location=FVector(100000,100000,100000); Rotation=FRotator::ZeroRotator; }
};

/** Real character components, without unrelated viewmodel/equipment startup. */
UCLASS(Transient, NotBlueprintable)
class AFurnitureRestAuditPawn : public AFPSGAMECharacter
{
    GENERATED_BODY()
protected:
    virtual void BeginPlay() override { ACharacter::BeginPlay(); SetActorTickEnabled(false); }
};

/** Isolated authority checks. This does not claim real client RPC or visual coverage. */
UCLASS()
class UFurnitureRestAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
