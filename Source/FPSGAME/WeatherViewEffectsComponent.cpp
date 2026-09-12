#include "WeatherViewEffectsComponent.h"
#include "FPSWeatherManager.h"
#include "FPSGAMECharacter.h"
#include "WeatherSurfaceComponent.h"
#include "WeatherPresentationValidation.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "UI/ColdSteelStatusModel.h"
#include "HAL/IConsoleManager.h"

static TAutoConsoleVariable<float> CVarScreenRain(TEXT("fps.ScreenRain"),.75f,TEXT("Screen edge water strength, 0 disables."),ECVF_Scalability);
static TAutoConsoleVariable<float> CVarWeaponWetness(TEXT("fps.WeaponWetness"),1.f,TEXT("Weapon wet material strength, 0 disables."),ECVF_Scalability);

namespace
{
UObject* SourceMesh(UMeshComponent* Mesh)
{
    if(auto* Skel=Cast<USkeletalMeshComponent>(Mesh))return Skel->GetSkinnedAsset();
    if(auto* Static=Cast<UStaticMeshComponent>(Mesh))return Static->GetStaticMesh();
    return nullptr;
}
void RestoreBinding(FWeatherViewMaterial& Binding)
{
    auto* Mesh=Binding.Mesh.Get();
    if(Mesh&&Mesh->GetMaterial(Binding.Slot)==Binding.Wet)
        Mesh->SetMaterial(Binding.Slot,SourceMesh(Mesh)==Binding.MeshAsset.Get()?Binding.Original.Get():nullptr);
}
}

UWeatherViewEffectsComponent::UWeatherViewEffectsComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UWeatherViewEffectsComponent::Initialize(UWeatherPresentationAssets* InAssets)
{
    Assets=InAssets;
    if(Assets&&Assets->ScreenMaterial)
    {
        LensMaterial=UMaterialInstanceDynamic::Create(Assets->ScreenMaterial,this);
        PostProcess=NewObject<UPostProcessComponent>(GetOwner(),TEXT("RainLensPostProcess"));
        PostProcess->bUnbound=true;
        PostProcess->Priority=20.f;
        PostProcess->BlendWeight=0.f;
        PostProcess->Settings.WeightedBlendables.Array.Add(FWeightedBlendable(1.f,LensMaterial));
        PostProcess->RegisterComponent();
    }
    UE_LOG(LogTemp,Display,TEXT("WeatherPresentation ready screen=%d wetMaterialSources=%d"),LensMaterial!=nullptr,Assets?Assets->WetMaterials.Num():0);
    StartWeatherPresentationValidation(Cast<AFPSWeatherManager>(GetOwner()));
}

void UWeatherViewEffectsComponent::RestoreMaterials()
{
    for(auto& Binding:Bindings)RestoreBinding(Binding);
    Bindings.Reset();
}

void UWeatherViewEffectsComponent::BindWeapon(AFPSGAMECharacter* Pawn)
{
    if(Pawn!=BoundPawn.Get()){RestoreMaterials();BoundPawn=Pawn;}
    if(!Pawn||!Assets)return;
    for(int32 I=Bindings.Num()-1;I>=0;--I)
    {
        auto& B=Bindings[I];auto* Mesh=B.Mesh.Get();
        if(!Mesh||SourceMesh(Mesh)!=B.MeshAsset.Get()||Mesh->GetMaterial(B.Slot)!=B.Wet)
        {RestoreBinding(B);Bindings.RemoveAtSwap(I);}
    }
    USkeletalMeshComponent* Main=nullptr;
    for(auto* M:TInlineComponentArray<USkeletalMeshComponent*>(Pawn))
        if(M->GetFName()==TEXT("AKMViewmodel")){Main=M;break;}
    if(!Main)return;
    for(auto* Mesh:TInlineComponentArray<UMeshComponent*>(Pawn))
    {
        if(Mesh!=Main&&!Mesh->IsAttachedTo(Main))continue;
        for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
        {
            if(Bindings.ContainsByPredicate([Mesh,Slot](const auto& B){return B.Mesh==Mesh&&B.Slot==Slot;}))continue;
            auto* Original=Mesh->GetMaterial(Slot);if(!Original)continue;
            auto* Source=Original;
            auto* Replacement=Assets->WetMaterials.Find(Source->GetPathName());
            // A gunsmith may already have a MID. Preserve its texture/color values.
            if(!Replacement)if(auto* MID=Cast<UMaterialInstanceDynamic>(Source))
                if(MID->Parent)Replacement=Assets->WetMaterials.Find(MID->Parent->GetPathName());
            if(!Replacement||!*Replacement)continue;
            auto* Wet=UMaterialInstanceDynamic::Create(*Replacement,this);
            Wet->CopyMaterialUniformParameters(Original);
            Wet->SetScalarParameterValue(TEXT("WeaponWetness"),0.f);
            FWeatherViewMaterial B;B.Mesh=Mesh;B.MeshAsset=SourceMesh(Mesh);B.Original=Original;B.Wet=Wet;B.Slot=Slot;
            Bindings.Add(B);Mesh->SetMaterial(Slot,Wet);
        }
    }
}

void UWeatherViewEffectsComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    auto* Weather=Cast<AFPSWeatherManager>(GetOwner());if(!Weather)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    BindCountdown-=Delta;
    if(BindCountdown<=0){BindWeapon(Pawn);BindCountdown=.2f;}
    const float Rain=Weather->GetEffectiveRainIntensity()*Weather->GetRainExposure();
    const bool bAiming=Pawn&&Pawn->IsAiming();
    const auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    const float Facing=Camera?FMath::Clamp(.7f+Camera->GetCameraRotation().Vector().Z*.45f,.3f,1.1f):.7f;
    ScreenWetness=FMath::Clamp(ScreenWetness+Delta*(Rain*.22f*Facing-1.f/32.f),0.f,1.f);
    FString Key;
    if(Pawn&&Pawn->HasInventoryWeapon())
    {
        if(auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            if(const auto* Item=Model->Equipped())Key=Item->InstanceId;
        if(Key.IsEmpty())Key=Pawn->bUseM4Infima?TEXT("PreviewM4"):TEXT("PreviewAKM");
    }
    for(auto& Pair:WeaponWetness)Pair.Value=FMath::Max(0.f,Pair.Value-Delta/120.f);
    if(!Key.IsEmpty())
    {
        float& Value=WeaponWetness.FindOrAdd(Key);
        Value=FMath::Clamp(Value+Delta*Rain*.065f,0.f,1.f);
        ActiveWeaponWetness=Value;
    }
    else ActiveWeaponWetness=0.f;
    const bool bVisible=UWeatherSurfaceComponent::GetQuality()>0;
    const float WeaponStrength=bVisible?FMath::Clamp(CVarWeaponWetness.GetValueOnGameThread(),0.f,1.f):0.f;
    for(auto& B:Bindings)if(B.Wet)
    {
        B.Wet->SetScalarParameterValue(TEXT("WeaponWetness"),ActiveWeaponWetness*WeaponStrength);
        B.Wet->SetScalarParameterValue(TEXT("WeaponRain"),Rain);
    }
    if(LensMaterial&&PostProcess)
    {
        const float Strength=bVisible?FMath::Clamp(CVarScreenRain.GetValueOnGameThread(),0.f,1.f):0.f;
        LensMaterial->SetScalarParameterValue(TEXT("ScreenWetness"),ScreenWetness);
        LensMaterial->SetScalarParameterValue(TEXT("RainStrength"),Strength);
        LensMaterial->SetScalarParameterValue(TEXT("AimProtection"),bAiming?1.f:0.f);
        PostProcess->BlendWeight=ScreenWetness>.001f&&Strength>0.f?1.f:0.f;
    }
}

void UWeatherViewEffectsComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    RestoreMaterials();
    if(PostProcess)PostProcess->DestroyComponent();
    Super::EndPlay(Reason);
}
