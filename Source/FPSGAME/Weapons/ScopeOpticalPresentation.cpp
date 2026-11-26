#include "../FPSGAMECharacter.h"
#include "Bow/BowWeaponComponent.h"
#include "RSH12OpticAssets.h"
#include "ThermalScopeAssets.h"
#include "KVScopeAssets.h"
#include "ThermalTargetSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "PhysicalScopeView.h"
#include "PistolDualWieldComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "SceneInterface.h"

namespace ScopeOpticalPresentation
{
static TAutoConsoleVariable<float> ZoomResponse(TEXT("fps.Scope.ZoomResponse"),24.f,
    TEXT("LPVO displayed magnification response per second; 0 snaps to the selected value."));
static TAutoConsoleVariable<float> Refraction(TEXT("fps.Scope.EdgeRefraction"),.65f,
    TEXT("Peripheral optic refraction strength, 0..1; 0 removes the post-process pass."));
static const FSoftObjectPath LensPath(TEXT("/Game/Weapons/ScopeOptics20260927/M_ScopePeripheralOptics.M_ScopePeripheralOptics"));

struct FGlassAndEtchSlots
{
    FName Glass;
    FName Etch;
};

static void ResolveFittedGlass(const UStaticMeshComponent& Mesh,FPhysicalScopeView& Out)
{
    // Matched against the actual glass and engraved sections of both fitted meshes.
    // LMG201 retains A762's slot names. M16 has a mount at index zero.
    static const FGlassAndEtchSlots LPVO[]={
        {TEXT("LPVO_Glass"),TEXT("LPVO_Reticle")}, {TEXT("M_LPVO_Glass"),TEXT("M_LPVO_Reticle")},
        {TEXT("A762_lpvo_1_6x_1"),TEXT("A762_lpvo_1_6x_0")}, {TEXT("SVD_lpvo_1_6x_1"),TEXT("SVD_lpvo_1_6x_0")},
        {TEXT("PKM14_lpvo_1_6x_1"),TEXT("PKM14_lpvo_1_6x_0")}};
    static const FGlassAndEtchSlots Prism[]={
        {TEXT("Scope2X_Glass"),TEXT("Scope2X_Reticle")}, {TEXT("M_Scope2X_Glass"),TEXT("M_Scope2X_Reticle")},
        {TEXT("A762_prism_scope_2x_1"),TEXT("A762_prism_scope_2x_0")}, {TEXT("SVD_prism_scope_2x_1"),TEXT("SVD_prism_scope_2x_0")},
        {TEXT("PKM14_prism_scope_2x_1"),TEXT("PKM14_prism_scope_2x_0")}};
    const TConstArrayView<FGlassAndEtchSlots> Slots=Out.Style==EPhysicalScopeStyle::LPVO?MakeArrayView(LPVO):MakeArrayView(Prism);
    for(const auto& Pair:Slots)
    {
        const int32 Glass=Mesh.GetMaterialIndex(Pair.Glass);
        if(Glass!=INDEX_NONE)
        {
            Out.Glass=Glass;
            Out.OriginalReticle=Mesh.GetMaterialIndex(Pair.Etch);
            return;
        }
    }
}
}

void AFPSGAMECharacter::InitializeScopeOptics()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    // One asynchronous request per character, with a weak owner callback. No
    // synchronous asset lookup or unbounded retry on ADS/paint/profile refresh.
    const TWeakObjectPtr<AFPSGAMECharacter> WeakOwner(this);
    const FSoftObjectPath ThermalPath(ThermalScopeAssets::Material);
    UAssetManager::GetStreamableManager().RequestAsyncLoad(ThermalPath,
        FStreamableDelegate::CreateLambda([WeakOwner,ThermalPath]()
        {
            auto* Owner=WeakOwner.Get();if(!Owner)return;
            if(auto* Source=Cast<UMaterialInterface>(ThermalPath.ResolveObject()))
                Owner->ThermalSceneMaterial=UMaterialInstanceDynamic::Create(Source,Owner);
            else UE_LOG(LogTemp,Error,TEXT("ThermalScope: failed to load post-process material %s"),*ThermalPath.ToString());
        }));
    UAssetManager::GetStreamableManager().RequestAsyncLoad(ScopeOpticalPresentation::LensPath,
        FStreamableDelegate::CreateLambda([WeakOwner]()
        {
            auto* Owner=WeakOwner.Get();if(!Owner)return;
            if(auto* Source=Cast<UMaterialInterface>(ScopeOpticalPresentation::LensPath.ResolveObject()))
                Owner->ScopeLensMaterial=UMaterialInstanceDynamic::Create(Source,Owner);
        }));
}

