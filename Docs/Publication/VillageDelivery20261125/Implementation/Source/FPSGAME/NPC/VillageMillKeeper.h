#pragma once

#include "GameFramework/Character.h"
#include "ResidentConversation.h"
#include "VillageMillKeeper.generated.h"

UCLASS()
class FPSGAME_API AVillageMillKeeper : public ACharacter
{
    GENERATED_BODY()

public:
    void SetLocalConversation(APlayerController* Player);

protected:
    virtual void BeginPlay() override;

private:
    FResidentConversationFacing Facing;
};
