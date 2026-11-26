#include "TemperateForestAuthoringLibrary.h"
#include "TemperateHillsVisibility.h"
#if WITH_EDITOR
#include "Materials/MaterialExpressionGetMaterialAttributes.h"
#include "Materials/MaterialExpressionSetMaterialAttributes.h"
#endif

int32 UTemperateForestAuthoringLibrary::AddWindOffsetPin(UObject* Expression)
{
#if WITH_EDITOR
    if(Expression&&(Expression->GetPathName().StartsWith(TEXT("/Game/WorldGeneration/TemperateHills/"))||
        Expression->GetPathName().StartsWith(TEXT("/Game/Items/HarvestTimber/Beech/M_FallingBeech."))))
    {
        if(auto* Attributes=Cast<UMaterialExpressionGetMaterialAttributes>(Expression))
            return Attributes->CreateOrGetOutputAttribute(MP_WorldPositionOffset);
        if(auto* Attributes=Cast<UMaterialExpressionSetMaterialAttributes>(Expression))
            return Attributes->CreateOrGetInputAttribute(MP_WorldPositionOffset);
    }
#endif
    return INDEX_NONE;
}

int32 UTemperateForestAuthoringLibrary::AddVisibilityMaskPin(UObject* Expression)
{
#if WITH_EDITOR
    // The beech harvest wrapper also reads the standing-tree opacity mask.
    // Rejecting it returns INDEX_NONE, which Python can silently use as [-1].
    if(Expression&&(Expression->GetPathName().StartsWith(TEXT("/Game/WorldGeneration/TemperateHills/"))||
        Expression->GetPathName().StartsWith(TEXT("/Game/Items/HarvestTimber/Beech/M_FallingBeech."))))
    {
        if(auto* Attributes=Cast<UMaterialExpressionGetMaterialAttributes>(Expression))
            return Attributes->CreateOrGetOutputAttribute(MP_OpacityMask);
        if(auto* Attributes=Cast<UMaterialExpressionSetMaterialAttributes>(Expression))
            return Attributes->CreateOrGetInputAttribute(MP_OpacityMask);
    }
#endif
    return INDEX_NONE;
}

int32 UTemperateForestAuthoringLibrary::AddSurfaceBlendPin(UObject* Expression,int32 Channel)
{
#if WITH_EDITOR
    const EMaterialProperty Properties[]={MP_BaseColor,MP_Normal,MP_Roughness};
    if(Expression&&Channel>=0&&Channel<3&&Expression->GetPathName().StartsWith(TEXT("/Game/WorldGeneration/TemperateHills/EcologyUpgrade/")))
    {
        if(auto* Attributes=Cast<UMaterialExpressionGetMaterialAttributes>(Expression))return Attributes->CreateOrGetOutputAttribute(Properties[Channel]);
        if(auto* Attributes=Cast<UMaterialExpressionSetMaterialAttributes>(Expression))return Attributes->CreateOrGetInputAttribute(Properties[Channel]);
    }
#endif
    return INDEX_NONE;
}

FVector UTemperateForestAuthoringLibrary::GetVisibilityDistances(int32 Layer)
{
    if(Layer<0||Layer>=UE_ARRAY_COUNT(TemperateHillsVisibility::Layers))return FVector::ZeroVector;
    const auto& Distances=TemperateHillsVisibility::Layers[Layer];
    return FVector(Distances.FadeStart,Distances.VisibleEnd,Distances.GenerateRadius);
}
