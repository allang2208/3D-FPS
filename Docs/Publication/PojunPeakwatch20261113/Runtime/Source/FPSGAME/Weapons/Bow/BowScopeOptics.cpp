#include "BowScopeOptics.h"
#include "BowWeaponComponent.h"
#include "BowPartComponent.h"
#include "../PhysicalScopeView.h"
#include "../../FPSGAMECharacter.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "SceneView.h"

namespace BowScopeOptics
{
TAutoConsoleVariable<int32> OpticalPresentation(TEXT("fps.Bow.Scope.OpticalPresentation"),1,
    TEXT("Peakwatch 3-6x physical-lens capture; 0 retains the legacy main-camera zoom."));
constexpr float LensRadiusCM=1.115f*1.75f;
// Settled glass diameter as a fraction of the owner's shorter viewport axis.
constexpr float ApertureFraction=.72f;
}

bool UBowScopeOptics::Enabled() { return BowScopeOptics::OpticalPresentation.GetValueOnGameThread()!=0; }

bool UBowScopeOptics::OwnsPrimitive(const UPrimitiveComponent* Primitive) const
{
    return bSavedCamera&&Primitives.ContainsByPredicate([Primitive](const auto& State){return State.Component.Get()==Primitive;});
}

bool UBowScopeOptics::HidesPrimitive(const UPrimitiveComponent* Primitive) const
{
    if(!bSavedCamera)return false;
    const auto* State=Primitives.FindByPredicate([Primitive](const auto& Entry){return Entry.Component.Get()==Primitive;});
    return State&&State->bOwnerNoSee;
}

void UBowScopeOptics::RestoreCamera()
{
    if (bSavedCamera) if (auto* Camera=OwnedCamera.Get())
    {
        Camera->SetEnableFirstPersonFieldOfView(bWasFirstPersonFOV);
        Camera->SetFirstPersonFieldOfView(SavedFirstPersonFOV);
    }
    bSavedCamera=false;OwnedCamera.Reset();
}

void UBowScopeOptics::RestoreAssembly(UBowWeaponComponent& Bow)
{
    if(Primitives.IsEmpty())return;
    auto Previous=MoveTemp(Primitives);
    for(const auto& State:Previous)if(auto* Primitive=State.Component.Get())
    {
        Primitive->SetFirstPersonPrimitiveType(static_cast<EFirstPersonPrimitiveType>(State.Type));
        if(Primitive->bOwnerNoSee!=State.bOwnerNoSee)Primitive->SetOwnerNoSee(State.bOwnerNoSee);
    }
    // Let death, rest and third-person viewing reapply their own hide requests.
    if(auto* Pawn=Bow.Character.Get())if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())Body->RefreshViewMode();
    for(const auto& State:Previous)if(State.bOwnerNoSee)if(auto* Primitive=State.Component.Get())
        if(!Primitive->bOwnerNoSee)Primitive->SetOwnerNoSee(true);
}

void UBowScopeOptics::InvalidateAssembly(UBowWeaponComponent& Bow)
{
    Release(Bow);
}

void UBowScopeOptics::Release(UBowWeaponComponent& Bow)
{
    Alpha=0.f;RestoreCamera();RestoreAssembly(Bow);Reticle=FBowScopeReticleState();
}

