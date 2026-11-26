#include "SurvivalClockAuditCommandlet.h"
#include "FPSSurvivalComponent.h"
#include "../FPSWeatherManager.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/WorldSettings.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "UObject/Script.h"

int32 USurvivalClockAuditCommandlet::Main(const FString& Params)
{
    if(!FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()).Contains(TEXT("SurvivalClockLink20261015/TestRuns/")))return 2;
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=SurvivalClockAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("SurvivalClockAudit"));
    auto* World=GI->GetWorld();World->GetWorldSettings()->MaxUndilatedFrameTime=1.f;
    auto* Clock=World->SpawnActor<AFPSWeatherManager>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetPlayerState(World->SpawnActor<APlayerState>());PC->SetAsLocalPlayerController();PC->Possess(Pawn);Pawn->DispatchBeginPlay();
    auto* Survival=Pawn->FindComponentByClass<UFPSSurvivalComponent>();
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failed=0;
    auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString()){
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);R->SetStringField(TEXT("detail"),Detail);
        Rows.Add(MakeShared<FJsonValueObject>(R));if(!OK)++Failed;UE_LOG(LogTemp,Display,TEXT("SURVIVAL_CLOCK %s %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);};
    auto Near=[](double A,double B,double Tolerance=.002){return FMath::Abs(A-B)<Tolerance;};
    auto Fresh=[&](){Health->Health=Health->MaxHealth;Survival->RestoreState(FFPSSurvivalState{});Survival->NaturalClock.Reset();Survival->ClockResolveAfter=0.;Survival->NaturalConsumptionSeconds(0.f);};
    // The weather manager owns the native clock (the authored sky Blueprint was
    // retired with the UDS migration); survival follows the manager directly.
    auto Step=[&](float RealDelta,bool RunSky){World->Tick(LEVELTICK_TimeOnly,RealDelta);const float Dt=World->GetDeltaSeconds();
        if(RunSky)Clock->AdvanceNaturalClock(Dt);Survival->TickComponent(Dt,LEVELTICK_All,nullptr);return Dt;};
    double HubCycleElapsed=0.,HubWaterElapsed=0.;
    {
        Clock->RealSecondsPerGameDay=2160;Clock->WeatherClockSeconds=0;Clock->NormalizedDayTime=0;Fresh();
        const double Begin=Clock->GetNaturalDayProgress();bool PositiveBefore=true;
        int32 HubSteps=0;
        while(Clock->GetNaturalDayProgress()-Begin<1.-1.e-10&&HubSteps<10000)
        {PositiveBefore&=Survival->GetState().Hunger>0.;HubCycleElapsed+=Step(.25f,true);++HubSteps;
            if(HubWaterElapsed==0.&&Survival->GetState().Hydration==0.f){HubWaterElapsed=HubCycleElapsed;Survival->RestoreResources(0,100,0);}}
        Check(HubSteps<10000&&Near(Clock->GetNaturalDayProgress()-Begin,1.,1.e-8),TEXT("native clock completes one natural day"),FString::Printf(TEXT("elapsed=%.6f steps=%d days=%.9f"),HubCycleElapsed,HubSteps,Clock->GetNaturalDayProgress()-Begin));
        Check(HubWaterElapsed>0.&&Near(HubWaterElapsed,HubCycleElapsed*.5,.5),TEXT("water exhausts at half the native day"),FString::Printf(TEXT("water elapsed=%.6f"),HubWaterElapsed));
        Check(PositiveBefore&&Survival->GetState().Hunger==0.f&&Near(Health->Health,Health->MaxHealth),TEXT("hunger exhausts on the native cycle; half-day water was refilled to avoid dehydration"));
        Fresh();Clock->RealSecondsPerGameDay=1080;const double FasterBegin=Clock->GetNaturalDayProgress();
        for(int32 I=0;I<400;++I)Step(.25f,true);
        Check(Clock->GetNaturalDayProgress()>FasterBegin&&Near(Survival->GetState().Hunger,100.-100.*(Clock->GetNaturalDayProgress()-FasterBegin))&&Near(Survival->GetState().Hydration,100.-200.*(Clock->GetNaturalDayProgress()-FasterBegin)),TEXT("runtime day-length changes drive hunger and twice-rate water"));
        const float BeforeJump=Survival->GetState().Hunger;const double BeforeDays=Clock->GetNaturalDayProgress();
        Clock->AdvanceGameTime(12.f);Check(Near(Clock->GetNaturalDayProgress(),BeforeDays,1.e-12),TEXT("manual time jump is excluded from natural progress"));
        Step(.25f,true);Check(BeforeJump-Survival->GetState().Hunger<.1f,TEXT("time jump charges only subsequent natural elapsed time"));
    }
    for(const float Dilation:{.5f,1.f,2.f})
    {
        UGameplayStatics::SetGlobalTimeDilation(World,Dilation);Clock->RealSecondsPerGameDay=2160;
        Clock->WeatherClockSeconds=0;Clock->NormalizedDayTime=0;Fresh();
        const double Begin=Clock->GetNaturalDayProgress();double Wall=0.,WaterWall=0.;int32 Steps=0;
        while(Clock->GetNaturalDayProgress()-Begin<1.-1.e-10&&Steps<18000){Step(.25f,false);Wall+=.25;++Steps;
            if(WaterWall==0.&&Survival->GetState().Hydration==0.f){WaterWall=Wall;Survival->RestoreResources(0,100,0);}}
        Check(Near(Wall,2160./Dilation,.26)&&Near(WaterWall,1080./Dilation,.26)&&Survival->GetState().Hunger==0&&Survival->GetState().Hydration==0&&Near(Health->Health,Health->MaxHealth),
            FString::Printf(TEXT("native calendar and 2x water consumption share global dilation %.1f"),Dilation),FString::Printf(TEXT("hunger undilated seconds=%.2f water=%.2f"),Wall,WaterWall));
    }
    UGameplayStatics::SetGlobalTimeDilation(World,1.f);Clock->RealSecondsPerGameDay=60.f;Clock->WeatherClockSeconds=0;Clock->NormalizedDayTime=0;Fresh();
    auto Buffed=Survival->GetState();Buffed.Hunger=Buffed.MaxHunger=10000;Buffed.Hydration=Buffed.MaxHydration=10000;
    Buffed.SausageRecoverySeconds=Buffed.LargeLambMealSeconds=600;Survival->RestoreState(Buffed);
    const double FastBegin=Clock->GetNaturalDayProgress();for(int32 I=0;I<400;++I)Step(.25f,false);
    Check(Near(Clock->GetNaturalDayProgress()-FastBegin,100./60.,1.e-6),TEXT("native authored day-length change is followed"));
    Check(Near(Survival->SausageRecoveryRemaining(),500)&&Near(Survival->LargeLambMealRemaining(),500),TEXT("food durations stay in gameplay seconds when the day accelerates"));
    Clock->RealSecondsPerGameDay=2160;Fresh();const double JumpBegin=Clock->GetNaturalDayProgress();Clock->AdvanceGameTime(12);Step(.25f,false);
    Check(Clock->GetNaturalDayProgress()-JumpBegin<.001&&100-Survival->GetState().Hunger<.1,TEXT("native manual jump is not billed as hunger"));
    const float BeforeDeath=Survival->GetState().Hunger;Health->Health=0;for(int32 I=0;I<40;++I)Step(.25f,false);
    Health->Health=Health->MaxHealth;Step(.25f,false);
    Check(BeforeDeath-Survival->GetState().Hunger<.1,TEXT("revival does not catch up consumption from dead time"));
    TArray<AActor*> Begun;for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())Begun.Add(*It);
    for(auto* A:Begun){A->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;A->GetComponents(Components);
        for(auto* C:Components)if(C->HasBegunPlay())C->EndPlay(EEndPlayReason::Quit);}
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("cases"),Rows);Report->SetNumberField(TEXT("passed"),Rows.Num()-Failed);Report->SetNumberField(TEXT("failed"),Failed);
    Report->SetNumberField(TEXT("hub_nominal_day_seconds"),2160.);Report->SetNumberField(TEXT("hub_actual_cycle_seconds_at_4Hz"),HubCycleElapsed);
    Report->SetNumberField(TEXT("hub_water_exhaustion_seconds_at_4Hz"),HubWaterElapsed);
    Report->SetStringField(TEXT("scope"),TEXT("actual Blueprint runtime function and native calendar in isolated world; no formal map/saves or rendered/network transport test"));
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*(FPaths::ProjectSavedDir()/TEXT("survival-clock-runtime.json")));
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    UE_LOG(LogTemp,Display,TEXT("SURVIVAL_CLOCK_RESULT passed=%d failed=%d"),Rows.Num()-Failed,Failed);return Failed?1:0;
}
