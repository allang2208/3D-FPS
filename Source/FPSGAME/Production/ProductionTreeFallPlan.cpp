#include "ProductionTreeFallPlan.h"
#include "ProductionResource.h"
#include "ProductionHarvestAssets.h"
#include "ProductionTreeCutProfile.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/SkeletalMesh.h"

FProductionTreeFallPlan FProductionTreeFallPlan::Make(const FProductionResource& Resource)
{
    FProductionTreeFallPlan Plan;
    Plan.Direction=Resource.Direction.GetSafeNormal2D();
    if(Plan.Direction.IsNearlyZero())Plan.Direction=FVector::ForwardVector;
    Plan.Axis=FVector::CrossProduct(FVector::UpVector,Plan.Direction);
    const int32 Variant=ProductionHarvestAssets::TreeVariant(Resource.Mesh);
    float TrunkRadius=18.f;
    if(auto* Profile=Cast<UProductionTreeCutProfile>(ProductionHarvestAssets::CutProfile(Variant).ResolveObject()))
    {
        const FVector LocalDirection=Resource.Transform.InverseTransformVectorNoScale(Plan.Direction);
        float Support=-TNumericLimits<float>::Max();
        for(const FVector2D& Point:Profile->Rim)
        {
            TrunkRadius=FMath::Max(TrunkRadius,float(Point.Size()));
            const float Projection=Point.X*LocalDirection.X+Point.Y*LocalDirection.Y;
            if(Projection>Support){Support=Projection;Plan.LocalHinge=FVector(Point.X,Point.Y,CutHeight);}
        }
    }
    Plan.Pivot=Resource.Transform.TransformPosition(Plan.LocalHinge);
    auto* Mesh=Cast<USkeletalMesh>(ProductionHarvestAssets::FallingMesh(Variant).ResolveObject());
    if(Mesh)Plan.LocalHeight=FMath::Max(300.f,float(Mesh->GetBounds().Origin.Z+Mesh->GetBounds().BoxExtent.Z));
    const float Scale=Resource.Transform.GetScale3D().Z;
    const float Height=(Plan.LocalHeight-CutHeight)*Scale;
    Plan.FallSeconds=FMath::Clamp(1.3f+.25f*FMath::Sqrt(Height/100.f),1.8f,3.f);
    auto* World=Resource.World.Get();if(!World)return Plan;
    // Refine first crown contact and final trunk support separately, once per fall.
    auto Contact=[&](float Degrees,bool Crown,FVector& Point)
    {
        const FQuat Rotation(Plan.Axis,FMath::DegreesToRadians(Degrees));
        float Lowest=TNumericLimits<float>::Max();
        for(float Fraction:{.14f,.32f,.52f,.72f,.92f})
        {
            if(Crown&&Fraction<.7f)continue;
            const float Radius=Crown?FMath::Clamp(Height*.045f,65.f,160.f):TrunkRadius*Scale*FMath::Lerp(1.f,.3f,Fraction);
            const FVector LocalSample=FVector(0,0,CutHeight+(Plan.LocalHeight-CutHeight)*Fraction);
            const FVector Offset=Resource.Transform.TransformVector(LocalSample-Plan.LocalHinge);
            const FVector Sample=Plan.Pivot+Rotation.RotateVector(Offset);
            const float Ground=World->Height(Sample.X,Sample.Y);
            const float Gap=Sample.Z-Ground-Radius;
            if(Gap<Lowest){Lowest=Gap;Point=FVector(Sample.X,Sample.Y,Ground+3);}
        }
        return Lowest<=0;
    };
    auto FirstContact=[&](bool Crown,FVector& Point)
    {
        for(float Degrees=8;Degrees<=112;Degrees+=4)
            if(Contact(Degrees,Crown,Point))
            {
                float Low=Degrees-4,High=Degrees;
                for(int32 Step=0;Step<5;++Step)
                {const float Mid=(Low+High)*.5f;if(Contact(Mid,Crown,Point))High=Mid;else Low=Mid;}
                Contact(High,Crown,Point);return Low;
            }
        Contact(112,Crown,Point);return 112.f;
    };
    Plan.LandingAngle=FirstContact(false,Plan.TrunkContact);
    Plan.CrownAngle=FMath::Min(Plan.LandingAngle,FirstContact(true,Plan.CrownContact));
    return Plan;
}