bool AFPSGAMECharacter::HasBowScope() const
{
    return Bow && Bow->IsEquipped() && Bow->HasOpticalSight();
}

float AFPSGAMECharacter::GetOpticMagnification() const
{
    if(Bow && Bow->IsEquipped())return Bow->ScopeMagnification();
    if(HasM24FactoryScope())return LPVOMagnification>3.5f?6.f:1.f;
    if(OpticVariant==KVScopeAssets::Id)return KVScopeAssets::Magnification(LPVOMagnification);
    if(HasThermalScope()){constexpr float Steps[]={1.5f,3.f,8.f};return Steps[FMath::Min<int32>(ThermalZoomIndex,2)];}
    // The RSH's retained EOTH model is now its fixed 1.5x tactical square sight.
    if(IsRSH12Weapon() && RSH12OpticAssets::Upgrade(OpticVariant)==RSH12OpticAssets::TacticalSquare)return 1.5f;
    return HasPSO1Scope()?4.f:(OpticVariant==TEXT("lpvo_1_6x")?LPVOMagnification:
        ((HasHandgunScope()||OpticVariant==TEXT("prism_scope_2x"))?2.f:1.f));
}

float AFPSGAMECharacter::GetDisplayedOpticMagnification() const
{
    if(Bow && Bow->IsEquipped())return Bow->DisplayedScopeMagnification();
    if(HasM24FactoryScope())return FMath::Clamp(DisplayedLPVOMagnification,1.f,6.f);
    return HasPSO1Scope()?4.f:(OpticVariant==TEXT("lpvo_1_6x")||OpticVariant==KVScopeAssets::Id||HasThermalScope())
        ?FMath::Clamp(DisplayedLPVOMagnification,1.f,8.f):GetOpticMagnification();
}

void AFPSGAMECharacter::AdvanceScopeOptics(float DeltaSeconds)
{
    const bool Changed=PresentedScopeVariant!=OpticVariant;
    PresentedScopeVariant=OpticVariant;
    const bool M24Dual=HasM24FactoryScope();
    const float Response=M24Dual?16.f:FMath::Max(0.f,ScopeOpticalPresentation::ZoomResponse.GetValueOnGameThread());
    const float TargetPower=GetOpticMagnification();
    if(Changed||(!M24Dual&&!IsAiming())||Response<=0.f)
        DisplayedLPVOMagnification=TargetPower;
    else
    {
        // Exponential interpolation is stable across frame rates and reversals.
        // FOV, aim sensitivity and the mechanical ring read this same value.
        DisplayedLPVOMagnification=FMath::Lerp(DisplayedLPVOMagnification,TargetPower,
            1.f-FMath::Exp(-Response*FMath::Max(0.f,DeltaSeconds)));
        if(FMath::Abs(DisplayedLPVOMagnification-TargetPower)<.001f)
            DisplayedLPVOMagnification=TargetPower;
    }
    if(LPVORing&&OpticVariant==TEXT("lpvo_1_6x"))
        LPVORing->SetRelativeRotation(FRotator(0,0,(DisplayedLPVOMagnification-1.f)*24.f));

    FVector2D Target(-WeaponSwayRotation.Y*.12f-GunKickRotation.Y*.06f,
        WeaponSwayRotation.X*.14f+GunKickRotation.X*.06f);
    Target+=FVector2D(WeaponBobPosition.X*1.5f,WeaponBobPosition.Y*1.5f);
    if(HasHandgunScope())Target*=.65f;
    Target=Target.GetClampedToMaxSize(HasPSO1Scope()?.028:.022);
    if(GetScopePresentationAlpha()<=0.f)Target=FVector2D::ZeroVector;
    ScopeEyeOffset=FMath::Lerp(ScopeEyeOffset,Target,1.f-FMath::Exp(-14.f*FMath::Max(0.f,DeltaSeconds)));
}

