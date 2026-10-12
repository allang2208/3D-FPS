#include "BellowGroundingNode.h"
#include "BellowSacLobber.h"
#include "QuadrupedAnimationTemplate.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "MonsterGroundSupport.h"

FBellowGroundingNode::FBellowGroundingNode()
{
    Alpha = 1.f;
    // Same chains/phase order as author_locomotion.py. Keep the rear hock.
    const TCHAR* Names[4][5] = {
        {TEXT("Bone_009"), TEXT("Bone_008"), TEXT("Bone_007"), TEXT("Bone_006"), TEXT("Bone_005")},
        {TEXT("Bone_022"), TEXT("Bone_021"), TEXT("Bone_020"), TEXT("Bone_019"), nullptr},
        {TEXT("Bone_015"), TEXT("Bone_014"), TEXT("Bone_013"), TEXT("Bone_012"), TEXT("Bone_011")},
        {TEXT("Bone_027"), TEXT("Bone_026"), TEXT("Bone_025"), TEXT("Bone_024"), nullptr}};
    const TCHAR* Toes[] = {TEXT("Bone_004"), TEXT("Bone_018"), TEXT("Bone_010"), TEXT("Bone_023")};
    for (int32 I = 0; I < 4; ++I)
    {
        auto& L = Legs[I];
        L.Count = I % 2 == 0 ? 5 : 4;
        L.PhaseOffset = .25f * I;
        L.ToeName = Toes[I];
        for (int32 J = 0; J < L.Count; ++J) L.Chain[J].BoneName = Names[I][J];
    }
}

void FBellowGroundingNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    for (auto& L : Legs)
        for (int32 J = 0; J < L.Count; ++J) L.Chain[J].Initialize(Bones);
}

bool FBellowGroundingNode::IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones)
{
    if (!ReferenceReady || !Enabled) return false;
    for (const auto& L : Legs)
        for (int32 J = 0; J < L.Count; ++J)
            if (!L.Chain[J].IsValidToEvaluate(Bones)) return false;
    return true;
}

void FBellowGroundingNode::CacheReference(const ABellowSacLobber* Monster)
{
    auto* Asset = Monster->GetMesh()->GetSkeletalMeshAsset();
    if (CachedMesh.Get() == Asset) return;
    CachedMesh = Asset;
    ReferenceReady = false;
    QueryAge = 1.f;
    if (!Asset) return;
    const auto& Ref = Asset->GetRefSkeleton();
    TArray<FTransform> Bind = Ref.GetRefBonePose();
    for (int32 I = 0; I < Bind.Num(); ++I)
        if (Ref.GetParentIndex(I) != INDEX_NONE) Bind[I] *= Bind[Ref.GetParentIndex(I)];
    const float FloorZ = Asset->GetBounds().Origin.Z - Asset->GetBounds().BoxExtent.Z;
    PivotCS = FVector::ZeroVector;
    for (auto& L : Legs)
    {
        L.Valid = false;
        L.FootMeshIndex = Ref.FindBoneIndex(L.Chain[L.Count - 1].BoneName);
        const int32 Toe = Ref.FindBoneIndex(L.ToeName);
        if (L.FootMeshIndex == INDEX_NONE || Toe == INDEX_NONE) return;
        const FTransform& Foot = Bind[L.FootMeshIndex];
        const FVector Along = Bind[Toe].GetLocation() - Foot.GetLocation();
        // The authored palm/sole lies on the mesh's bind floor, below its ankle.
        // InverseTransformPosition retains the SmartRig's 100x root-unit conversion.
        for (int32 J = 0; J < 2; ++J)
        {
            FVector Contact = Foot.GetLocation() + Along * (J == 0 ? -.35f : 1.5f);
            Contact.Z = FloorZ;
            L.Sole[J] = Foot.InverseTransformPosition(Contact);
            PivotCS += Contact / 8.f;
        }
    }
    ReferenceReady = true;
}

