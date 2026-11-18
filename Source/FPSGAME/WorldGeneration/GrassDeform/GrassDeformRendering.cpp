#include "GrassDeformSubsystem.h"
#include "GrassDeformSettings.h"

#include "Engine/World.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/Paths.h"
#include "Scalability.h"   // Scalability::DefaultQualityLevel, the permissive fallback when the cvar is unresolved

#include "GrassDeformParamsPrivate.h"
UTextureRenderTarget2D* UGrassDeformSubsystem::GetReadTarget() const
{
    return RenderTargets[ReadIndex];
}

UTextureRenderTarget2D* UGrassDeformSubsystem::GetWriteTarget() const
{
    return RenderTargets[1 - ReadIndex];
}

void UGrassDeformSubsystem::FlipReadSide()
{
    ReadIndex = 1 - ReadIndex;
    bReadSideDirty = true;
}

void UGrassDeformSubsystem::DrainPendingStamps()
{
    if (Pending.Num() == 0) return;

    UWorld* World = GetWorld();
    UMaterialInstanceDynamic* Material = StampMaterial;
    if (!World || !Material || !GetWriteTarget() || !GetReadTarget()) { Pending.Reset(); return; }

    // Radius arrives in cm; the stamp material needs it in UV. One division per event.
    const float InvWindow = 1.f / GrassDeformTuning::WindowSizeCm;

    // The stamp reads the current read side through its "Old" texture parameter and accumulates
    // into the write side, so the whole queue is chained stamp-on-stamp. Each iteration promotes
    // the target it just wrote (see the flip below) so the next stamp sees the previous one.
    UTextureRenderTarget2D* WriteTarget = GetWriteTarget();

    for (const FPendingStamp& Stamp : Pending)
    {
        const FVector2D StampUV = (Stamp.CenterXY - WindowCenter) * InvWindow + FVector2D(0.5, 0.5);
        const float Margin = Stamp.Radius * InvWindow;
        if (StampUV.X < -Margin || StampUV.X > 1.f + Margin || StampUV.Y < -Margin || StampUV.Y > 1.f + Margin) continue;
        const FVector2D StartUV = (Stamp.StartXY - WindowCenter) * InvWindow + FVector2D(0.5, 0.5);
        // Both outputs sample exactly the same old pair. Only promote after BOTH draws.
        for (UMaterialInstanceDynamic* Pass : {StampMaterial.Get(), StampTimeMaterial.Get()})
        {
            Pass->SetTextureParameterValue(GrassDeformParams::PassSource, GetReadTarget());
            Pass->SetTextureParameterValue(TEXT("OldTime"), ContactTimeTargets[ReadIndex]);
            Pass->SetVectorParameterValue(GrassDeformParams::CenterUV, FLinearColor(StampUV.X, StampUV.Y, 0.f, 0.f));
            Pass->SetVectorParameterValue(GrassDeformParams::StartUV, FLinearColor(StartUV.X, StartUV.Y, 0.f, 0.f));
            Pass->SetVectorParameterValue(TEXT("TravelDirection"), FLinearColor(Stamp.Direction.X, Stamp.Direction.Y, 0.f, 0.f));
            Pass->SetScalarParameterValue(GrassDeformParams::IsSweep, Stamp.bSweep ? 1.f : 0.f);
            Pass->SetScalarParameterValue(GrassDeformParams::RadiusUV, Stamp.Radius * InvWindow);
            Pass->SetScalarParameterValue(GrassDeformParams::Strength, Stamp.Strength);
            Pass->SetScalarParameterValue(TEXT("CoreFraction"), Stamp.CoreFraction);
            Pass->SetScalarParameterValue(TEXT("DirectionBias"), Stamp.DirectionBias);
            Pass->SetScalarParameterValue(TEXT("PressDistanceUV"), Stamp.PressDistance * InvWindow);
            Pass->SetScalarParameterValue(TEXT("ContactNow"), float(World->GetTimeSeconds()));
            Pass->SetScalarParameterValue(TEXT("HoldSeconds"), FMath::Max(Response->HoldSeconds, 0.f));
            Pass->SetScalarParameterValue(TEXT("RecoverSeconds"), FMath::Max(Response->RecoverSeconds, 0.05f));
        }
        UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, WriteTarget, StampMaterial);
        UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, ContactTimeTargets[1 - ReadIndex], StampTimeMaterial);

        // The wavefront speed and origin are read by MF_GrassDeform at render time, so they are
        // published to the collection here (once per impulse; each setter is skipped when the value
        // already matches, because a redundant write dirties the uniform buffer for every material
        // that references the collection).
        if (Stamp.bImpulse && Stamp.WaveSpeed > 0.f)
        {
            if (UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(CollectionAsset))
            {
                // Canvas opaque emissive writes RGB, not the fourth component of a Custom node.
                // Keep the one active wave in the MPC; RT RGB holds flatten and radial direction.
                Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveStartTime, Stamp.Timestamp);
                Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveRadius, Stamp.Radius);
                Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveStrength, Stamp.Strength);
                if (!FMath::IsNearlyEqual(Stamp.WaveSpeed, LastPublishedWaveSpeed))
                {
                    LastPublishedWaveSpeed = Stamp.WaveSpeed;
                    Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveSpeed, Stamp.WaveSpeed);
                }

                // World-space origin survives a recenter without an extra parameter update.
                const FLinearColor Origin(float(Stamp.CenterXY.X), float(Stamp.CenterXY.Y), 0.f, 0.f);
                if (!Origin.Equals(LastPublishedWaveOrigin, 1e-4f))
                {
                    LastPublishedWaveOrigin = Origin;
                    Instance->SetVectorParameterValue(GrassDeformParams::MpcWaveOrigin, Origin);
                }
            }
        }

        // A second stamp in the same batch must see the first, so promote the write side to the
        // read side immediately and keep drawing into the other target.
        FlipReadSide();
        WriteTarget = GetWriteTarget();
        bDirty = true;
        FadeSecondsRemaining = FMath::Max(Response->HoldSeconds, 0.f) + FMath::Max(Response->RecoverSeconds, 0.05f);
    }

    // New footsteps never restart the fade clock for older footprints.
    Pending.Reset();
}

