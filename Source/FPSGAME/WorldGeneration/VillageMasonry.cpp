#include "VillageMasonry.h"
#include "Components/PrimitiveComponent.h"

void VillageMasonry::ApplyCurtainPhase(UPrimitiveComponent& Surface, const FTransform& IntactWallPose)
{
    // The curtain and keep map a two-metre fieldstone scan across each elevation.
    // Use the intact wall's frame: cut faces share this origin even after a shard moves.
    const FVector Origin=IntactWallPose.GetTranslation();
    const FVector Along=IntactWallPose.GetUnitAxis(EAxis::X);
    const FVector Scale=IntactWallPose.GetScale3D();
    const double U=FVector::DotProduct(Origin,Along)/(200. * FMath::Max(Scale.X,UE_SMALL_NUMBER));
    const double V=-Origin.Z/(200. * FMath::Max(Scale.Z,UE_SMALL_NUMBER));
    Surface.SetCustomPrimitiveDataFloat(8,float(U-FMath::FloorToDouble(U)));
    Surface.SetCustomPrimitiveDataFloat(9,float(V-FMath::FloorToDouble(V)));
}

void VillageMasonry::ApplyWallPhase(UPrimitiveComponent& Surface, int32 SectionId)
{
    FRandomStream Phase(SectionId);
    Surface.SetCustomPrimitiveDataFloat(8, Phase.FRand());
    Surface.SetCustomPrimitiveDataFloat(9, Phase.FRand());
}

