// Included by LPVOScopeWidget.cpp. One owner-local capture for guns and Peakwatch.
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Weapons/PhysicalScopeView.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SceneView.h"
#include "UObject/StrongObjectPtr.h"

namespace PhysicalScopeScene
{
// Registered only while the view actually replaces slots. Lookup follows the mesh
// across unpossess/rejoin until its original surfaces have been restored.
static TArray<const FPhysicalScopeScene*> BoundScenes;
static TAutoConsoleVariable<int32> Resolution(TEXT("fps.Scope.CaptureResolution"),1024,
    TEXT("Owner-local ADS capture resolution ceiling, 512..1536. Peakwatch allows up to twice this for its larger aperture."));
static const FSoftObjectPath LensPath(TEXT("/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeLens.M_PhysicalScopeLens"));
static const FSoftObjectPath PeakwatchLensPath(TEXT("/Game/Weapons/SharedPhysicalOptics20261030/M_PeakwatchVariableLens.M_PeakwatchVariableLens"));
static const FSoftObjectPath HidePath(TEXT("/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeHideReticle.M_PhysicalScopeHideReticle"));
static UObject* MeshAsset(const UMeshComponent* Mesh)
{
    if(auto* Static=Cast<UStaticMeshComponent>(Mesh))return Static->GetStaticMesh();
    if(auto* Skin=Cast<USkeletalMeshComponent>(Mesh))return Skin->GetSkeletalMeshAsset();
    return nullptr;
}
}

struct FPhysicalScopeScene
{
    TWeakObjectPtr<APlayerController> Controller;
    TWeakObjectPtr<AFPSGAMECharacter> CapturedPawn;
    TWeakObjectPtr<UMeshComponent> BoundOptic;
    TWeakObjectPtr<UObject> BoundAsset;
    TStrongObjectPtr<UMaterialInterface> OriginalGlass,OriginalReticle,HiddenReticle;
    TStrongObjectPtr<UMaterialInstanceDynamic> DefaultLens,PeakwatchLens;
    UMaterialInstanceDynamic* Lens=nullptr;
    TStrongObjectPtr<USceneCaptureComponent2D> Capture;
    TStrongObjectPtr<UTextureRenderTarget2D> Target;
    TSharedPtr<FStreamableHandle> MaterialLoad;
    FDelegateHandle UpdateHandle;
    int32 GlassSlot=INDEX_NONE,ReticleSlot=INDEX_NONE;
    bool bLoadFinished=false,bWasActive=false;

