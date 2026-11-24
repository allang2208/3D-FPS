#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelDamageNumberTypes.h"
#include "ColdSteelDamageNumberSubsystem.generated.h"

/** Transient bus between combat receipts and the local HUD damage-number layer. */
UCLASS()
class FPSGAME_API UColdSteelDamageNumberSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    /** Queue one accepted player hit. Only the selected viewer's HUD consumes it. */
    void PushDamageNumber(AActor* Target,APlayerController* Viewer,const FVector& WorldPoint,float Damage,bool bCritical,bool bKilled,bool bBig,bool bTrackTarget,float MagicDamage);
    /** Top-centre of the visible character mesh (falls back to all component bounds). */
    static FVector TargetTopAnchor(const AActor* Target);
    /** Drain pending receipts. Returns false when the queue was empty. */
    bool ConsumeDamageNumbers(TArray<FColdSteelDamageNumberEvent>& Out);
    void Reset();
private:
    static constexpr int32 MaxPending=128;
    TArray<FColdSteelDamageNumberEvent> Pending;
};
