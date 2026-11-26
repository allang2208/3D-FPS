#pragma once
#include "Commandlets/Commandlet.h"
#include "SurvivalClockAuditCommandlet.generated.h"
/** Opt-in calendar/consumption checks with separate UserDir and profile. */
UCLASS()
class USurvivalClockAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
