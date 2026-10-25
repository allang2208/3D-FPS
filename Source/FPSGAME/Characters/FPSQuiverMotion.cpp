#include "FPSQuiverMotion.h"
#include "FPSPlayerBodyComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

namespace FPSQuiver
{
FVector Vector(const TSharedPtr<FJsonObject>& Json, const TCHAR* Key, const FVector& Fallback)
{
    const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
    if (!Json || !Json->TryGetArrayField(Key, Values) || Values->Num() != 3) return Fallback;
    return FVector((*Values)[0]->AsNumber(), (*Values)[1]->AsNumber(), (*Values)[2]->AsNumber());
}
float Number(const TSharedPtr<FJsonObject>& Json, const TCHAR* Key, float Fallback)
{
    double Value = Fallback; Json->TryGetNumberField(Key, Value); return float(Value);
}
}

FFPSQuiverMotion::~FFPSQuiverMotion()
{
    for (auto& Arrow : Arrows) if (auto* Part = Arrow.Get()) Part->DestroyComponent();
    if (auto* Target = Belt.Get())
    { const float Zero[30] = {}; Target->SetCustomPrimitiveDataFloatArray(0, MakeArrayView(Zero)); }
}

void FFPSQuiverMotion::Initialize(USkeletalMeshComponent* InBody, USkeletalMeshComponent* InBelt,
    const TSharedPtr<FJsonObject>& Settings, UStaticMesh* ArrowMesh, bool bOwnerBody)
{
    if (!InBody || !InBelt || !Settings || !InBody->GetSkeletalMeshAsset()) return;
    const auto& Ref = InBody->GetSkeletalMeshAsset()->GetRefSkeleton();
    Pelvis = Ref.FindBoneIndex(TEXT("pelvis")); if (Pelvis == INDEX_NONE) return;
    FTransform Bind = Ref.GetRefBonePose()[Pelvis];
    for (int32 Parent = Ref.GetParentIndex(Pelvis); Parent != INDEX_NONE; Parent = Ref.GetParentIndex(Parent))
        Bind = Bind * Ref.GetRefBonePose()[Parent];
    Body = InBody; Belt = InBelt; InverseBind = Bind.Inverse();
    BodyState = InBody->GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    Pivot = FPSQuiver::Vector(Settings, TEXT("pivot"), Pivot);
    Outward = FPSQuiver::Vector(Settings, TEXT("outward"), Outward).GetSafeNormal();
    BoundsMin = FPSQuiver::Vector(Settings, TEXT("bounds_min"), Pivot);
    BoundsMax = FPSQuiver::Vector(Settings, TEXT("bounds_max"), Pivot);
    Frequency = FMath::Clamp(FPSQuiver::Number(Settings, TEXT("frequency_hz"), 1.7f), 1.2f, 3.f);
    Damping = FMath::Clamp(FPSQuiver::Number(Settings, TEXT("damping"), 1.f), .85f, 1.2f);
    MaxAngle = FMath::Clamp(FPSQuiver::Number(Settings, TEXT("max_angle_degrees"), 2.f), 0.f, 2.5f);
    MaxTravel = FMath::Clamp(FPSQuiver::Number(Settings, TEXT("max_displacement_cm"), 2.f), 0.f, 2.5f);
    const TArray<TSharedPtr<FJsonValue>>* Tips = nullptr;
    if (!ArrowMesh || !Settings->TryGetArrayField(TEXT("arrow_tips"), Tips)) return;
    // The existing wooden-arrow asset points toward its tip along local +X.
    const FVector Up = FPSQuiver::Vector(Settings, TEXT("arrow_up"), FVector::UpVector).GetSafeNormal();
    const FQuat Rotation = FQuat::FindBetweenNormals(FVector::ForwardVector, -Up);
    const FBoxSphereBounds Bounds = ArrowMesh->GetBounds();
    for (int32 Index = 0; Index < FMath::Min(5, Tips->Num()); ++Index)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!(*Tips)[Index]->TryGetArray(Values) || Values->Num() != 3) continue;
        const FVector Tip((*Values)[0]->AsNumber(), (*Values)[1]->AsNumber(), (*Values)[2]->AsNumber());
        const FVector TipInMesh(Bounds.Origin.X + Bounds.BoxExtent.X, Bounds.Origin.Y, Bounds.Origin.Z);
        const FTransform Reference(Rotation, Tip - Rotation.RotateVector(TipInMesh));
        auto* Part = NewObject<UStaticMeshComponent>(InBelt->GetOwner(), NAME_None, RF_Transient);
        InBelt->GetOwner()->AddInstanceComponent(Part);
        Part->ComponentTags.Add(TEXT("QuiverDecorativeArrow"));
        Part->SetStaticMesh(ArrowMesh); Part->SetupAttachment(InBody, TEXT("pelvis"));
        Part->SetRelativeTransform(Reference * InverseBind);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision); Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false); Part->SetVisibility(false); Part->SetHiddenInGame(true);
        Part->SetOnlyOwnerSee(InBelt->bOnlyOwnerSee); Part->SetOwnerNoSee(InBelt->bOwnerNoSee);
        Part->SetFirstPersonPrimitiveType(InBelt->FirstPersonPrimitiveType);
        Part->SetCastShadow(InBelt->CastShadow); Part->bCastHiddenShadow = false;
        if (bOwnerBody) { Part->SetHiddenInSceneCapture(true); Part->SetVisibleInRayTracing(false); Part->bAffectDynamicIndirectLighting = false; }
        Part->RegisterComponent(); Part->SetComponentTickEnabled(false);
        Arrows.Add(Part); ArrowReferences.Add(Reference);
    }
    FollowVisibility();
}