void UBowScopeOptics::UpdateCamera(UBowWeaponComponent& Bow)
{
    auto* Pawn=Bow.Character.Get();auto* Camera=Bow.Camera.Get();
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    if(!Pawn||!Pawn->IsLocallyControlled()||!Camera||!PC||PC->GetViewTarget()!=Pawn||PC->bShowMouseCursor||Pawn->IsAmmoWheelOpen()||
        !Bow.IsScopeOpticalPresentationEnabled()||!Bow.CanPresent(true)||Bow.AimAlpha()<=.001f||
        !Bow.Pivot||(Body&&Body->IsThirdPersonViewEnabled()))
    {Release(Bow);return;}
    if(!bSavedCamera)
    {
        OwnedCamera=Camera;bSavedCamera=true;
        bWasFirstPersonFOV=Camera->bEnableFirstPersonFieldOfView;
        SavedFirstPersonFOV=Camera->FirstPersonFieldOfView;
    }
    if(Primitives.IsEmpty())
    {
        // Cache only this bow's camera assembly, never replicated world meshes.
        TArray<USceneComponent*> Children;Bow.Pivot->GetChildrenComponents(true,Children);
        for(auto* Child:Children)if(auto* Primitive=Cast<UPrimitiveComponent>(Child))
        {
            Primitives.Add({Primitive,static_cast<uint8>(Primitive->FirstPersonPrimitiveType),bool(Primitive->bOwnerNoSee)});
            if(Primitive->FirstPersonPrimitiveType!=EFirstPersonPrimitiveType::FirstPerson)
                Primitive->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
        }
    }
    // A bow must retain its extended grip and full draw length. Calibrate its
    // optical eye relief through owner-view projection, without translating
    // the world camera, physical bow or drawing hand towards/behind the eye.
    // Focal normalization respects the actual constrained viewport and axis
    // policy; selected optical magnification never enters this framing solve.
    float FocalToShortSide=16.f/9.f;
    auto* Local=PC->GetLocalPlayer();FSceneViewProjectionData Projection;
    if(Local&&Local->ViewportClient&&Local->ViewportClient->Viewport&&
        Local->GetProjectionData(Local->ViewportClient->Viewport,Projection))
    {
        const FIntRect Rect=Projection.GetConstrainedViewRect();
        const float ViewFOV=PC->PlayerCameraManager?PC->PlayerCameraManager->GetFOVAngle():Camera->FieldOfView;
        if(Rect.Width()>0&&Rect.Height()>0)
            FocalToShortSide=float(Projection.ProjectionMatrix.M[0][0])*Rect.Width()
                /FMath::Min(Rect.Width(),Rect.Height())*FMath::Tan(FMath::DegreesToRadians(ViewFOV)*.5f);
    }
    const float TargetTan=BowScopeOptics::LensRadiusCM*Bow.BowScale*FocalToShortSide
        /(FMath::Max(30.f,Bow.AimSightDistanceCM)*BowScopeOptics::ApertureFraction);
    const float RestFOV=bWasFirstPersonFOV?SavedFirstPersonFOV:Camera->FieldOfView;
    const float RestTan=FMath::Tan(FMath::DegreesToRadians(RestFOV)*.5f);
    const float FramingPower=FMath::Lerp(1.f,RestTan/FMath::Max(.01f,TargetTan),
        FMath::SmoothStep(0.f,1.f,Bow.AimAlpha()));
    const float FramingFOV=FMath::RadiansToDegrees(2.f*FMath::Atan(RestTan/FramingPower));
    if(!Camera->bEnableFirstPersonFieldOfView)Camera->SetEnableFirstPersonFieldOfView(true);
    if(!FMath::IsNearlyEqual(Camera->FirstPersonFieldOfView,FramingFOV,.001f))Camera->SetFirstPersonFieldOfView(FramingFOV);
}

void UBowScopeOptics::Update(UBowWeaponComponent& Bow,float Delta,bool Present)
{
    if(!Present){Release(Bow);return;}
    UpdateCamera(Bow);
    if(!bSavedCamera)return;
    const auto* Sight=Bow.Part(TEXT("sight"));
    if(!Sight||!Sight->HasMesh()){Release(Bow);return;}
    Alpha=FMath::SmoothStep(.58f,.94f,Bow.AimAlpha());
    UpdateReticle(Bow,Delta);
    // The real frame, bow and arms remain visible. No screen-space housing
    // takes over; PhysicalScopeScene replaces only the original glass material.
}