void FBellowGroundingNode::Prepare(const ABellowSacLobber* Monster,
    const UQuadrupedTemplateAnimInstance* Anim, float DeltaSeconds)
{
    const bool WasEnabled = Enabled;
    Enabled = false;
    if (!Monster || !Anim || Monster->Dead()) return;
    const auto* Mesh = Monster->GetMesh();
    const auto* Move = Monster->GetCharacterMovement();
    if (Mesh->IsSimulatingPhysics() || !Move->IsMovingOnGround()) return;
    CacheReference(Monster);
    if (!ReferenceReady) return;
    const FTransform NextFrame = Mesh->GetComponentTransform();
    const bool Reset = !WasEnabled || FVector::DistSquared(NextFrame.GetLocation(), Frame.GetLocation()) > FMath::Square(120.);
    Frame = NextFrame;
    if (Reset) { QueryAge = 1.f; Tilt = WantedTilt = FQuat::Identity; Height = WantedHeight = 0.f; }
    Enabled = true;
    MoveWeight = Anim->MoveAlpha;
    Walking = Anim->ActiveAction.IsNone() && Anim->MoveAlpha > .05f;
    Phase = Anim->GaitPhase + (Anim->AnimationSet
        ? FMath::Lerp(Anim->AnimationSet->WalkPhaseOffset, Anim->AnimationSet->RunPhaseOffset, Anim->WalkRunAlpha) : 0.f);
    const float Dt = FMath::Clamp(DeltaSeconds, 0.f, .1f);
    QueryAge += Dt;
    const float Interval = Mesh->WasRecentlyRendered(.3f) || Monster->GetNetMode() == NM_DedicatedServer ? .05f : .15f;
    if (QueryAge >= Interval)
    {
        QueryAge = 0.f;
        // Complex scene collision follows visible treads even when movement uses a stair ramp.
        FMonsterGroundProbe Probe(Monster);
        const FVector Pivot = Frame.TransformPosition(PivotCS);
        auto Trace = [&](const FVector& At, FHitResult& Hit)
        {
            return Probe.Trace(Monster->GetWorld(),FVector(At.X,At.Y,Pivot.Z+110.f),
                FVector(At.X,At.Y,Pivot.Z-160.f),FVector::UpVector,Move->GetWalkableFloorZ(),Hit);
        };
        FVector Points[4], Mean = FVector::ZeroVector;
        int32 Count = 0;
        for (auto& L : Legs)
        {
            L.Valid = false;
            const FTransform Foot = Mesh->GetBoneTransform(L.FootMeshIndex);
            const FVector Middle = Foot.TransformPosition((L.Sole[0] + L.Sole[1]) * .5f);
            double BestHeight = -TNumericLimits<double>::Max();
            for (const FVector& Sole : L.Sole)
            {
                FHitResult Hit;
                if (!Trace(Foot.TransformPosition(Sole), Hit)) continue;
                const FVector N = Hit.ImpactNormal;
                const double Z = Hit.ImpactPoint.Z - (N.X * (Middle.X - Hit.ImpactPoint.X)
                    + N.Y * (Middle.Y - Hit.ImpactPoint.Y)) / N.Z;
                if (Z > BestHeight)
                {
                    BestHeight = Z;
                    L.Point = Hit.ImpactPoint;
                    L.Normal = N;
                    L.Valid = true;
                }
            }
            if (L.Valid) { Points[Count] = FVector(Middle.X, Middle.Y, BestHeight); Mean += Points[Count++]; }
        }
        WantedHeight = 0.f;
        WantedTilt = FQuat::Identity;
        if (Count >= 3)
        {
            Mean /= Count;
            double XX = 0., YY = 0., XY = 0., XZ = 0., YZ = 0.;
            for (int32 I = 0; I < Count; ++I)
            {
                const FVector D = Points[I] - Mean;
                XX += D.X * D.X; YY += D.Y * D.Y; XY += D.X * D.Y;
                XZ += D.X * D.Z; YZ += D.Y * D.Z;
            }
            const double Det = XX * YY - XY * XY;
            if (Det > 1.)
            {
                FVector Normal(-(XZ * YY - YZ * XY) / Det, -(YZ * XX - XZ * XY) / Det, 1.);
                Normal.Normalize();
                WantedTilt = FQuat::FindBetweenNormals(FVector::UpVector, Normal);
                const float Angle = WantedTilt.GetAngle(), Limit = FMath::DegreesToRadians(32.f);
                if (Angle > Limit) WantedTilt = FQuat::Slerp(FQuat::Identity, WantedTilt, Limit / Angle);
                Normal = WantedTilt.RotateVector(FVector::UpVector);
                WantedHeight = Mean.Z - (Normal.X * (Pivot.X - Mean.X) + Normal.Y * (Pivot.Y - Mean.Y)) / Normal.Z - Pivot.Z;
                // Keep the heavy belly clear of raised treads between the front/rear feet.
                for (const FName Body : {FName(TEXT("Bone_000")), FName(TEXT("Bone_003"))})
                {
                    const FVector At = Mesh->GetSocketLocation(Body);
                    FHitResult Hit;
                    if (Trace(At, Hit))
                    {
                        const FVector FloorAt = Pivot + WantedTilt.RotateVector(FVector(At.X, At.Y, Pivot.Z) - Pivot);
                        WantedHeight = FMath::Max(WantedHeight, float(Hit.ImpactPoint.Z - FloorAt.Z - 24.f));
                    }
                }
                WantedHeight = FMath::Clamp(WantedHeight, -90.f, 65.f);
            }
        }
    }
    const float Blend = Reset ? 1.f : 1.f - FMath::Exp(-10.f * Dt);
    Height = FMath::Lerp(Height, WantedHeight, Blend);
    Tilt = FQuat::Slerp(Tilt, WantedTilt, Blend).GetNormalized();
}

