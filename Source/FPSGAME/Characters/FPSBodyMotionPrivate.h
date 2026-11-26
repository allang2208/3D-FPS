#pragma once
#include "CoreMinimal.h"
#include "Components/PrimitiveComponent.h"
namespace FPSBodyMotionPrivate
{
inline FTransform BodyMotionRigidTransform(FTransform T){T.SetScale3D(FVector::OneVector);return T;}
inline bool Drawn(const UPrimitiveComponent* C){return C&&C->IsVisible()&&!C->bHiddenInGame;}
}
