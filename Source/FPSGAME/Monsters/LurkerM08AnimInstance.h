#pragma once
#include "QuadrupedAnimationTemplate.h"
#include "LurkerM08AnimInstance.generated.h"

/** Uses the shared combat clock with M08's contact-driven surface locomotion. */
UCLASS(Transient, Blueprintable)
class FPSGAME_API ULurkerM08AnimInstance : public UQuadrupedTemplateAnimInstance
{
    GENERATED_BODY()
};