    explicit FPhysicalScopeScene(APlayerController* PC):Controller(PC)
    {
        MaterialLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
            TArray<FSoftObjectPath>{PhysicalScopeScene::LensPath,PhysicalScopeScene::PeakwatchLensPath,PhysicalScopeScene::HidePath});
        UpdateHandle=FWorldDelegates::OnWorldPostActorTick.AddRaw(this,&FPhysicalScopeScene::Update);
    }
    ~FPhysicalScopeScene()
    {
        FWorldDelegates::OnWorldPostActorTick.Remove(UpdateHandle);Release();
        if(MaterialLoad.IsValid())MaterialLoad->CancelHandle();
    }
    void RestoreGlass()
    {
        if(auto* Optic=BoundOptic.Get();Optic&&PhysicalScopeScene::MeshAsset(Optic)==BoundAsset.Get())
        {
            if(GlassSlot!=INDEX_NONE&&Optic->GetMaterial(GlassSlot)==Lens)Optic->SetMaterial(GlassSlot,OriginalGlass.Get());
            if(ReticleSlot!=INDEX_NONE&&Optic->GetMaterial(ReticleSlot)==HiddenReticle.Get())Optic->SetMaterial(ReticleSlot,OriginalReticle.Get());
        }
        if(GlassSlot!=INDEX_NONE)PhysicalScopeScene::BoundScenes.RemoveSingleSwap(this);
        BoundOptic.Reset();BoundAsset.Reset();OriginalGlass.Reset();OriginalReticle.Reset();
        GlassSlot=ReticleSlot=INDEX_NONE;bWasActive=false;
    }
    void Release()
    {
        RestoreGlass();
        if(Capture.IsValid())Capture->DestroyComponent();
        if(DefaultLens.IsValid())DefaultLens->SetTextureParameterValue(TEXT("ScopeScene"),nullptr);
        if(PeakwatchLens.IsValid())PeakwatchLens->SetTextureParameterValue(TEXT("ScopeScene"),nullptr);
        Lens=nullptr;
        Capture.Reset();Target.Reset();CapturedPawn.Reset();
    }
    void Update(UWorld* World,ELevelTick TickType,float Delta)
    {
        auto* PC=Controller.Get();if(!PC||PC->GetWorld()!=World)return;
        if(!bLoadFinished&&MaterialLoad.IsValid()&&MaterialLoad->HasLoadCompleted())
        {
            bLoadFinished=true;
            if(auto* Source=Cast<UMaterialInterface>(PhysicalScopeScene::LensPath.ResolveObject()))
                DefaultLens.Reset(UMaterialInstanceDynamic::Create(Source,GetTransientPackage()));
            if(auto* Source=Cast<UMaterialInterface>(PhysicalScopeScene::PeakwatchLensPath.ResolveObject()))
                PeakwatchLens.Reset(UMaterialInstanceDynamic::Create(Source,GetTransientPackage()));
            HiddenReticle.Reset(Cast<UMaterialInterface>(PhysicalScopeScene::HidePath.ResolveObject()));
            if(!DefaultLens.IsValid()||!PeakwatchLens.IsValid()||!HiddenReticle.IsValid())UE_LOG(LogTemp,Error,TEXT("Physical scope materials could not be loaded"));
        }
        auto* Pawn=Cast<AFPSGAMECharacter>(PC->GetPawn());
        if(!Pawn||!PC->IsLocalController()||!Pawn->UsesPhysicalScope())
        {if(Capture.IsValid()||BoundOptic.IsValid())Release();return;}
        if(Capture.IsValid()&&CapturedPawn.Get()!=Pawn)Release();
        const auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
        const float Alpha=Pawn->GetScopePresentationAlpha();
        auto* Camera=Pawn->FirstPersonCamera.Get();FPhysicalScopeView Optic;
        if(!Camera||!HiddenReticle.IsValid()||PC->bShowMouseCursor||PC->GetViewTarget()!=Pawn
            ||Pawn->IsAmmoWheelOpen()||(Body&&Body->IsThirdPersonViewEnabled())||Alpha<=.001f
            ||!Pawn->GetPhysicalScopeView(Optic))
        {RestoreGlass();return;}
        const bool Peakwatch=Optic.Style==EPhysicalScopeStyle::Peakwatch;
        auto* SelectedLens=Peakwatch?PeakwatchLens.Get():DefaultLens.Get();
        if(SelectedLens!=Lens){RestoreGlass();Lens=SelectedLens;}
        if(!Lens)return;
        const bool Thermal=Optic.Style==EPhysicalScopeStyle::Thermal;
        auto* ThermalMaterial=Thermal?Pawn->GetPhysicalThermalMaterial():nullptr;
        if(Thermal&&!ThermalMaterial){RestoreGlass();return;}
        auto* Local=PC->GetLocalPlayer();FSceneViewProjectionData Projection;
        if(!Local||!Local->ViewportClient||!Local->ViewportClient->Viewport
            ||!Local->GetProjectionData(Local->ViewportClient->Viewport,Projection))
        {RestoreGlass();return;}
        const FIntRect View=Projection.GetConstrainedViewRect();
        const float MainFocal=float(Projection.ProjectionMatrix.M[0][0])*View.Width()*.5f;
        if(View.Width()<=0||View.Height()<=0||MainFocal<=0.f){RestoreGlass();return;}
        const FMatrix VP=Projection.ComputeViewProjectionMatrix();
        const FVector2D ScreenCenter(View.Min.X+View.Width()*.5,View.Min.Y+View.Height()*.5);
        // First-person geometry can use its own projection. Account for that
        // without changing its pose, scale, near-plane or camera settings.
        const auto* CameraManager=PC->PlayerCameraManager.Get();
        const FMinimalViewInfo* POV=CameraManager?&CameraManager->GetCameraCacheView():nullptr;
        const double FPCorrection=POV&&POV->bUseFirstPersonParameters&&Optic.Mesh->FirstPersonPrimitiveType==EFirstPersonPrimitiveType::FirstPerson
            ?POV->CalculateFirstPersonFOVCorrectionFactor():1.;
        // Both PSO meshes retain a painted, opaque eyepiece 2.234 cm in front
        // of the original glass. Seat the active disk just ahead of that face;
        // the raised rubber cup still masks the edge by depth. Keep its etching
        // in the authored local plane and project the capture at the visible disk.
        const bool PaintedEyepiece=Optic.Style==EPhysicalScopeStyle::PSO||Optic.Style==EPhysicalScopeStyle::SVDFactory;
        const FVector GlassOffset=PaintedEyepiece?-Optic.Forward*(2.4*Optic.Radius.X/1.56):FVector::ZeroVector;
        double Radius=16.;
        for(int X:{-1,1})for(int Y:{-1,1})
        {
            FVector2D Pixel;
            const FVector Edge=Optic.Center+GlassOffset+(Optic.Right*(X*Optic.Radius.X)+Optic.Up*(Y*Optic.Radius.Y))*Optic.CaptureRadiusScale;
            if(!FSceneView::ProjectWorldToScreen(Edge,View,VP,Pixel)){RestoreGlass();return;}
            const FVector2D Offset=(Pixel-ScreenCenter)*FPCorrection;
            Radius=FMath::Max(Radius,FMath::Max(FMath::Abs(Offset.X),FMath::Abs(Offset.Y)));
        }
        Radius*=1.08;
        const float DisplayPower=Pawn->GetPhysicalScopeMagnification();
        // Magnification changes the captured scene. The etching is on the glass.
        const float TanHalfFOV=float(Radius)/(MainFocal*DisplayPower);
        if(BoundOptic.Get()!=Optic.Mesh||BoundAsset.Get()!=PhysicalScopeScene::MeshAsset(Optic.Mesh)
            ||GlassSlot!=Optic.Glass||ReticleSlot!=Optic.OriginalReticle||Optic.Mesh->GetMaterial(Optic.Glass)!=Lens
            ||(ReticleSlot!=INDEX_NONE&&Optic.Mesh->GetMaterial(ReticleSlot)!=HiddenReticle.Get()))
        {
            RestoreGlass();BoundOptic=Optic.Mesh;BoundAsset=PhysicalScopeScene::MeshAsset(Optic.Mesh);
            GlassSlot=Optic.Glass;ReticleSlot=Optic.OriginalReticle;
            PhysicalScopeScene::BoundScenes.Add(this);
            OriginalGlass.Reset(Optic.Mesh->GetMaterial(GlassSlot));
            if(ReticleSlot!=INDEX_NONE)OriginalReticle.Reset(Optic.Mesh->GetMaterial(ReticleSlot));
        }
        const int32 BaseSize=FMath::Clamp(PhysicalScopeScene::Resolution.GetValueOnGameThread(),512,1536);
        // Budget for the glass in this player's viewport. Using a stable size
        // avoids target reallocations during sway, ADS transitions and zoom.
        const int32 ShortSide=FMath::Min(View.Width(),View.Height());
        const int32 ViewBudget=64*FMath::DivideAndRoundUp(ShortSide*3,4*64);
        const int32 Size=FMath::Clamp(ViewBudget,384,Peakwatch?FMath::Min(2560,2*BaseSize):BaseSize);
        if(!Capture.IsValid())
        {
            Target.Reset(NewObject<UTextureRenderTarget2D>(GetTransientPackage(),NAME_None,RF_Transient));
            Target->RenderTargetFormat=RTF_RGBA16f;Target->ClearColor=FLinearColor::Black;
            Target->InitAutoFormat(Size,Size);Target->UpdateResourceImmediate(true);
            Capture.Reset(NewObject<USceneCaptureComponent2D>(Pawn,NAME_None,RF_Transient));
            Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;
            Capture->bAlwaysPersistRenderingState=true;Capture->TextureTarget=Target.Get();
            Capture->bMainViewFamily=true;Capture->bInheritMainViewCameraPostProcessSettings=false;
            Capture->bMainViewCamera=false;Capture->bMainViewResolution=false;
            Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetDepthOfField(false);
            Capture->ShowFlags.SetScreenPercentage(false);
            Capture->ShowFlags.SetScreenSpaceReflections(false);
            Capture->ShowFlags.SetContactShadows(false);
            Capture->HiddenActors.Add(Pawn);Capture->RegisterComponentWithWorld(World);CapturedPawn=Pawn;
        }
        if(Target->SizeX!=Size){Target->ResizeTarget(Size,Size);bWasActive=false;}
        if(!bWasActive)Lens->SetTextureParameterValue(TEXT("ScopeScene"),Target.Get());
        Capture->ShowFlags.SetTemporalAA(false);
        // Ordinary optics stay scene-linear. The thermal pass runs only in this
        // capture, whose final HDR output also remains linear for the mesh lens.
        Capture->CaptureSource=Thermal?SCS_FinalColorHDR:SCS_SceneColorHDRNoAlpha;
        Capture->FOVAngle=FMath::RadiansToDegrees(2.f*FMath::Atan(TanHalfFOV));
        // Use the same view (including camera modifiers) as the glass projection.
        const FMatrix ViewToWorld=Projection.ViewRotationMatrix.GetTransposed();
        const FRotator Rotation=FRotationMatrix::MakeFromXZ(ViewToWorld.TransformVector(FVector::UpVector),
            ViewToWorld.TransformVector(FVector::RightVector)).Rotator();
        Capture->SetWorldLocationAndRotation(Projection.ViewOrigin,Rotation);
        Capture->PostProcessSettings=Camera->PostProcessSettings;
        Capture->PostProcessBlendWeight=Thermal?1.f:Camera->PostProcessBlendWeight;
        if(Thermal)Capture->PostProcessSettings.AddBlendable(ThermalMaterial,1.f);
        Capture->bCameraCutThisFrame=!bWasActive;Capture->CaptureSceneDeferred();
        // Store the capture FOV alongside its screen scale for the coverage readback.
        Lens->SetVectorParameterValue(TEXT("ScreenToLens"),FLinearColor(View.Width()/(2.f*Radius),View.Height()/(2.f*Radius),TanHalfFOV,0));
        // The animated mesh supplies each fragment's local position, including during
        // the M24 bolt cycle. These two planes express it in rear-glass radii.
        const FTransform& Mount=Optic.Mesh->GetComponentTransform();
        const FVector LocalCenter=Mount.InverseTransformPosition(Optic.Center);
        const double GlassRadius=FMath::Max(UE_SMALL_NUMBER,FMath::Min(Optic.Radius.X,Optic.Radius.Y));
        const auto EtchPlane=[&](const FVector& Axis)
        {
            const FVector Coeff=Mount.InverseTransformVectorNoScale(Axis)*Mount.GetScale3D()/GlassRadius;
            return FLinearColor(Coeff.X,Coeff.Y,Coeff.Z,-FVector::DotProduct(LocalCenter,Coeff));
        };
        Lens->SetVectorParameterValue(TEXT("ReticlePlaneU"),EtchPlane(Optic.Right));
        Lens->SetVectorParameterValue(TEXT("ReticlePlaneV"),EtchPlane(-Optic.Up));
        Lens->SetVectorParameterValue(TEXT("LensCenter"),FLinearColor(Optic.Center.X,Optic.Center.Y,Optic.Center.Z));
        Lens->SetVectorParameterValue(TEXT("LensForward"),FLinearColor(Optic.Forward.X,Optic.Forward.Y,Optic.Forward.Z));
        if(!Peakwatch)
            Lens->SetVectorParameterValue(TEXT("EyepieceOffset"),FLinearColor(GlassOffset.X,GlassOffset.Y,GlassOffset.Z));
        Lens->SetScalarParameterValue(TEXT("RearDepth"),Optic.RearDepth);
        Lens->SetScalarParameterValue(TEXT("ReticleStyle"),static_cast<float>(Optic.Style));
        Lens->SetVectorParameterValue(TEXT("BowDrawState"),Optic.BowDrawState);
        Lens->SetScalarParameterValue(TEXT("BowRelease"),Optic.BowRelease);
        // Alpha also gates binding. Once the bow glass is in view, a translucent
        // crossfade would show the unmagnified world through its magnified image.
        Lens->SetScalarParameterValue(TEXT("LensBlend"),Peakwatch?1.f:Alpha);
        if(Optic.Mesh->GetMaterial(GlassSlot)!=Lens)Optic.Mesh->SetMaterial(GlassSlot,Lens);
        if(ReticleSlot!=INDEX_NONE&&Optic.Mesh->GetMaterial(ReticleSlot)!=HiddenReticle.Get())Optic.Mesh->SetMaterial(ReticleSlot,HiddenReticle.Get());
        bWasActive=true;
    }
};

UMaterialInterface* PhysicalScopeMaterials::ForWorldEquipment(const UMeshComponent* Mesh,int32 Slot,UMaterialInterface* Current)
{
    for(const auto* Scene:PhysicalScopeScene::BoundScenes)
    {
        if(Scene->BoundOptic.Get()!=Mesh||PhysicalScopeScene::MeshAsset(Mesh)!=Scene->BoundAsset.Get())continue;
        if(Slot==Scene->GlassSlot&&Current==Scene->Lens)return Scene->OriginalGlass.Get();
        if(Slot==Scene->ReticleSlot&&Current==Scene->HiddenReticle.Get())return Scene->OriginalReticle.Get();
    }
    return Current;
}