void UGrassDeformSubsystem::UpdateFade(float DeltaTime)
{
    // No render pass. The material evaluates age every frame, even between 10 Hz contacts.
    // Peak/time records can remain in the bounded window: expired records evaluate to zero.
    FadeSecondsRemaining = FMath::Max(0.f, FadeSecondsRemaining - DeltaTime);
    bDirty = FadeSecondsRemaining > 0.f;
}

void UGrassDeformSubsystem::RecenterWindow(const FVector& GroundPosition)
{
    // An integer texel shift is a copy, not another blur of the persistent trail.
    // 400 cm is 85.333 texels at 1024/48m; repeated fractional shifts smeared directions.
    const float TexelCm = GrassDeformTuning::WindowSizeCm / FMath::Max(ActiveRTSize, 1);
    const float Snapped = FMath::Max(1.f, FMath::RoundToFloat(GrassDeformTuning::SnapGridCm / TexelCm)) * TexelCm;
    const FVector2D NewCenter(
        FMath::GridSnap(float(GroundPosition.X), Snapped),
        FMath::GridSnap(float(GroundPosition.Y), Snapped));

    if (bWindowInitialized && FVector2D::Distance(NewCenter, WindowCenter) < KINDA_SMALL_NUMBER) return;

    UWorld* World = GetWorld();
    if (!World) return;

    const bool bFirst = !bWindowInitialized;
    const FVector2D PreviousCenter = WindowCenter;
    WindowCenter = NewCenter;
    bWindowInitialized = true;

    if (bFirst || !RenderTargets[0] || !RenderTargets[1] || !RecenterMaterial)
    {
        // Nothing to move on the first placement; both targets start black.
        return;
    }

    // UV offset of the new window centre measured in the old window's UV space. The recenter
    // material samples the read target at uv + ShiftUV, which is exactly the content move
    // (a feature's uv shifts by -Shift when the centre moves by +Shift).
    const FVector2D Shift(
        (NewCenter.X - PreviousCenter.X) / GrassDeformTuning::WindowSizeCm,
        (NewCenter.Y - PreviousCenter.Y) / GrassDeformTuning::WindowSizeCm);

    RecenterMaterial->SetVectorParameterValue(GrassDeformParams::ShiftUV, FLinearColor(Shift.X, Shift.Y, 0.f, 0.f));

    // Only the promoted read side is authoritative. Every next pass fully overwrites the other
    // target, so mirroring it costs a redundant full-screen draw and is unnecessary.
    RecenterMaterial->SetTextureParameterValue(GrassDeformParams::PassSource, GetReadTarget());
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, GetWriteTarget(), RecenterMaterial);
    RecenterTimeMaterial->SetVectorParameterValue(GrassDeformParams::ShiftUV, FLinearColor(Shift.X, Shift.Y, 0.f, 0.f));
    RecenterTimeMaterial->SetTextureParameterValue(GrassDeformParams::PassSource, ContactTimeTargets[ReadIndex]);
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, ContactTimeTargets[1 - ReadIndex], RecenterTimeMaterial);
    FlipReadSide();
}

