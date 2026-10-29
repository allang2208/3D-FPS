#pragma once
#include "Commandlets/Commandlet.h"
#include "KukriNetworkAuditCommandlet.generated.h"

UCLASS()
class UKukriNetworkAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    void CheckRunes(class AColdSteelPlayerState* PS,class AFPSGAMECharacter* Pawn,TFunctionRef<void(bool,const TCHAR*)> Check);
};
