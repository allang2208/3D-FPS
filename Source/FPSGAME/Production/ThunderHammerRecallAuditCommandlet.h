#pragma once
#include "Commandlets/Commandlet.h"
#include "GameFramework/PlayerController.h"
#include "ThunderHammerRecallAuditCommandlet.generated.h"

UCLASS(Transient,NotBlueprintable)
class AThunderRecallAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual bool IsLocalController() const override {return true;}
};

/** Explicitly invoked, isolated recall/action fixture. Never loads a player's save. */
UCLASS()
class UThunderHammerRecallAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