FTransform FBellowGroundingNode::Grounded(const FTransform& Bone) const
{
    FTransform Result = Bone;
    const FVector Pivot = Frame.TransformPosition(PivotCS);
    Result.SetLocation(Frame.InverseTransformPosition(Pivot + Tilt.RotateVector(Frame.TransformPosition(Bone.GetLocation()) - Pivot)
        + FVector(0.f, 0.f, Height)));
    Result.SetRotation((Frame.GetRotation().Inverse() * Tilt * Frame.GetRotation() * Bone.GetRotation()).GetNormalized());
    return Result;
}

void FBellowGroundingNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output, TArray<FBoneTransform>& Out)
{
    const auto& Bones = Output.Pose.GetPose().GetBoneContainer();
    const float BaseZ = Frame.TransformPosition(PivotCS).Z;
    FVector Goals[4];
    FQuat FootRotations[4];
    float ReachLowering = 0.f;
    // First place all four soles, then lower the body just enough for the
    // longest-reaching support leg. Reach clamping alone leaves that foot hanging.
    for (int32 I = 0; I < 4; ++I)
    {
        const auto& L = Legs[I];
        if (!L.Valid) continue;
        const FTransform SourceFoot = Output.Pose.GetComponentSpaceTransform(L.Chain[L.Count - 1].GetCompactPoseIndex(Bones));
        const FQuat WorldRotation = (FQuat::FindBetweenNormals(FVector::UpVector, L.Normal)
            * Frame.GetRotation() * SourceFoot.GetRotation()).GetNormalized();
        FVector Goal = Frame.TransformPosition(SourceFoot.GetLocation());
        const FTransform WorldFoot(WorldRotation, Goal, SourceFoot.GetScale3D() * Frame.GetScale3D());
        double Gap = TNumericLimits<double>::Max(), SourceBottom = TNumericLimits<double>::Max();
        for (const FVector& Sole : L.Sole)
        {
            Gap = FMath::Min(Gap, FVector::DotProduct(WorldFoot.TransformPosition(Sole) - L.Point, L.Normal));
            SourceBottom = FMath::Min(SourceBottom, Frame.TransformPosition(SourceFoot.TransformPosition(Sole)).Z);
        }
        float Lift = 0.f;
        const float FootPhase = FMath::Frac(Phase + L.PhaseOffset);
        if (Walking && FootPhase >= .76f)
        {
            const float Swing = (FootPhase - .76f) / .24f;
            // Preserve the source swing and give the toes extra clearance over a riser.
            Lift = FMath::Max(float(FMath::Max(0., SourceBottom - BaseZ)), 12.f * MoveWeight * FMath::Square(FMath::Sin(PI * Swing)));
        }
        Goal.Z += (.6 - Gap) / L.Normal.Z + Lift;
        Goals[I] = Frame.InverseTransformPosition(Goal);
        FootRotations[I] = (Frame.GetRotation().Inverse() * WorldRotation).GetNormalized();
        if (Lift < 1.f)
        {
            FVector Previous = Frame.TransformPosition(Grounded(Output.Pose.GetComponentSpaceTransform(L.Chain[0].GetCompactPoseIndex(Bones))).GetLocation());
            const FVector Root = Previous;
            double Reach = 0.;
            for (int32 J = 1; J < L.Count; ++J)
            {
                const FVector Joint = Frame.TransformPosition(Grounded(Output.Pose.GetComponentSpaceTransform(L.Chain[J].GetCompactPoseIndex(Bones))).GetLocation());
                Reach += FVector::Distance(Previous, Joint);
                Previous = Joint;
            }
            const double VerticalSquared = FMath::Square(Reach * .98) - FVector::DistSquared2D(Root, Goal);
            if (VerticalSquared > 0. && Root.Z > Goal.Z)
                ReachLowering = FMath::Min(ReachLowering, float(Goal.Z + FMath::Sqrt(VerticalSquared) - Root.Z));
        }
    }
    // A bounded additional compression preserves belly clearance and avoids
    // pulling the entire animal down when one foot has no reachable support.
    const FVector Compression = Frame.InverseTransformVector(FVector(0.f, 0.f, FMath::Clamp(ReachLowering, -18.f, 0.f)));
    FTransform Root = Grounded(Output.Pose.GetComponentSpaceTransform(FCompactPoseBoneIndex(0)));
    Root.AddToTranslation(Compression);
    Out.Emplace(FCompactPoseBoneIndex(0), Root);
    for (int32 I = 0; I < 4; ++I)
    {
        const auto& L = Legs[I];
        if (!L.Valid) continue;
        FCompactPoseBoneIndex Indices[5];
        FTransform Solved[5];
        FVector Points[5];
        double Lengths[4], Reach = 0.;
        for (int32 J = 0; J < L.Count; ++J)
        {
            Indices[J] = L.Chain[J].GetCompactPoseIndex(Bones);
            Solved[J] = Grounded(Output.Pose.GetComponentSpaceTransform(Indices[J]));
            Solved[J].AddToTranslation(Compression);
            Points[J] = Solved[J].GetLocation();
            if (J > 0) { Lengths[J - 1] = FVector::Distance(Points[J - 1], Points[J]); Reach += Lengths[J - 1]; }
        }
        const int32 Last = L.Count - 1;
        FVector Target = Goals[I];
        const FVector Origin = Points[0], ToTarget = Target - Origin;
        if (ToTarget.Size() > Reach * .995) Target = Origin + ToTarget.GetSafeNormal() * Reach * .995;
        // Bounded FABRIK, seeded from this authored pose's anatomical bend every
        // frame. No stretched scales, no collapse of the rear hock into a two-bone leg.
        for (int32 Iteration = 0; Iteration < 16; ++Iteration)
        {
            Points[Last] = Target;
            for (int32 J = Last - 1; J >= 0; --J)
                Points[J] = Points[J + 1] + (Points[J] - Points[J + 1]).GetSafeNormal() * Lengths[J];
            Points[0] = Origin;
            for (int32 J = 1; J <= Last; ++J)
                Points[J] = Points[J - 1] + (Points[J] - Points[J - 1]).GetSafeNormal() * Lengths[J - 1];
            if (FVector::DistSquared(Points[Last], Target) < .01) break;
        }
        for (int32 J = 0; J < Last; ++J)
        {
            const FVector Before = (Solved[J + 1].GetLocation() - Solved[J].GetLocation()).GetSafeNormal();
            const FVector After = (Points[J + 1] - Points[J]).GetSafeNormal();
            FTransform Bone = Solved[J];
            Bone.SetLocation(Points[J]);
            Bone.SetRotation((FQuat::FindBetweenNormals(Before, After) * Bone.GetRotation()).GetNormalized());
            Out.Emplace(Indices[J], Bone);
        }
        FTransform Foot = Solved[Last];
        Foot.SetLocation(Points[Last]);
        Foot.SetRotation(FootRotations[I]);
        Out.Emplace(Indices[Last], Foot);
    }
    Out.Sort([](const FBoneTransform& A, const FBoneTransform& B) { return A.BoneIndex.GetInt() < B.BoneIndex.GetInt(); });
}
