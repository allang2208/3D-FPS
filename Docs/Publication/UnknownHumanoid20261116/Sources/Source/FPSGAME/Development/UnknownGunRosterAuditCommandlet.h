#pragma once
#include "Commandlets/Commandlet.h"
#include "UnknownGunRosterAuditCommandlet.generated.h"

UCLASS()
class UUnknownGunRosterAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