void UGrassDeformSubsystem::UpdateTrampleSource(float DeltaTime)
{
    UWorld* World = GetWorld();
    if (!World || !Response) return;
    APlayerController* Controller = World->GetFirstPlayerController();
    ACharacter* Character = Controller ? Cast<ACharacter>(Controller->GetPawn()) : nullptr;
    if (Trample.Character.Get() != Character)
    {
        Trample.Character = Character;
        Trample.bHasProjection = false;
        bBodyGrounded = false;
    }
    const bool bGrounded = Character && Character->GetCharacterMovement()
        && Character->GetCharacterMovement()->IsMovingOnGround();
    if (!bGrounded)
    {
        BodyContact.A = 0.f;
        BodyContactAge = 0.f;
        bBodyGrounded = false;
        Trample.bHasProjection = false;
        TrampleClock = 0.f;
        return;
    }

    const FVector Location = Character->GetActorLocation();
    const FVector2D Projection(Location.X, Location.Y);
    const bool bTeleport = bBodyGrounded && FVector2D::Distance(Projection, PreviousBodyPosition)
        > GrassDeformTuning::TrampleMaxSegmentCm;
    if (!bBodyGrounded || bTeleport)
    {
        BodyContactAge = 0.f;
        Trample.bHasProjection = false;
    }
    PreviousBodyPosition = Projection;
    bBodyGrounded = true;
    BodyContactAge += DeltaTime;
    const FVector Velocity = Character->GetVelocity();
    const FVector2D HorizontalVelocity(Velocity.X, Velocity.Y);
    const float Speed = HorizontalVelocity.Size();
    if (Speed > 1.f) BodyDirection = HorizontalVelocity / Speed;
    const float CapsuleRadius = Character->GetCapsuleComponent()->GetScaledCapsuleRadius();
    const float Radius = FMath::Max(FMath::Max(Response->BodyRadiusCm, 1.f), CapsuleRadius * GrassDeformTuning::TrampleRadiusScale);
    const float PressSeconds = FMath::Max(Response->PressSeconds, 0.01f);
    const float Entry = FMath::SmoothStep(0.f, 1.f, FMath::Clamp(BodyContactAge / PressSeconds, 0.f, 1.f));
    const float Strength = FMath::Clamp(Response->BodyStrength, 0.f, 1.f) * Entry;
    BodyContact = FLinearColor(Projection.X, Projection.Y, Radius, Strength);
    // Leading edge eases down over the distance travelled in PressSeconds.
    BodyMotion = FLinearColor(BodyDirection.X, BodyDirection.Y, Speed * PressSeconds, 0.f);

    TrampleClock += DeltaTime;
    if (TrampleClock < 1.f / GrassDeformTuning::TrampleCheckHz) return;
    TrampleClock = 0.f;
    if (Trample.bHasProjection && FVector2D::Distance(Projection, Trample.LastProjection) > GrassDeformTuning::TrampleMaxSegmentCm)
        Trample.bHasProjection = false;
    // Also refresh while stationary. The continuous body field holds between these writes.
    if (EnqueueStamp(Location, Radius, Strength, 0.f, false))
    {
        FPendingStamp& Stamp = Pending.Last();
        Stamp.StartXY = Trample.bHasProjection ? Trample.LastProjection : Projection;
        Stamp.bSweep = true;
        Stamp.Direction = BodyDirection;
        Stamp.DirectionBias = FMath::Clamp(Response->ForwardBias, 0.51f, 1.f);
        Stamp.CoreFraction = FMath::Clamp(Response->CoreFraction, 0.f, 0.95f);
        Stamp.PressDistance = Speed * PressSeconds;
        Trample.LastProjection = Projection;
        Trample.bHasProjection = true;
    }
}

