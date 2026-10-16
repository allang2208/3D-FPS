#pragma once
#include "CoreMinimal.h"

enum class EAlchemyTableObject : uint8 {None,Ingredient,Book,Mortar,Heater,Stirrer,Liquid,Hourglass,Bottle,Decoration};
struct FAlchemyTableHit
{
    EAlchemyTableObject Object=EAlchemyTableObject::None;
    int32 Ingredient=INDEX_NONE;
    FVector WorldPoint=FVector::ZeroVector;
};
namespace AlchemyTabletop
{
// Clear space on the ceramic preparation board, left of the physical manual.
inline const FVector Ingredients[]={FVector(70,-38,95.02),FVector(86,-38,95.02),FVector(79,-58,95.02)};
// Facing +Y, camera-left is bench-local +X (the cauldron side).
inline const FVector Eye(157,-185,186);
inline const FVector Aim(157,-55,103);
inline constexpr float FieldOfView=84.f;
}