void AFPSGAMECharacter::UpdateScopeLensMaterial()
{
    if(!ScopeLensMaterial||!FirstPersonCamera)return;
    const auto* PC=Cast<APlayerController>(GetController());
    const float Alpha=PC&&PC->IsLocalController()&&!PC->bShowMouseCursor?GetScopePresentationAlpha():0.f;
    const float Strength=FMath::Clamp(ScopeOpticalPresentation::Refraction.GetValueOnGameThread(),0.f,1.f)
        *(HasM24FactoryScope()?.45f:1.f);
    // The handgun's smaller aperture has its own Slate coating and eye shadow.
    // Do not apply the rifle material's fixed 85%-diameter refraction to it.
    bool Apply=Alpha>UE_SMALL_NUMBER&&Strength>0.f&&!UsesPhysicalScope()&&!HasHandgunScope()&&!HasBowScope()&&!HasThermalScope();
    if(Apply)
    {
        const auto* World=GetWorld();
        const auto* Resource=World&&World->Scene?ScopeLensMaterial->GetMaterialResource(World->Scene->GetShaderPlatform()):nullptr;
        // Match the project's existing post-process contract: a default shader
        // fallback is not a transparent lens and must not replace the scene.
        Apply=Resource&&Resource->GetGameThreadShaderMap()&&Resource->IsGameThreadShaderMapComplete();
    }
    if(Apply)
    {
        ScopeLensMaterial->SetScalarParameterValue(TEXT("ScopeAlpha"),Alpha);
        ScopeLensMaterial->SetScalarParameterValue(TEXT("ScopePSO"),HasPSO1Scope()?1.f:0.f);
        ScopeLensMaterial->SetScalarParameterValue(TEXT("ScopeZoom"),GetDisplayedOpticMagnification());
        ScopeLensMaterial->SetScalarParameterValue(TEXT("Strength"),Strength);
        ScopeLensMaterial->SetVectorParameterValue(TEXT("EyeOffset"),FLinearColor(ScopeEyeOffset.X,ScopeEyeOffset.Y,0.f,0.f));
    }
    if(Apply!=bScopeLensApplied)
    {
        if(Apply)FirstPersonCamera->PostProcessSettings.AddBlendable(ScopeLensMaterial,1.f);
        else FirstPersonCamera->PostProcessSettings.RemoveBlendable(ScopeLensMaterial);
        bScopeLensApplied=Apply;
    }
}

void AFPSGAMECharacter::UpdateThermalPresentation()
{
    const auto* PC=Cast<APlayerController>(GetController());
    const float Alpha=HasThermalScope()&&PC&&PC->IsLocalController()&&!PC->bShowMouseCursor?GetScopePresentationAlpha():0.f;
    bool Apply=Alpha>UE_SMALL_NUMBER&&FirstPersonCamera&&ThermalSceneMaterial;
    if(Apply)
    {
        const auto* World=GetWorld();
        const auto* Resource=World&&World->Scene?ThermalSceneMaterial->GetMaterialResource(World->Scene->GetShaderPlatform()):nullptr;
        const auto* ShaderMap=Resource?Resource->GetGameThreadShaderMap():nullptr;
        // UE 5.8 compiles the needed post-process permutations when the renderer
        // requests them. Waiting for EVERY permutation before adding the pass
        // can prevent both this effect and its heat targets from ever starting.
        Apply=ShaderMap&&ShaderMap->IsValidForRendering();
    }
    if(Apply)ThermalSceneMaterial->SetScalarParameterValue(TEXT("ThermalAlpha"),Alpha);
    if(Apply!=bThermalApplied)
    {
        // The thermal pass belongs to the magnified capture. Keep the owner's
        // surrounding scene in its normal colour/exposure at every zoom level.
        if(FirstPersonCamera)FirstPersonCamera->PostProcessSettings.RemoveBlendable(ThermalSceneMaterial);
        bThermalApplied=Apply;
        if(auto* Targets=GetWorld()->GetSubsystem<UThermalTargetSubsystem>())Targets->SetViewer(FirstPersonCamera,Apply);
        UE_LOG(LogTemp,Display,TEXT("ThermalScope: lens heat targets %s (ADS=%.3f)"),Apply?TEXT("enabled"):TEXT("disabled"),Alpha);
    }
}
void AFPSGAMECharacter::ReleaseThermalPresentation()
{
    if(FirstPersonCamera&&ThermalSceneMaterial)FirstPersonCamera->PostProcessSettings.RemoveBlendable(ThermalSceneMaterial);
    if(GetWorld())if(auto* Targets=GetWorld()->GetSubsystem<UThermalTargetSubsystem>())Targets->SetViewer(FirstPersonCamera,false);
    bThermalApplied=false;
}