void UGrassDeformSubsystem::PublishParameters()
{
    UWorld* World = GetWorld();
    if (!World || !CollectionAsset) return;

    UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(CollectionAsset);
    if (!Instance) return;

    // Time plus changed body vectors; no per-instance writes or per-frame RT passes.
    if (!BodyContact.Equals(PublishedBodyContact, 0.0001f))
    {
        PublishedBodyContact = BodyContact;
        Instance->SetVectorParameterValue(TEXT("GrassBodyContact"), BodyContact);
    }
    if (!BodyMotion.Equals(PublishedBodyMotion, 0.0001f))
    {
        PublishedBodyMotion = BodyMotion;
        Instance->SetVectorParameterValue(TEXT("GrassBodyMotion"), BodyMotion);
    }
    if (Response && !bResponsePublished)
    {
        Instance->SetScalarParameterValue(TEXT("GrassHoldSeconds"), FMath::Max(Response->HoldSeconds, 0.f));
        Instance->SetScalarParameterValue(TEXT("GrassRecoverSeconds"), FMath::Max(Response->RecoverSeconds, 0.05f));
        Instance->SetScalarParameterValue(TEXT("GrassCoreFraction"), FMath::Clamp(Response->CoreFraction, 0.f, 0.95f));
        Instance->SetScalarParameterValue(TEXT("GrassBendAngle"), FMath::Clamp(Response->BendAngleDegrees, 0.f, 85.f));
        Instance->SetScalarParameterValue(TEXT("GrassFlatWindScale"), FMath::Clamp(Response->FlatWindScale, 0.f, 1.f));
        Instance->SetScalarParameterValue(TEXT("GrassForwardBias"), FMath::Clamp(Response->ForwardBias, 0.51f, 1.f));
        bResponsePublished = true;
    }
    const double Now = World->GetTimeSeconds();
    if (Now != PublishedWorldTime)
    {
        Instance->SetScalarParameterValue(GrassDeformParams::MpcWorldTime, float(Now));
        PublishedWorldTime = Now;
    }

    // The grass shader picks the read side of the ping-pong pair through this scalar: both RT
    // assets are wired into MF_GrassDeform as TextureObjectParameter defaults (a Material
    // Parameter Collection cannot carry textures, and a subsystem-owned MID of MA_Grass never
    // reaches the rendered foliage), and ReadIsB selects between them with a uniform branch.
    // Published on flip only.
    if (bReadSideDirty)
    {
        bReadSideDirty = false;
        const int32 ReadIsB = (ReadIndex == 1) ? 1 : 0;
        if (ReadIsB != LastPublishedReadIsB)
        {
            LastPublishedReadIsB = ReadIsB;
            Instance->SetScalarParameterValue(GrassDeformParams::MpcReadIsB, float(ReadIsB));
        }
    }

    // Publish the off gate even before the first player/window placement.
    const int32 Enabled = IsEnabled() && bWindowInitialized ? 1 : 0;
    if (Enabled != LastPublishedEnabled)
    {
        LastPublishedEnabled = Enabled;
        Instance->SetScalarParameterValue(GrassDeformParams::MpcEnabled, float(Enabled));
    }

    if (!bWindowInitialized) return;

    if (!WindowCenter.Equals(LastPublishedCenter, 0.01f))
    {
        LastPublishedCenter = WindowCenter;
        Instance->SetVectorParameterValue(GrassDeformParams::MpcCenter, FLinearColor(WindowCenter.X, WindowCenter.Y, 0.f, 0.f));
    }

    const float WindowSize = GrassDeformTuning::WindowSizeCm;
    if (!FMath::IsNearlyEqual(WindowSize, LastPublishedWindowSize))
    {
        LastPublishedWindowSize = WindowSize;
        Instance->SetScalarParameterValue(GrassDeformParams::MpcWindowSize, WindowSize);
    }

    const float Regrowth = Response ? FMath::Max(Response->HoldSeconds, 0.f) + FMath::Max(Response->RecoverSeconds, 0.05f) : 2.4f;
    if (!FMath::IsNearlyEqual(Regrowth, LastPublishedRegrowth))
    {
        LastPublishedRegrowth = Regrowth;
        Instance->SetScalarParameterValue(GrassDeformParams::MpcRegrowthSeconds, Regrowth);
    }

}

bool UGrassDeformSubsystem::HasLiveContent() const
{
    return bDirty;
}
