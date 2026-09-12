#include "WeatherPresentationValidation.h"
#include "FPSWeatherManager.h"
#include "WeatherViewEffectsComponent.h"
#include "StormCloudComponent.h"
#include "FPSGAMECharacter.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Components/StaticMeshComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "HAL/IConsoleManager.h"
#include "UObject/UnrealType.h"

namespace
{
struct FPresentationAudit
{
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    TWeakObjectPtr<AActor> Roof;
    FDelegateHandle Handle;
    float Time=0.f,ScreenBeforeShelter=0.f,WetBeforeDry=0.f,NextCapture=14.f;
    int32 Stage=0,Failures=0,Frame=0,Bindings=0;
    bool SawPartialExposure=false;
    int32 ComparisonStage=0,WeaponSwitchStage=0;
    float StoredM4Wetness=0.f;
    FString Directory;
    void Check(bool Pass,const TCHAR* What)
    {
        Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("WEATHER_PRESENTATION_CHECK %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),What);
    }
    void Capture(const FString& Name)
    { FScreenshotRequest::RequestScreenshot(Directory/TEXT("images")/(Name+TEXT(".png")),false,false); }
    void Tick(float Delta)
    {
        auto* W=Weather.Get();if(!W)return;
        auto* View=W->FindComponentByClass<UWeatherViewEffectsComponent>();
        auto* Cloud=W->FindComponentByClass<UStormCloudComponent>();
        auto* Pawn=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(W,0));
        if(!Pawn||!View||!Cloud)return;
        Time+=Delta;
        if(ComparisonStage==0&&Time>17)
        {
            IConsoleManager::Get().FindConsoleVariable(TEXT("fps.ScreenRain"))->Set(0.f,ECVF_SetByCode);
            IConsoleManager::Get().FindConsoleVariable(TEXT("fps.WeaponWetness"))->Set(0.f,ECVF_SetByCode);
            ComparisonStage=1;
        }
        if(ComparisonStage==1&&Time>18){Capture(TEXT("02a-rain-dry-materials"));ComparisonStage=2;}
        if(ComparisonStage==2&&Time>19)
        {
            IConsoleManager::Get().FindConsoleVariable(TEXT("fps.ScreenRain"))->Set(.75f,ECVF_SetByCode);
            IConsoleManager::Get().FindConsoleVariable(TEXT("fps.WeaponWetness"))->Set(1.f,ECVF_SetByCode);
            ComparisonStage=3;
        }
        if(Stage==0)
        {
            FParse::Value(FCommandLine::Get(),TEXT("WeatherAuditLabel="),Directory);
            if(Directory.IsEmpty())Directory=UGameplayStatics::GetCurrentLevelName(W,true);
            Directory=FPaths::ProjectSavedDir()/TEXT("WeatherPresentation20260912")/Directory;
            IFileManager::Get().MakeDirectory(*(Directory/TEXT("images")),true);
            W->TransitionSeconds=2.f;W->SetWeatherState(EFPSWeatherState::Clear);
            for(TActorIterator<AActor> It(W->GetWorld());It;++It)
                if(It->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager")))
                    for(TFieldIterator<FProperty> P(It->GetClass());P;++P)
                    {
                        const FString Name=P->GetName();
                        const bool Height=Name.Contains(TEXT("Sun Height")),Speed=Name.Contains(TEXT("Sun Speed"));
                        if(!Height&&!Speed)continue;
                        if(auto* F=CastField<FFloatProperty>(*P))F->SetPropertyValue_InContainer(*It,Height?1000:0);
                        if(auto* F=CastField<FDoubleProperty>(*P))F->SetPropertyValue_InContainer(*It,Height?1000:0);
                    }
            // Only this isolated audit save is changed; equip its granted AKM in slot two.
            if(auto* Model=W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            {
                auto State=Model->Snapshot();
                for(auto& Item:State.Items)if(Item.Definition==TEXT("ue_akm")){Item.Place=1;Item.Cell=9;break;}
                State.ActiveWeaponSlot=6;
                Check(Model->CommitState(State),TEXT("isolated two-weapon audit profile prepared"));
            }
            Pawn->SetCanBeDamaged(false);
            if(auto* PC=UGameplayStatics::GetPlayerController(W,0)){PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);PC->SetControlRotation(FRotator(12,-35,0));}
            Check(W->RealSecondsPerGameDay==2160.f,TEXT("36-minute day contract retained"));
            Check(View->GetLensMaterial()!=nullptr,TEXT("screen material loaded in runtime"));
            Stage=1;
        }
        if(Stage==1&&Time>4){Capture(TEXT("01-clear"));W->SetWeatherState(EFPSWeatherState::Cloudy);Stage=2;}
        if(Stage==2&&Time>8){Check(FMath::IsNearlyEqual(Cloud->GetStormBlend(),.3f,.01f),TEXT("cloudy has its own continuous cloud target"));W->SetWeatherState(EFPSWeatherState::LightRain);Stage=3;}
        if(Stage==3&&Time>12){Check(FMath::IsNearlyEqual(Cloud->GetStormBlend(),.52f,.01f),TEXT("light rain drives cloud layer"));W->SetWeatherState(EFPSWeatherState::Rain);Stage=4;}
        if(Stage==4&&Time>22)
        {
            Check(FMath::IsNearlyEqual(Cloud->GetStormBlend(),.76f,.01f),TEXT("rain drives cloud layer"));
            Check(View->GetScreenWetness()>.05f&&View->GetWeaponWetness()>.1f,TEXT("exposed view and weapon accumulate rain"));
            Bindings=View->GetWetMaterialCount();Check(Bindings>=1,TEXT("active gun materials consume wetness"));
            Capture(TEXT("02-rain-wet-gun"));Pawn->SetGunsmithAimPreview(true);Stage=5;
        }
        if(Stage==5&&Time>25){Check(Pawn->IsAiming(),TEXT("ADS still operates with wet materials"));Capture(TEXT("03-ads"));Pawn->SetGunsmithAimPreview(false);Stage=6;}
        if(Stage==6&&Time>28){Pawn->SetGunsmithInspection(true);Stage=7;}
        if(Stage==7&&Time>31){Capture(TEXT("04-inspection"));Pawn->SetGunsmithInspection(false);W->SetWeatherState(EFPSWeatherState::Storm);Stage=8;}
        if(Stage==8&&Time>40)
        {
            Check(Cloud->GetCloud()&&Cloud->GetCloud()->IsVisible(),TEXT("storm cloud visible"));
            Capture(TEXT("05-storm"));Stage=9;
        }
        if(Stage==9&&Time>43)
        {
            ScreenBeforeShelter=View->GetScreenWetness();
            auto* Actor=W->GetWorld()->SpawnActor<AActor>();Roof=Actor;
            auto* Mesh=NewObject<UStaticMeshComponent>(Actor);Actor->SetRootComponent(Mesh);
            Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
            Mesh->SetMobility(EComponentMobility::Movable);
            Mesh->SetCollisionProfileName(TEXT("BlockAll"));Mesh->SetWorldScale3D(FVector(10,10,.15));Mesh->RegisterComponent();
            Actor->SetActorLocation(Pawn->GetActorLocation()+FVector(0,0,400));
            Stage=10;
        }
        if(Stage==10&&W->GetRainExposure()>.05f&&W->GetRainExposure()<.95f)SawPartialExposure=true;
        if(Stage==10&&Time>47)
        {
            Check(SawPartialExposure,TEXT("roof exposure transitions smoothly"));
            Check(W->GetRainExposure()<.05f,TEXT("roof blocks new camera rain"));
            Check(View->GetScreenWetness()>0.f&&ScreenBeforeShelter>0.f,TEXT("screen retains residual water under shelter"));
            WetBeforeDry=View->GetWeaponWetness();Capture(TEXT("06-sheltered"));W->SetWeatherState(EFPSWeatherState::Clear);Stage=11;
        }
        if(Stage==11&&Time>51){if(Roof.IsValid())Roof->Destroy();Stage=12;}
        if(WeaponSwitchStage==0&&Time>53)
        {
            StoredM4Wetness=View->GetWeaponWetness();
            if(auto* Model=W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
                Check(Model->CycleWeapon(),TEXT("alternate inventory weapon can equip"));
            WeaponSwitchStage=1;
        }
        if(WeaponSwitchStage==1&&Time>56)
        {
            Check(View->GetWeaponWetness()<.01f&&View->GetWetMaterialCount()>0,TEXT("stored AKM stays dry and has wet material bindings"));
            Capture(TEXT("08-dry-akm"));
            if(auto* Model=W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Model->CycleWeapon();
            WeaponSwitchStage=2;
        }
        if(WeaponSwitchStage==2&&Time>59)
        {
            Check(View->GetWeaponWetness()>0.f&&View->GetWeaponWetness()<StoredM4Wetness,TEXT("M4 retains its own residual water after switching"));
            WeaponSwitchStage=3;
        }
        if(Stage==12&&Time>87)
        {
            Check(View->GetScreenWetness()<.01f,TEXT("screen dries after rain stops"));
            Check(View->GetWeaponWetness()>0.f&&View->GetWeaponWetness()<WetBeforeDry,TEXT("gun dries more slowly than screen"));
            Check(Cloud->GetStormBlend()==0.f,TEXT("clear sky restored"));
            Check(View->GetWetMaterialCount()==Bindings,TEXT("wet material count remains bounded"));
            Capture(TEXT("07-restored"));Stage=13;
        }
        if(Stage==13&&Time>90)
        {
            UE_LOG(LogTemp,Display,TEXT("WEATHER_PRESENTATION_AUDIT_%s failures=%d screen=%.3f gun=%.3f materials=%d"),Failures?TEXT("FAIL"):TEXT("PASS"),Failures,View->GetScreenWetness(),View->GetWeaponWetness(),View->GetWetMaterialCount());
            FWorldDelegates::OnWorldPostActorTick.Remove(Handle);
            UKismetSystemLibrary::QuitGame(W,nullptr,EQuitPreference::Quit,false);
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("WeatherCaptureSequence"))&&Time>=NextCapture&&Time<34.f)
        {
            Capture(FString::Printf(TEXT("sequence-%04d"),Frame++));NextCapture+=.5f;
        }
    }
};
}

void StartWeatherPresentationValidation(AFPSWeatherManager* Weather)
{
    if(!Weather||!FParse::Param(FCommandLine::Get(),TEXT("WeatherPresentationAudit")))return;
    auto Audit=MakeShared<FPresentationAudit>();Audit->Weather=Weather;
    Audit->Handle=FWorldDelegates::OnWorldPostActorTick.AddLambda([Audit](UWorld* World,ELevelTick,float Delta)
    {if(Audit->Weather.IsValid()&&Audit->Weather->GetWorld()==World)Audit->Tick(Delta);});
}