void UBowScopeOptics::UpdateReticle(const UBowWeaponComponent& Bow,float Delta)
{
    FBowDrawRhythm Rhythm;
    const bool Drawing=Bow.GetDrawRhythm(Rhythm);
    const float Draw=Drawing?FMath::Clamp(Rhythm.Elapsed/FMath::Max(.001f,Rhythm.FullDrawSeconds),0.f,1.f):0.f;
    const float Response=1.f-FMath::Exp(-30.f*FMath::Max(0.f,Delta));
    Reticle.Draw=FMath::Lerp(Reticle.Draw,Draw,Response);
    Reticle.Full=FMath::Lerp(Reticle.Full,Drawing&&!Rhythm.bMagicArrowRain&&Draw>=1.f?1.f:0.f,Response);
    Reticle.Perfect=FMath::Lerp(Reticle.Perfect,Drawing&&Rhythm.bPerfect?1.f:0.f,Response);
    Reticle.Piercing=FMath::Lerp(Reticle.Piercing,Drawing&&Rhythm.bPiercingReady?1.f:0.f,Response);
    Reticle.bRain=Drawing&&Rhythm.bMagicArrowRain;Reticle.bRainValid=Rhythm.bMagicRainValid;
    Reticle.Release=Bow.ReleaseFeedbackAge>=0.f?FMath::Square(1.f-FMath::Clamp(Bow.ReleaseFeedbackAge/.24f,0.f,1.f)):0.f;
    Reticle.Age=Bow.VisualTime;
    const float Power=Bow.DisplayedScopeMagnification();
    const float Zoom=FMath::Clamp(FMath::Abs(Power-Reticle.Power)/FMath::Max(.001f,Delta)*.07f,0.f,1.f);
    Reticle.Zoom=FMath::Lerp(Reticle.Zoom,Zoom,1.f-FMath::Exp(-16.f*FMath::Max(0.f,Delta)));
    Reticle.Power=Power;
}

FVector2D UBowScopeOptics::CueOffset(const FGeometry&,float) const
{
    // Existing draw/rhythm/XP feedback keeps its normal HUD position.
    return FVector2D::ZeroVector;
}

int32 UBowScopeOptics::Paint(const FGeometry&,FSlateWindowElementList&,int32 Layer,const FLinearColor&) const
{
    return Layer; // Reticle now lives on the physical glass, underneath HUD.
}

float UBowWeaponComponent::PhysicalScopeAlpha() const
{
    return IsScopeOpticalPresentationEnabled()&&CanPresent(true)&&Optics?Optics->PresentationAlpha():0.f;
}

bool UBowWeaponComponent::GetPhysicalScopeView(FPhysicalScopeView& Out) const
{
    if(PhysicalScopeAlpha()<=0.f)return false;
    const auto* Sight=Part(TEXT("sight"));
    auto* Mesh=Sight?Sight->GetVisual():nullptr;
    if(!Mesh||!Mesh->GetStaticMesh()||!Mesh->IsVisible()||Mesh->bHiddenInGame||Mesh->bOwnerNoSee)return false;
    Out=FPhysicalScopeView();Out.Mesh=Mesh;Out.Style=EPhysicalScopeStyle::Peakwatch;
    Out.Glass=Mesh->GetMaterialIndex(TEXT("M_Peakwatch_Glass"));
    // Scope3to6V11/V12 authoring coordinates, centimetres. Its physical glass is
    // centred at the same mount point used by the bow's authored ADS alignment.
    const FTransform& T=Mesh->GetComponentTransform();
    Out.Center=T.TransformPosition(FVector(-.4,-10.223,24.3328));
    Out.Forward=T.TransformVectorNoScale(FVector::ForwardVector).GetSafeNormal();
    const FVector Right=T.TransformVector(FVector::RightVector),Up=T.TransformVector(FVector::UpVector);
    Out.Right=Right.GetSafeNormal();Out.Up=Up.GetSafeNormal();
    Out.Radius=FVector2D(BowScopeOptics::LensRadiusCM*Right.Size(),BowScopeOptics::LensRadiusCM*Up.Size());
    Out.RearDepth=FMath::Max(.2f,T.TransformVector(FVector::ForwardVector).Size());
    const auto& State=Optics->ReticleState();
    Out.BowDrawState=FLinearColor(State.Draw,State.Full,State.Perfect,State.Piercing);
    Out.BowRelease=State.Release;
    return Out.Glass!=INDEX_NONE&&!Out.Forward.IsNearlyZero();
}
