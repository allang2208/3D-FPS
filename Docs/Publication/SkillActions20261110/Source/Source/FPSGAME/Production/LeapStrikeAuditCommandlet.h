#pragma once
#include "Commandlets/Commandlet.h"
#include "LeapStrikeAuditCommandlet.generated.h"

/** Explicit leap review; isolated profile, native movement/camera/final arm poses. */
UCLASS()
class ULeapStrikeAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