void FFPSQuiverMotion::FollowVisibility()
{
    const auto* Target = Belt.Get(); const auto* State = BodyState.Get(); if (!Target) return;
    const bool bBow = State && State->HasBowForPresentation();
    const bool bVisible = bBow && Target->IsVisible() && !Target->bHiddenInGame;
    for (auto& Entry : Arrows) if (auto* Part = Entry.Get())
    {
        if (Part->IsVisible() != bVisible) Part->SetVisibility(bVisible, false);
        if (Part->bHiddenInGame == bVisible) Part->SetHiddenInGame(!bVisible, false);
        if (Part->bOnlyOwnerSee != Target->bOnlyOwnerSee) Part->SetOnlyOwnerSee(Target->bOnlyOwnerSee);
        if (Part->bOwnerNoSee != Target->bOwnerNoSee) Part->SetOwnerNoSee(Target->bOwnerNoSee);
        if (Part->CastShadow != Target->CastShadow) Part->SetCastShadow(Target->CastShadow);
        // Hidden arrows must never cast a leftover shadow after switching weapons.
        Part->bCastHiddenShadow = bBow && Target->bCastHiddenShadow;
        if (Part->FirstPersonPrimitiveType != Target->FirstPersonPrimitiveType)
            Part->SetFirstPersonPrimitiveType(Target->FirstPersonPrimitiveType);
    }
}

void FFPSQuiverMotion::Push(const FTransform& Frame, const FQuat& Rotation, const FVector& Shift, bool bReset)
{
    auto* Target = Belt.Get(); if (!Target) return;
    const FTransform Motion(Rotation, Pivot - Rotation.RotateVector(Pivot) + Shift);
    for (int32 I = 0; I < Arrows.Num(); ++I) if (auto* Part = Arrows[I].Get())
        Part->SetRelativeTransform(ArrowReferences[I] * Motion * InverseBind);
    const FQuat Q = Frame.GetRotation() * Rotation * Frame.GetRotation().Inverse();
    const FVector X = Q.RotateVector(FVector::ForwardVector) - FVector::ForwardVector;
    const FVector Y = Q.RotateVector(FVector::RightVector) - FVector::RightVector;
    const FVector Z = Q.RotateVector(FVector::UpVector) - FVector::UpVector;
    const FVector Values[] = {Frame.TransformPosition(Pivot), FVector(X.X,Y.X,Z.X),
        FVector(X.Y,Y.Y,Z.Y), FVector(X.Z,Y.Z,Z.Z), Frame.TransformVectorNoScale(Shift)};
    float Data[30];
    for (int32 I = 0; I < 5; ++I) for (int32 J = 0; J < 3; ++J) Data[I*3+J] = float(Values[I][J]);
    FMemory::Memcpy(Data+15, bReset ? Data : Previous, sizeof(Previous));
    Target->SetCustomPrimitiveDataFloatArray(0, MakeArrayView(Data));
    FMemory::Memcpy(Previous, Data, sizeof(Previous));
}

