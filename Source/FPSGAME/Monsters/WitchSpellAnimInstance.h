#pragma once
#include "CoreMinimal.h"
#include "FatZombieAnimInstance.h"
#include "WitchSpellAnimInstance.generated.h"

/** Witch spell presentation; the existing combat clock still owns both releases. */
UCLASS(Transient)
class FPSGAME_API UWitchSpellAnimInstance : public UFatZombieAnimInstance
{
    GENERATED_BODY()
public:
    void PlayState(UAnimSequence* Clip, bool bLoop);
    uint32 SpellGeneration = 0;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
