#pragma once
#include "CoreMinimal.h"

// Value-only contacts in the holding BODY hand's frame. The complete source
// animation still supplies the shoulder/elbow performance and the free hand.
struct FFPSBodySinglePistolContact
{
    FTransform Ready=FTransform::Identity;
    FTransform Operation=FTransform::Identity;
    float OperationWeight=0.f;
    float MagazineStroke=0.f;
    bool bReady=false;
};