void FFPSQuiverMotion::Tick(float Delta)
{
    auto* Leader = Body.Get(); auto* Target = Belt.Get();
    if (!Leader || !Target || Pelvis == INDEX_NONE || Delta <= UE_SMALL_NUMBER) return;
    FollowVisibility();
    const FTransform Frame = InverseBind * Leader->GetBoneTransform(Pelvis);
    const FVector Anchor = Frame.TransformPosition(Pivot);
    const bool bReset = !bInitialized || Delta > .35f || FVector::DistSquared(Anchor, LastAnchor) > 22500.f
        || !Target->IsVisible() || Target->bHiddenInGame || Leader->IsSimulatingPhysics();
    if (bReset)
    {
        Angles = AngularVelocity = FVector::ZeroVector; Bounce = BounceVelocity = 0.f;
        FilteredVelocity = Leader->GetOwner()->GetVelocity(); LastAnchor = Anchor;
        LastFrame = Frame.GetRotation(); bInitialized = true;
        Push(Frame, FQuat::Identity, FVector::ZeroVector, true); return;
    }
    // Rendered pelvis motion includes the native walk/run cadence and network
    // smoothing. No replicated cosmetic state or independent bobbing clock.
    const FVector Velocity = FMath::Lerp(FilteredVelocity, ((Anchor-LastAnchor)/Delta).GetClampedToMaxSize(1200.f), 1.f-FMath::Exp(-16.f*Delta));
    const FVector Acceleration = Frame.InverseTransformVectorNoScale((Velocity-FilteredVelocity)/Delta).GetClampedToMaxSize(1800.f);
    FVector Axis; double Angle; (LastFrame.Inverse()*Frame.GetRotation()).ToAxisAndAngle(Axis, Angle);
    const FVector Turning = (Axis*FMath::RadiansToDegrees(FMath::UnwindRadians(Angle))/Delta).GetClampedToMaxSize(300.f);
    const FVector Aim = (FVector(-Acceleration.Y, Acceleration.X, 0.)*.002 - Turning*.012).GetClampedToMaxSize(MaxAngle);
    const float BounceAim = FMath::Clamp(float(-Acceleration.Z*.00012), -.12f, .12f);
    const int32 Steps = FMath::Clamp(FMath::CeilToInt(Delta*120.f), 1, 42);
    const float Step = Delta/Steps, W = 2.f*UE_PI*Frequency;
    for (int32 I = 0; I < Steps; ++I)
    {
        AngularVelocity += (W*W*(Aim-Angles)-2.f*Damping*W*AngularVelocity)*Step;
        Angles += AngularVelocity*Step;
        if (Angles.SizeSquared() > MaxAngle*MaxAngle) { Angles = Angles.GetClampedToMaxSize(MaxAngle); AngularVelocity *= .5; }
        BounceVelocity += (W*W*(BounceAim-Bounce)-2.f*Damping*W*BounceVelocity)*Step;
        Bounce = FMath::Clamp(Bounce+BounceVelocity*Step, -.12f, .12f);
    }
    FilteredVelocity = Velocity; LastAnchor = Anchor; LastFrame = Frame.GetRotation();
    FQuat Rotation = FQuat(FVector::UpVector,FMath::DegreesToRadians(Angles.Z))
        *FQuat(FVector::RightVector,FMath::DegreesToRadians(Angles.Y))*FQuat(FVector::ForwardVector,FMath::DegreesToRadians(Angles.X));
    FVector Shift(0,0,Bounce);
    // Limit total surface travel, then react any inward swing against the hip.
    // A radius bound covers every point, including simultaneous pitch and roll.
    double Radius = 0.;
    for (int32 I = 0; I < 8; ++I)
    {
        const FVector P((I&1)?BoundsMax.X:BoundsMin.X,(I&2)?BoundsMax.Y:BoundsMin.Y,(I&4)?BoundsMax.Z:BoundsMin.Z);
        Radius = FMath::Max(Radius, (P-Pivot).Size());
    }
    const double Travel = 2.*Radius*FMath::Sin(Rotation.GetAngle()*.5) + FMath::Abs(Bounce);
    // Up to one additional outward correction of equal size is budgeted.
    if (Travel > MaxTravel*.5 && Travel > UE_SMALL_NUMBER)
    { const double Ratio = MaxTravel*.5/Travel; Rotation = FQuat::Slerp(FQuat::Identity,Rotation,Ratio).GetNormalized(); Shift *= Ratio; }
    double Inward = 0.;
    for (int32 I = 0; I < 8; ++I)
    {
        const FVector P((I&1)?BoundsMax.X:BoundsMin.X,(I&2)?BoundsMax.Y:BoundsMin.Y,(I&4)?BoundsMax.Z:BoundsMin.Z);
        Inward = FMath::Max(Inward, -FVector::DotProduct(Rotation.RotateVector(P-Pivot)-(P-Pivot)+Shift, Outward));
    }
    Shift += Outward*Inward;
    Push(Frame, Rotation, Shift, false);
}
