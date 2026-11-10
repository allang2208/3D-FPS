#pragma once
#include "Commandlets/Commandlet.h"
#include "EnhancementEscrowAuditCommandlet.generated.h"
class UColdSteelStatusModel;
/** Explicit isolated escrow/authority regression. Not a UDP or visual audit. */
UCLASS()
class UEnhancementEscrowAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    static void Run(UColdSteelStatusModel* Model,bool LoadOnly,TFunctionRef<void(bool,const TCHAR*)> Check);
};
