#pragma once

#include "GameFramework/Actor.h"
#include "ResidentConversation.h"
#include "VillageMasterArtisan.generated.h"

class USkeletalMeshComponent;

UCLASS(meta=(DisplayName="工匠大师"))
class FPSGAME_API AVillageMasterArtisan : public AActor
{
    GENERATED_BODY()
public:
    AVillageMasterArtisan();
    void SetLocalConversation(APlayerController* Player) { Facing.SetLocalPlayer(Player); }
    class ATemperateHillsWorld* Village() const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Head;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Workwear;
    FResidentConversationFacing Facing;
    FTimerHandle DressTimer;
    void Dress();
};
