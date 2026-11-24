#pragma once
#include "CoreMinimal.h"

class AActor;
class APlayerController;

/** One accepted player damage receipt, before HUD pooling/merging. */
struct FColdSteelDamageNumberEvent
{
    TWeakObjectPtr<AActor> Target;
    TWeakObjectPtr<APlayerController> Viewer;
    FVector WorldPoint=FVector::ZeroVector;
    float Physical=0.f,Magic=0.f;
    bool bCritical=false;
    bool bKilled=false;
    bool bBig=false;
    /** Monster hits follow the mesh top every frame; practice-target hits use WorldPoint. */
    bool bTrackTarget=false;
};
