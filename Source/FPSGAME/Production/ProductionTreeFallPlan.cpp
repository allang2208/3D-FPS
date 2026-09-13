#include "ProductionTreeFallPlan.h"
#include "ProductionResource.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/SkeletalMesh.h"

FProductionTreeFallPlan FProductionTreeFallPlan::Make(const FProductionResource& Resource)
{
    FProductionTreeFallPlan Plan;
    Plan.Direction=Resource.Direction.GetSafeNormal2D();
    if(Plan.Direction.IsNearlyZero())Plan.Direction=FVector::ForwardVector;
    Plan.Axis=FVector::CrossProduct(FVector::UpVector,Plan.Direction);
    Plan.Pivot=Resource.Transform.TransformPosition(FVector(0,0,CutHeight));
    auto* Mesh=Cast<USkeletalMesh>(Resource.Mesh.ResolveObject());
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
            const float Radius=Crown?FMath::Clamp(Height*.045f,65.f,160.f):18.f*Scale;
            const FVector Sample=Plan.Pivot+Rotation.RotateVector(FVector::UpVector*Height*Fraction);
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
