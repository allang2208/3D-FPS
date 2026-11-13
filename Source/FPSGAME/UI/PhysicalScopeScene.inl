// Included by LPVOScopeWidget.cpp. One owner-local capture for guns and Peakwatch.
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Weapons/PhysicalScopeView.h"
#include "Camera/CameraComponent.h"
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
static TAutoConsoleVariable<int32> Resolution(TEXT("fps.Scope.CaptureResolution"),1024,
    TEXT("Owner-local physical lens resolution, 512..1536; one capture during ADS only."));
static const FSoftObjectPath LensPath(TEXT("/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeLens.M_PhysicalScopeLens"));
static const FSoftObjectPath PeakwatchLensPath(TEXT("/Game/Weapons/SharedPhysicalOptics20261030/M_PeakwatchClearLens.M_PeakwatchClearLens"));
static const FSoftObjectPath HidePath(TEXT("/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeHideReticle.M_PhysicalScopeHideReticle"));
static UObject* MeshAsset(UMeshComponent* Mesh)
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
        const double FPCorrection=Optic.Mesh->FirstPersonPrimitiveType==EFirstPersonPrimitiveType::FirstPerson&&Camera->bEnableFirstPersonFieldOfView
            ?FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView)*.5)/FMath::Tan(FMath::DegreesToRadians(Camera->FirstPersonFieldOfView)*.5):1.;
        double Radius=16.;
        for(int X:{-1,1})for(int Y:{-1,1})
        {
            FVector2D Pixel;
            const FVector Edge=Optic.Center+Optic.Right*(X*Optic.Radius.X)+Optic.Up*(Y*Optic.Radius.Y);
            if(!FSceneView::ProjectWorldToScreen(Edge,View,VP,Pixel)){RestoreGlass();return;}
            const FVector2D Offset=(Pixel-ScreenCenter)*FPCorrection;
            Radius=FMath::Max(Radius,FMath::Max(FMath::Abs(Offset.X),FMath::Abs(Offset.Y)));
        }
        Radius*=1.08;
        const float TanHalfFOV=float(Radius)/(MainFocal*Pawn->GetPhysicalScopeMagnification());
        if(BoundOptic.Get()!=Optic.Mesh||BoundAsset.Get()!=PhysicalScopeScene::MeshAsset(Optic.Mesh)
            ||GlassSlot!=Optic.Glass||Optic.Mesh->GetMaterial(Optic.Glass)!=Lens)
        {
            RestoreGlass();BoundOptic=Optic.Mesh;BoundAsset=PhysicalScopeScene::MeshAsset(Optic.Mesh);
            GlassSlot=Optic.Glass;ReticleSlot=Optic.OriginalReticle;
            OriginalGlass.Reset(Optic.Mesh->GetMaterial(GlassSlot));
            if(ReticleSlot!=INDEX_NONE)OriginalReticle.Reset(Optic.Mesh->GetMaterial(ReticleSlot));
        }
        const int32 BaseSize=FMath::Clamp(PhysicalScopeScene::Resolution.GetValueOnGameThread(),512,1536);
        // Size the enlarged bow aperture once from the viewport, not every frame of the draw.
        const int32 Size=Peakwatch?FMath::Clamp(FMath::DivideAndRoundUp(FMath::Min(View.Width(),View.Height()),128)*128,BaseSize,2560):BaseSize;
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
            Capture->HiddenActors.Add(Pawn);Capture->RegisterComponentWithWorld(World);CapturedPawn=Pawn;
        }
        if(Target->SizeX!=Size){Target->ResizeTarget(Size,Size);bWasActive=false;}
        if(!bWasActive)Lens->SetTextureParameterValue(TEXT("ScopeScene"),Target.Get());
        Capture->ShowFlags.SetTemporalAA(!Peakwatch&&GetDefault<USceneCaptureComponent2D>()->ShowFlags.TemporalAA);
        // Ordinary optics stay scene-linear. The thermal pass runs only in this
        // capture, whose final HDR output also remains linear for the mesh lens.
        Capture->CaptureSource=Thermal?SCS_FinalColorHDR:SCS_SceneColorHDRNoAlpha;
        Capture->FOVAngle=FMath::RadiansToDegrees(2.f*FMath::Atan(TanHalfFOV));
        if(Peakwatch)
        {
            const FMatrix ViewToWorld=Projection.ViewRotationMatrix.GetTransposed();
            const FRotator Rotation=FRotationMatrix::MakeFromXZ(ViewToWorld.TransformVector(FVector::UpVector),
                ViewToWorld.TransformVector(FVector::RightVector)).Rotator();
            Capture->SetWorldLocationAndRotation(Projection.ViewOrigin,Rotation);
        }
        else Capture->SetWorldLocationAndRotation(Camera->GetComponentLocation(),Camera->GetComponentRotation());
        Capture->PostProcessSettings=Camera->PostProcessSettings;
        Capture->PostProcessBlendWeight=Thermal?1.f:Camera->PostProcessBlendWeight;
        if(Thermal)Capture->PostProcessSettings.AddBlendable(ThermalMaterial,1.f);
        Capture->bCameraCutThisFrame=!bWasActive;Capture->CaptureSceneDeferred();
        Lens->SetVectorParameterValue(TEXT("ScreenToLens"),FLinearColor(View.Width()/(2.f*Radius),View.Height()/(2.f*Radius),0,0));
        Lens->SetVectorParameterValue(TEXT("LensCenter"),FLinearColor(Optic.Center.X,Optic.Center.Y,Optic.Center.Z));
        Lens->SetVectorParameterValue(TEXT("LensForward"),FLinearColor(Optic.Forward.X,Optic.Forward.Y,Optic.Forward.Z));
        Lens->SetScalarParameterValue(TEXT("RearDepth"),Optic.RearDepth);
        Lens->SetScalarParameterValue(TEXT("CaptureTanHalfFOV"),TanHalfFOV);
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
