#pragma once
#include "CoreMinimal.h"
// Generated from the authored mesh contact surfaces by RefinementV4/author_layout.py.
namespace AlchemyLayout
{
inline constexpr float PrepTop=94.43000000f;
inline constexpr float StirPickupSeconds=.6f;
inline const FVector StirrerRest(148.00000000,-29.00000000,97.43000000);
inline const FVector LadleRest(148.00000000,-60.00000000,98.62999981);
inline const FVector DoseRest(145.00000000,-45.00000000,99.43000000);
inline const FVector HourglassRest(164.00000000,-45.00000000,94.77999999);
inline const FQuat ToolRestRotation=FRotator(90,0,0).Quaternion();
inline const FVector Book(118,-45,PrepTop);
inline const FVector Cauldron(225,-106,119.05);
inline const FVector Mortar(45,-50,100);
}
