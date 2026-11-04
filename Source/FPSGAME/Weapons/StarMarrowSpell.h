#pragma once
#include "CoreMinimal.h"
class AActor;
struct FStarMarrowSpell
{
    bool bReleased=false;
    float HealthRatio=0,ManaRatio=0;
};
namespace StarMarrow
{
    // Material recovery only; Star Marrow no longer adds crystal damage to spells.
    FPSGAME_API void CaptureSpell(AActor* Owner,FStarMarrowSpell& Receipt);
    class FPSGAME_API FHitRecovery
    {
    public:
        FHitRecovery(AActor* Shooter,AActor* Victim,const FStarMarrowSpell& Receipt);
        void Finish(float Applied) const;
    private:
        AActor* Source=nullptr;
        AActor* Target=nullptr;
        float Before=0,HealthRatio=0,ManaRatio=0;
    };
}
