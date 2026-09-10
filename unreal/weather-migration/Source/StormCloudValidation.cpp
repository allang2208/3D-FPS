#include "StormCloudValidation.h"
#include "FPSWeatherManager.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/MeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "UObject/UnrealType.h"
#include "Kismet/KismetSystemLibrary.h"
#include "StormCloudComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "DynamicRHI.h"
#include "RenderTimer.h"

namespace
{
struct FStormAudit
{
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    FTimerHandle Timer;
    FDelegateHandle PostTick;
    float SampleTime=0;
    TArray<double> ClearGPU, StormGPU;
    int32 Step=0,Failures=0;
    float ClearSun=0,StormSun=0;
    TWeakObjectPtr<UDirectionalLightComponent> Sun;
    TWeakObjectPtr<UVolumetricCloudComponent> FirstCloud;
    UMaterialInterface* ClearMaterial=nullptr;
    bool ClearVisible=false;
    void Check(bool bPass,const TCHAR* Name)
    {Failures+=!bPass;UE_LOG(LogTemp,Display,TEXT("STORM_CHECK %s %s"),bPass?TEXT("PASS"):TEXT("FAIL"),Name);}
    void Capture(const TCHAR* Label)
    {
        const FString Dir=FPaths::ProjectSavedDir()/TEXT("StormClouds");IFileManager::Get().MakeDirectory(*Dir,true);
        FScreenshotRequest::RequestScreenshot(Dir/(UGameplayStatics::GetCurrentLevelName(Weather.Get(),true)+TEXT("-")+Label+TEXT(".png")),false,false);
    }
    void Tick()
    {
        if(!Weather.IsValid())return;
        ++Step;auto* W=Weather->GetWorld();auto* Clouds=Weather->FindComponentByClass<UStormCloudComponent>();
        if(Step==1)
        {
            Weather->TransitionSeconds=4;Weather->SetWeatherState(EFPSWeatherState::Clear);
            auto* PC=UGameplayStatics::GetPlayerController(W,0);
            if(PC){PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);PC->SetControlRotation(FRotator(25,-35,0));}
            if(auto* Pawn=UGameplayStatics::GetPlayerPawn(W,0))Pawn->SetCanBeDamaged(false);
            for(TActorIterator<AActor> It(W);It;++It)
            {
                for(auto* L:TInlineComponentArray<UDirectionalLightComponent*>(*It))if(L->IsVisible())Sun=L;
                if(!It->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager")))continue;
                for(TFieldIterator<FProperty> P(It->GetClass());P;++P)
                {
                    const FString N=P->GetName();const bool bHeight=N.Contains(TEXT("Sun Height")),bSpeed=N.Contains(TEXT("Sun Speed"));
                    if(!bHeight&&!bSpeed)continue;
                    if(auto* F=CastField<FFloatProperty>(*P))F->SetPropertyValue_InContainer(*It,bHeight?1000:0);
                    if(auto* F=CastField<FDoubleProperty>(*P))F->SetPropertyValue_InContainer(*It,bHeight?1000:0);
                }
            }
        }
        if(Step==24)
        {
            Sun=nullptr;
            for(TActorIterator<AActor> It(W);It;++It)for(auto* L:TInlineComponentArray<UDirectionalLightComponent*>(*It))
                if(L->IsVisible()&&L->bAffectsWorld&&!It->IsHidden()&&(!Sun.IsValid()||L->Intensity>Sun->Intensity))Sun=L;
            ClearSun=Sun.IsValid()?Sun->Intensity:0;
            if(auto* C=Clouds->GetCloud()){ClearMaterial=C->GetMaterial();ClearVisible=C->IsVisible();}
            Capture(TEXT("clear"));
        }
        if(Step==28)Weather->SetWeatherState(EFPSWeatherState::Storm);
        if(Step==36)Check(Clouds->GetStormBlend()>.2f&&Clouds->GetStormBlend()<.8f,TEXT("storm transition interpolates"));
        if(Step==72)
        {
            auto* C=Clouds->GetCloud();FirstCloud=C;
            Check(Clouds->GetStormBlend()==1&&C&&C->IsVisible(),TEXT("storm has visible cloud layer"));
            float Coverage=0,Density=0;if(C&&C->GetMaterial()){C->GetMaterial()->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Cloud_GlobalCoverage")),Coverage);C->GetMaterial()->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Cloud_GlobalDensity")),Density);}
            Check(FMath::IsNearlyEqual(Coverage,.1f,.0001f)&&FMath::IsNearlyZero(Density,.0001f),TEXT("overcast coverage preserves cloud erosion"));
            if(C)UE_LOG(LogTemp,Display,TEXT("STORM_RENDER hidden=%d ownerHidden=%d mainpass=%d"),C->bHiddenInGame,C->GetOwner()->IsHidden(),C->bRenderInMainPass);
            StormSun=Sun.IsValid()?Sun->Intensity:0;
            Check(Sun.IsValid()&&Sun->AtmosphereSunDiskColorScale.R<.01f&&StormSun<ClearSun*.3f,TEXT("sun disk and direct sunlight suppressed"));
            UE_LOG(LogTemp,Display,TEXT("STORM_LIGHT clear=%f storm=%f"),ClearSun,StormSun);
            Capture(TEXT("storm"));
        }
        if(Step==80)Weather->SetWeatherState(EFPSWeatherState::Clear);
        if(Step==112)
        {
            auto* C=Clouds->GetCloud();
            Check(Clouds->GetStormBlend()==0,TEXT("clear transition completes"));
            Check(C&&C->IsVisible()==ClearVisible&&(!ClearMaterial||C->GetMaterial()==ClearMaterial),TEXT("original cloud material and visibility restored"));
            Check(Sun.IsValid()&&Sun->AtmosphereSunDiskColorScale.R>.99f&&Sun->Intensity>StormSun*3,TEXT("sunlight restored without accumulated dimming"));
            Capture(TEXT("restored"));
        }
        if(Step==120)Weather->SetWeatherState(EFPSWeatherState::Storm);
        if(Step==148)
        {
            Check(Clouds->GetCloud()==FirstCloud,TEXT("repeat storm reuses cloud component"));
            int32 VisibleClouds=0,VisibleSuns=0;
            for(TActorIterator<AActor> It(W);It;++It){for(auto* C:TInlineComponentArray<UVolumetricCloudComponent*>(*It))VisibleClouds+=C->IsVisible();for(auto* L:TInlineComponentArray<UDirectionalLightComponent*>(*It))VisibleSuns+=L->IsVisible()&&L->Intensity>0;}
            Check(VisibleClouds==1&&VisibleSuns==1,TEXT("one active cloud layer and directional light"));
            Weather->SetWeatherState(EFPSWeatherState::Clear);
        }
        if(Step==176)
        {
            Check(Clouds->GetStormBlend()==0&&Sun.IsValid()&&Sun->Intensity>StormSun*3,TEXT("second clear restores sun"));
            UE_LOG(LogTemp,Display,TEXT("STORM_CLOUD_AUDIT_%s failures=%d"),Failures?TEXT("FAIL"):TEXT("PASS"),Failures);
            ClearGPU.Sort();StormGPU.Sort();
            if(ClearGPU.Num()&&StormGPU.Num())UE_LOG(LogTemp,Display,TEXT("STORM_GPU whole_scene clear_median=%.3f storm_median=%.3f clear_samples=%d storm_samples=%d"),ClearGPU[ClearGPU.Num()/2],StormGPU[StormGPU.Num()/2],ClearGPU.Num(),StormGPU.Num());
            FWorldDelegates::OnWorldPostActorTick.Remove(PostTick);UKismetSystemLibrary::QuitGame(Weather.Get(),nullptr,EQuitPreference::Quit,false);
        }
    }
};
}

