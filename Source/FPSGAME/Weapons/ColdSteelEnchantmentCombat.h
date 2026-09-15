#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ColdSteelEnchantmentCombat.generated.h"

struct FColdSteelShotEffects {int32 Piercing=0,Poison=0;};
struct FColdSteelItem;
namespace ColdSteelCombat
{
    FPSGAME_API FColdSteelShotEffects Snapshot(AActor* Shooter,const FColdSteelItem* Item=nullptr);
    FPSGAME_API void OnHit(AActor* Target,AActor* Shooter,int32 Poison);
}
/** Target-owned poison; one damage per stack per second, one stack fades every five seconds; no dependence on later weapon swaps. */
UCLASS()
class FPSGAME_API UColdSteelPoisonComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    void AddStacks(AActor* Source,int32 Amount);
    int32 GetStacks()const{return Stacks;}
    void Pulse();
protected:
    virtual void EndPlay(const EEndPlayReason::Type)override;
private:
    int32 Stacks=0,TicksLeft=0;
    TWeakObjectPtr<AActor> Shooter;
    TWeakObjectPtr<AController> Instigator;
    FTimerHandle Timer;
};