bool AFPSGAMECharacter::UsesPhysicalScope() const
{
    if(Bow&&Bow->IsEquipped())return Bow->IsScopeOpticalPresentationEnabled();
    return HasM24FactoryScope()||HasPSO1Scope()||HasHandgunScope()||HasThermalScope()
        ||(bHolographicOptic&&(OpticVariant==TEXT("lpvo_1_6x")||OpticVariant==TEXT("prism_scope_2x")||OpticVariant==KVScopeAssets::Id));
}

float AFPSGAMECharacter::GetPhysicalScopeMagnification() const
{
    // The bow lens is opaque as soon as it appears. Its ADS transition frames
    // the eyepiece; it is not a second zoom control.
    if(Bow && Bow->IsEquipped())
        return Bow->IsScopeOpticalPresentationEnabled()?Bow->DisplayedScopeMagnification():1.f;
    return UsesPhysicalScope()?FMath::Lerp(1.f,GetDisplayedOpticMagnification(),GetScopePresentationAlpha()):1.f;
}

UMaterialInterface* AFPSGAMECharacter::GetPhysicalThermalMaterial() const {return ThermalSceneMaterial.Get();}

bool AFPSGAMECharacter::GetPhysicalScopeView(FPhysicalScopeView& Out) const
{
    if(!UsesPhysicalScope())return false;
    Out=FPhysicalScopeView();
    if(Bow&&Bow->IsEquipped())return Bow->GetPhysicalScopeView(Out);
    Out.Style=HasM24FactoryScope()?EPhysicalScopeStyle::M24:HasThermalScope()?EPhysicalScopeStyle::Thermal:
        HasPSO1Scope()?EPhysicalScopeStyle::PSO:HasHandgunScope()?EPhysicalScopeStyle::Handgun:
        OpticVariant==TEXT("prism_scope_2x")?EPhysicalScopeStyle::Prism:
        OpticVariant==KVScopeAssets::Id?EPhysicalScopeStyle::KV:EPhysicalScopeStyle::LPVO;
    const TCHAR* GlassName=Out.Style==EPhysicalScopeStyle::M24?TEXT("M24_ScopeGlass"):
        Out.Style==EPhysicalScopeStyle::KV?TEXT("att_lens_scope"):
        Out.Style==EPhysicalScopeStyle::PSO?TEXT("PSO1_OpticalGlass"):
        Out.Style==EPhysicalScopeStyle::Handgun?TEXT("DW715_CoatedGlass"):TEXT("Thermal_Display");
    if(HasSVDFactoryScope())
    {
        if(!AKMViewmodel||!AKMViewmodel->GetSkeletalMeshAsset())return false;
        Out.Style=EPhysicalScopeStyle::SVDFactory;
        Out.Mesh=AKMViewmodel;
        Out.Center=AKMViewmodel->GetSocketLocation(TEXT("WPN_RearSight"));
        Out.Forward=(AKMViewmodel->GetSocketLocation(TEXT("WPN_FrontSight"))-Out.Center).GetSafeNormal();
        const FVector RootUp=AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).GetUnitAxis(EAxis::Z);
        Out.Right=FVector::CrossProduct(RootUp,Out.Forward).GetSafeNormal();
        Out.Up=FVector::CrossProduct(Out.Forward,Out.Right).GetSafeNormal();
        // The rear marker is at the rubber mouth, 3.182 cm behind the display.
        Out.Center+=Out.Forward*3.182;
        Out.Radius=FVector2D(1.56,1.56);Out.RearDepth=1.f;
        // Factory glass is part of the native skeletal assembly.
        Out.Glass=AKMViewmodel->GetMaterialIndex(TEXT("SM_SVD_ScopeLens_001"));
    }
    else
    {
        auto* Mounted=IsLoneLeftHandRig()&&DualPistols?DualPistols->LonePhysicalOptic():HolographicOptic.Get();
        if(!Mounted||!Mounted->GetStaticMesh())return false;
        Out.Mesh=Mounted;
        const UStaticMesh* OpticalStaticMesh=Mounted->GetStaticMesh();
        const auto* Rear=OpticalStaticMesh->FindSocket(TEXT("SightRear"));
        if(!Rear)Rear=OpticalStaticMesh->FindSocket(TEXT("AimCenter"));
        const auto* Front=OpticalStaticMesh->FindSocket(TEXT("SightFront"));
        const auto* Up=OpticalStaticMesh->FindSocket(TEXT("SightUp"));
        FVector R=Rear?Rear->RelativeLocation:OpticLocalAimPoint();
        const FVector F=Front?(Front->RelativeLocation-R).GetSafeNormal():FVector::ForwardVector;
        const FVector U=Up?(Up->RelativeLocation-R).GetSafeNormal():FVector::UpVector;
        const FVector Side=FVector::CrossProduct(U,F).GetSafeNormal();
        const FVector Top=FVector::CrossProduct(F,Side).GetSafeNormal();
        const float NominalLength=Out.Style==EPhysicalScopeStyle::M24?41.28978f:
            Out.Style==EPhysicalScopeStyle::LPVO?24.25f:Out.Style==EPhysicalScopeStyle::Prism?12.25f:
            Out.Style==EPhysicalScopeStyle::KV?22.65478f:Out.Style==EPhysicalScopeStyle::PSO?30.04649f:9.9f;
        const float AuthoredScale=Rear&&Front?FVector::Distance(Rear->RelativeLocation,Front->RelativeLocation)/NominalLength:1.f;
        const float Radius=Out.Style==EPhysicalScopeStyle::M24?2.472f:Out.Style==EPhysicalScopeStyle::LPVO?1.79f:
            Out.Style==EPhysicalScopeStyle::Prism?1.585f:Out.Style==EPhysicalScopeStyle::KV?1.98f:
            Out.Style==EPhysicalScopeStyle::PSO?1.56f:Out.Style==EPhysicalScopeStyle::Handgun?1.35f:1.72f;
        // The thermal screen and PSO glass sit inside their original eyecups.
        if(Out.Style==EPhysicalScopeStyle::Thermal)R+=F*(2.6f*AuthoredScale);
        if(Out.Style==EPhysicalScopeStyle::PSO)R+=F*3.182f;
        const FTransform& T=Mounted->GetComponentTransform();
        Out.Center=T.TransformPosition(R);Out.Forward=T.TransformVectorNoScale(F).GetSafeNormal();
        const FVector X=T.TransformVector(Side*AuthoredScale),Y=T.TransformVector(Top*AuthoredScale);
        Out.Right=X.GetSafeNormal();Out.Up=Y.GetSafeNormal();
        Out.Radius=FVector2D(Radius*X.Size(),(Out.Style==EPhysicalScopeStyle::Thermal?1.4f:Radius)*Y.Size());
        Out.RearDepth=FMath::Max(.2f,T.TransformVector(F*AuthoredScale).Size());
        if(Out.Style==EPhysicalScopeStyle::LPVO||Out.Style==EPhysicalScopeStyle::Prism)
            ScopeOpticalPresentation::ResolveFittedGlass(*Mounted,Out);
        else Out.Glass=Mounted->GetMaterialIndex(GlassName);
        if(Out.Style==EPhysicalScopeStyle::LPVO)
        {
            // Fitted copies can bake their scale into the mesh. Project the local
            // housing bounds onto the rear plane so the capture covers the full disk,
            // even on copies without a front socket. The mount can extend below it.
            const FBox Bounds=OpticalStaticMesh->GetBoundingBox();
            const FVector Extent=Bounds.GetExtent(), Offset=Bounds.GetCenter()-R;
            const double SideSpan=FVector::DotProduct(Extent,Side.GetAbs())+FMath::Abs(FVector::DotProduct(Offset,Side));
            const double TopSpan=FVector::DotProduct(Extent,Top.GetAbs())+FMath::Abs(FVector::DotProduct(Offset,Top));
            // A circular disk fits within both spans. The shorter one excludes the rail.
            const double Rim=FMath::Max(double(Radius*AuthoredScale),FMath::Min(SideSpan,TopSpan));
            Out.CaptureRadiusScale=Rim/(Radius*AuthoredScale);
            // Front and rear glass are separate planes in a single material section.
            Out.RearDepth=FMath::Max(Out.RearDepth,float(T.TransformVector(F*FVector::DotProduct(Offset,F)).Size()));
        }
    }
    // The SVCh fitting has its own lighter engraving on the shared KV glass.
    if(Out.Style==EPhysicalScopeStyle::KV && ActiveInventoryWeaponDefinition==TEXT("ue_svch"))
        Out.Style=EPhysicalScopeStyle::SVChKV;
    return Out.Mesh&&Out.Glass!=INDEX_NONE&&Out.Mesh->IsVisible()&&!Out.Mesh->bHiddenInGame&&!Out.Forward.IsNearlyZero();
}
