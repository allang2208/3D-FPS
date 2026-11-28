#include "VillageSiegeUseTargets.h"
#include "VillageSiegeEngine.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"

namespace
{
    // Dimensions are in each authored mesh's local centimetres. Separate the tall
    // frame from its chassis and moving pieces so aiming past a machine clears focus.
    struct FUseBox
    {
        FName Part;
        FVector Center;
        FVector Extent;
        FQuat Rotation = FQuat::Identity;
    };

    FUseBox Beam(FName Part, const FVector& A, const FVector& B, double HalfWidth, double HalfHeight)
    {
        const FVector Span = B - A;
        return {Part, (A+B)*.5, FVector(Span.Size()*.5+4.,HalfWidth,HalfHeight), Span.Rotation().Quaternion()};
    }

    TConstArrayView<FUseBox> UseBoxes(const AVillageSiegeEngine& Engine)
    {
        static const FUseBox BallistaBoxes[] = {
            {NAME_None, {-6,1,17}, {82,82,17}},
            {NAME_None, {-5,0,56}, {47,43,25}},
            {NAME_None, {0,0,98}, {23,23,36}},
            Beam(TEXT("Stock"), {-163,0,80}, {83,0,154}, 17,16),
            {TEXT("Windlass"), {4,0,-2}, {27,14,15}},
            {TEXT("LimbL"), {-18,-66,-4}, {37,74,19}},
            {TEXT("LimbR"), {-18,66,-4}, {37,74,19}},
            {TEXT("StringL"), {96,-2,0}, {99,10,7}},
            {TEXT("StringR"), {96,2,0}, {99,10,7}},
            {TEXT("Bolt"), {8,0,0}, {191,9,9}},
            {TEXT("Bolt"), {-136,0,6}, {50,25,25}}
        };
        static const FUseBox TrebuchetBoxes[] = {
            {NAME_None, {-13,0,34}, {244,150,34}},
            {NAME_None, {-190,-123,85}, {62,23,62}},
            {NAME_None, {-190,123,85}, {62,23,62}},
            {NAME_None, {0,-83,155}, {18,29,171}},
            {NAME_None, {0,83,155}, {18,29,171}},
            Beam(NAME_None, {-159,-86,18}, {0,-86,316}, 20,18),
            Beam(NAME_None, {159,-86,18}, {0,-86,316}, 20,18),
            Beam(NAME_None, {-159,86,18}, {0,86,316}, 20,18),
            Beam(NAME_None, {159,86,18}, {0,86,316}, 20,18),
            Beam(NAME_None, {0,-166,26}, {0,-88,253}, 16,16),
            Beam(NAME_None, {0,166,26}, {0,88,253}, 16,16),
            {NAME_None, {0,0,305}, {20,103,19}},
            Beam(TEXT("Arm"), {-278,0,-242}, {84,0,79}, 20,18),
            {TEXT("Weight"), {0,0,-73}, {55,48,85}},
            Beam(TEXT("Sling"), {0,0,0}, {-61,0,-35}, 20,14),
            {TEXT("Round"), {0,0,0}, {20,18,18}}
        };
        static const FUseBox SpireBoxes[] = {
            {NAME_None, {0,0,21}, {82,82,21}},
            {NAME_None, {0,0,80}, {58,58,38}},
            {NAME_None, {-74,0,98}, {18,28,28}},
            {TEXT("Mast"), {0,0,120}, {48,48,120}}
        };
        if (Engine.IsLightningSpire()) return MakeArrayView(SpireBoxes);
        if (Engine.IsTrebuchet()) return MakeArrayView(TrebuchetBoxes);
        return MakeArrayView(BallistaBoxes);
    }
}

void UVillageSiegeUseTargets::Register(AVillageSiegeEngine& Engine)
{
    Engines.Add(&Engine);
}

void UVillageSiegeUseTargets::Remove(AVillageSiegeEngine& Engine)
{
    Engines.Remove(&Engine);
}

AVillageSiegeEngine* UVillageSiegeUseTargets::Trace(const FVector& Player, const FVector& Eye,
    const FVector& Direction, double Reach, double& HitDistance) const
{
    AVillageSiegeEngine* Best = nullptr;
    HitDistance = TNumericLimits<double>::Max();
    for (const auto& Entry : Engines)
    {
        auto* Engine = Entry.Get();
        if (!Engine || Engine->IsActorBeingDestroyed()) continue;
        // Conservative bounds for a complete swing. Idle engines outside reach cost one distance check.
        const double Radius = (Engine->IsTrebuchet() ? 820. : 560.) * Engine->GetActorScale3D().GetAbsMax();
        const FVector Origin = Engine->GetActorLocation();
        if (FVector::DistSquared(Player,Origin) > FMath::Square(Reach+Radius) || !Engine->CanOperate()) continue;

        const double RayLength = FVector::Distance(Eye,Origin)+Radius+1.;
        const FVector End = Eye + Direction*RayLength;
        bool InReach = false;
        double First = TNumericLimits<double>::Max();
        for (const FUseBox& Box : UseBoxes(*Engine))
        {
            FTransform PartFrame = Engine->GetMasonry()->GetComponentTransform();
            if (!Box.Part.IsNone())
            {
                const FTransform* Pose = Engine->UsePartPoses.Find(Box.Part);
                if (!Pose) continue; // Includes ammunition already in flight.
                PartFrame = *Pose * Engine->Carriage->GetComponentTransform();
            }
            const FTransform Frame = FTransform(Box.Rotation,Box.Center) * PartFrame;
            const FBox Bounds(-Box.Extent,Box.Extent);
            if (!InReach)
            {
                const FVector Nearest = Bounds.GetClosestPointTo(Frame.InverseTransformPosition(Player));
                InReach = FVector::DistSquared(Frame.TransformPosition(Nearest),Player) <= FMath::Square(Reach);
            }
            const FVector Start = Frame.InverseTransformPosition(Eye);
            if (Bounds.IsInsideOrOn(Start))
            {
                // Turning away while standing at the edge of a thin part must release focus.
                if (FVector::DotProduct(Frame.GetLocation()-Eye,Direction) >= 0.) First = 0.;
                continue;
            }
            FVector Hit, Normal;
            float Time = 0.f;
            if (FMath::LineExtentBoxIntersection(Bounds,Start,Frame.InverseTransformPosition(End),
                    FVector::ZeroVector,Hit,Normal,Time))
                First = FMath::Min(First,RayLength*Time);
        }
        if (!InReach || First == TNumericLimits<double>::Max()) continue;
        if (!Best || First < HitDistance ||
            (First == HitDistance && Engine->GetPlacedId() < Best->GetPlacedId()))
        {
            Best = Engine;
            HitDistance = First;
        }
    }
    return Best;
}
