#pragma once
#include "Commandlets/Commandlet.h"
#include "GameFramework/Character.h"
#include "HeQueAuditCommandlet.generated.h"

/** Minimal transient physics fixture: no player profile, map, UI or BeginPlay. */
UCLASS(NotBlueprintable,Transient)
class AHeQueAuditPawn : public ACharacter
{
    GENERATED_BODY()
public:
    AHeQueAuditPawn(const FObjectInitializer& Init=FObjectInitializer::Get());
};

UCLASS()
class UHeQueAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
