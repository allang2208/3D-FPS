#pragma once
#include "Commandlets/Commandlet.h"
#include "MonsterNetworkHitAuditCommandlet.generated.h"

UCLASS()
class UMonsterNetworkHitAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
