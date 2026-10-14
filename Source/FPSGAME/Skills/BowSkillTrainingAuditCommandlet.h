#pragma once
#include "Commandlets/Commandlet.h"
#include "GameFramework/PlayerController.h"
#include "BowSkillTrainingAuditCommandlet.generated.h"

// Authority-side remote owner without opening a socket or starting a game map.
UCLASS()
class ABowSkillAuditRemoteController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual bool IsLocalController() const override { return false; }
};

UCLASS()
class UBowSkillTrainingAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