void StartStormCloudValidation(AFPSWeatherManager* Weather)
{
    if(FParse::Param(FCommandLine::Get(),TEXT("StormCloudAudit")))
    {
        auto Audit=MakeShared<FStormAudit>();Audit->Weather=Weather;
        Audit->PostTick=FWorldDelegates::OnWorldPostActorTick.AddLambda([Audit](UWorld* W,ELevelTick,float Delta)
        {
            if(!Audit->Weather.IsValid()||W!=Audit->Weather->GetWorld())return;
            const double GPU=FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles());
            if(GPU>0){if(Audit->Step>=12&&Audit->Step<24)Audit->ClearGPU.Add(GPU);if(Audit->Step>=52&&Audit->Step<72)Audit->StormGPU.Add(GPU);}
            Audit->SampleTime+=Delta;if(Audit->SampleTime>=.25f){Audit->SampleTime-=.25f;Audit->Tick();}
        });
        return;
    }
    if (!FParse::Param(FCommandLine::Get(), TEXT("StormCloudInspect"))) return;
    FTimerHandle Handle;
    TWeakObjectPtr<AFPSWeatherManager> Weak(Weather);
    Weather->GetWorldTimerManager().SetTimer(Handle, [Weak]()
    {
        if (!Weak.IsValid()) return;
        auto DumpMaterial = [](UMaterialInterface* M)
        {
            if (!M) return;
            UE_LOG(LogTemp, Display, TEXT("CLOUD_MATERIAL %s"), *M->GetPathName());
            TArray<FMaterialParameterInfo> Infos; TArray<FGuid> IDs;
            M->GetAllScalarParameterInfo(Infos, IDs);
            for (const auto& Info : Infos) { float V=0; M->GetScalarParameterValue(Info,V); UE_LOG(LogTemp,Display,TEXT("CLOUD_SCALAR %s=%f"),*Info.Name.ToString(),V); }
        };
        for (TActorIterator<AActor> It(Weak->GetWorld()); It; ++It)
        {
            for (auto* C : TInlineComponentArray<UVolumetricCloudComponent*>(*It))
            { UE_LOG(LogTemp,Display,TEXT("CLOUD_COMPONENT %s visible=%d bottom=%f height=%f"),*C->GetPathName(),C->IsVisible(),C->LayerBottomAltitude,C->LayerHeight); DumpMaterial(C->GetMaterial()); }
            if (!It->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager"))) continue;
            for (TFieldIterator<FProperty> P(It->GetClass()); P; ++P)
            {
                FString Name=P->GetName();
                if (!Name.Contains(TEXT("cloud")) && !Name.Contains(TEXT("sun")) && !Name.Contains(TEXT("sky"))) continue;
                FString V; P->ExportText_InContainer(0,V,*It,*It,*It,PPF_None);
                UE_LOG(LogTemp,Display,TEXT("CLOUD_BP %s=%s"),*Name,*V);
            }
            for (auto* C : TInlineComponentArray<UMeshComponent*>(*It)) for(int32 I=0;I<C->GetNumMaterials();++I) DumpMaterial(C->GetMaterial(I));
        }
        UKismetSystemLibrary::QuitGame(Weak.Get(),nullptr,EQuitPreference::Quit,false);
    }, 6.0f, false);
}
