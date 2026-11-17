#pragma once

#include "CoreMinimal.h"
#include "Engine/AssetUserData.h"
#include "ColdSteelHubMapRegistration.generated.h"

/** The north-up photo and its absolute world footprint are serialized in the same texture package. */
UCLASS()
class UColdSteelHubMapRegistration : public UAssetUserData
{
    GENERATED_BODY()
public:
    static constexpr const TCHAR* TexturePath=TEXT("/Game/ColdSteelUI/WorldMap/T_GodSpaceOrtho.T_GodSpaceOrtho");
    UPROPERTY() FVector2D CenterCm=FVector2D::ZeroVector;
    UPROPERTY() double WidthCm=0.;
};
