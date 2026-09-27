#include "../FPSGAMECharacter.h"
#include "Bow/BowWeaponComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "SceneInterface.h"

namespace ScopeOpticalPresentation
{
static TAutoConsoleVariable<float> ZoomResponse(TEXT("fps.Scope.ZoomResponse"),24.f,
    TEXT("LPVO displayed magnification response per second; 0 snaps to the selected value."));
static TAutoConsoleVariable<float> Refraction(TEXT("fps.Scope.EdgeRefraction"),.65f,
    TEXT("Peripheral optic refraction strength, 0..1; 0 removes the post-process pass."));
static const FSoftObjectPath LensPath(TEXT("/Game/Weapons/ScopeOptics20260927/M_ScopePeripheralOptics.M_ScopePeripheralOptics"));
}

void AFPSGAMECharacter::InitializeScopeOptics()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    // One asynchronous request per character, with a weak owner callback. No
    // synchronous asset lookup or unbounded retry on ADS/paint/profile refresh.
    const TWeakObjectPtr<AFPSGAMECharacter> WeakOwner(this);
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
    return HasPSO1Scope()?4.f:(OpticVariant==TEXT("lpvo_1_6x")?LPVOMagnification:
        ((HasHandgunScope()||OpticVariant==TEXT("prism_scope_2x"))?2.f:1.f));
}

float AFPSGAMECharacter::GetDisplayedOpticMagnification() const
{
    if(Bow && Bow->IsEquipped())return Bow->ScopeMagnification();
    return HasPSO1Scope()?4.f:OpticVariant==TEXT("lpvo_1_6x")
        ?FMath::Clamp(DisplayedLPVOMagnification,1.f,6.f):GetOpticMagnification();
}

void AFPSGAMECharacter::AdvanceScopeOptics(float DeltaSeconds)
{
    const bool Changed=PresentedScopeVariant!=OpticVariant;
    PresentedScopeVariant=OpticVariant;
    const float Response=FMath::Max(0.f,ScopeOpticalPresentation::ZoomResponse.GetValueOnGameThread());
    if(Changed||OpticVariant!=TEXT("lpvo_1_6x")||!IsAiming()||Response<=0.f)
        DisplayedLPVOMagnification=LPVOMagnification;
    else
    {
        // Exponential interpolation is stable across frame rates and reversals.
        // FOV, aim sensitivity and the mechanical ring read this same value.
        DisplayedLPVOMagnification=FMath::Lerp(DisplayedLPVOMagnification,LPVOMagnification,
            1.f-FMath::Exp(-Response*FMath::Max(0.f,DeltaSeconds)));
        if(FMath::Abs(DisplayedLPVOMagnification-LPVOMagnification)<.001f)
            DisplayedLPVOMagnification=LPVOMagnification;
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
    const float Strength=FMath::Clamp(ScopeOpticalPresentation::Refraction.GetValueOnGameThread(),0.f,1.f);
    // The handgun's smaller aperture has its own Slate coating and eye shadow.
    // Do not apply the rifle material's fixed 85%-diameter refraction to it.
    bool Apply=Alpha>UE_SMALL_NUMBER&&Strength>0.f&&!HasHandgunScope()&&!HasBowScope();
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
