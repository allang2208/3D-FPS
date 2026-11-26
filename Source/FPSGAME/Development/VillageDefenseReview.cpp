// Explicit opt-in, isolated save directory. Never runs in ordinary gameplay.
#if !UE_BUILD_SHIPPING
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseDebris.h"
#include "../WorldGeneration/VillageDefenseState.h"
#include "../WorldGeneration/VillageDefenseCombat.h"
#include "../WorldGeneration/VillagePlantingDisplay.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterAIController.h"
#include "../NPC/ChapelNun.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Engine/DamageEvents.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Engine/Engine.h"
#include "UnrealClient.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Containers/Ticker.h"
#include "Kismet/GameplayStatics.h"
#include "Serialization/JsonSerializer.h"
#include "TimerManager.h"

namespace VillageDefenseReview
{
struct FRun
{
    TWeakObjectPtr<UWorld> World;TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<ACameraActor> Camera;TWeakObjectPtr<AVillageDefenseGate> Gate;
    TWeakObjectPtr<AVillageDefenseSection> Wall;TWeakObjectPtr<ANurseZombie> Monster;
    FString Out,Trace;TArray<TSharedPtr<FJsonValue>> Checks;
    int32 Stage=0,Errors=0;double Start=FPlatformTime::Seconds(),Next=0,AttackAt=0;
    float BeforeHealth=0;bool AttackRequested=false;
    uint64 OverviewFrame=0;
    bool GateOnly=FParse::Param(FCommandLine::Get(),TEXT("VillageGateOnly"));
    void Log(const FString& S){Trace+=S+LINE_TERMINATOR;FFileHelper::SaveStringToFile(Trace,*(Out/TEXT("trace.txt")));UE_LOG(LogTemp,Display,TEXT("VILLAGE_DEFENSE_REVIEW %s"),*S);}
    void Check(bool Pass,const FString& Name)
    {auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("name"),Name);J->SetBoolField(TEXT("pass"),Pass);Checks.Add(MakeShared<FJsonValueObject>(J));if(!Pass)++Errors;Log((Pass?TEXT("PASS "):TEXT("FAIL "))+Name);}
    void View(FVector Eye,FVector Target,float Fov=60)
    {
        auto* PC=World->GetFirstPlayerController();if(!Camera.IsValid())Camera=World->SpawnActor<ACameraActor>();
        PC->GetPawn()->SetActorLocation(Eye+FVector(0,0,400),false,nullptr,ETeleportType::TeleportPhysics);PC->GetPawn()->SetActorHiddenInGame(true);
        Camera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());Camera->GetCameraComponent()->SetFieldOfView(Fov);PC->SetViewTarget(Camera.Get());
    }
    FVector Ground(double X,double Y,double Z=0) const
    {const auto P=Hills->GetVillageSite().World(X,Y);return FVector(P,Hills->Height(P.X,P.Y)+Z);}
    void Overview(){const auto& V=Hills->GetVillageSite();View(Ground(-V.PadHalfX-1500,-V.PadHalfY-1400,2100),Ground(-V.PadHalfX+2500,-V.PadHalfY+2500,100));}
    bool OpenGateThroughInteraction()
    {
        if(!Gate.IsValid())return false;
        auto* PC=World->GetFirstPlayerController();APawn* Pawn=PC->GetPawn();
        const auto T=Gate->GetActorTransform();Pawn->SetActorLocation(T.TransformPosition(FVector(-150,-180,94)),false,nullptr,ETeleportType::TeleportPhysics);
        PC->SetViewTarget(Pawn);const FVector Aim=T.TransformPosition(FVector(-150,0,130));
        PC->SetControlRotation((Aim-Pawn->GetPawnViewLocation()).Rotation());PC->PlayerCameraManager->UpdateCamera(0);
        FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);PC->SetControlRotation((Aim-Eye).Rotation());PC->PlayerCameraManager->UpdateCamera(0);
        auto* Push=Pawn->FindComponentByClass<UFPSDoorPushComponent>();return Push&&Push->RequestDoorInteraction(Gate.Get());
    }
    void Shot(const TCHAR* Name)
    {const FString Path=Out/(FString(Name)+TEXT(".png"));FScreenshotRequest::RequestScreenshot(Path,false,false);Log(TEXT("screenshot ")+Path);}
    bool Finish()
    {
        auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("pass"),Errors==0);J->SetArrayField(TEXT("checks"),Checks);
        J->SetStringField(TEXT("scope"),GateOnly?TEXT("isolated rendered gate visual follow-up and both swings; not multiplayer"):TEXT("isolated rendered standalone: same-camera layout, gates, animation-contact damage, physical debris and persisted health; not multiplayer"));
        FString Json;auto Writer=TJsonWriterFactory<>::Create(&Json);FJsonSerializer::Serialize(J,Writer);FFileHelper::SaveStringToFile(Json,*(Out/TEXT("result.json")));
        const int32 Exit=Errors?1:0;UGameplayStatics::OpenLevel(World.Get(),TEXT("/Engine/Maps/Entry"));
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Exit](float){FPlatformMisc::RequestExitWithStatus(false,Exit);return false;}),5.f);return false;
    }
    bool Tick(float)
    {
        auto* W=World.Get();if(!W)return false;
        // Gameplay timers and animation clocks slow together during asset compilation.
        // Wall-clock waits can otherwise inspect a moving gate or unexpired rubble.
        const double Now=W->GetTimeSeconds();
        if(FPlatformTime::Seconds()-Start>1200){Check(false,TEXT("review timeout at stage ")+FString::FromInt(Stage));return Finish();}
        if(Now<Next)return true;
        auto* PC=W->GetFirstPlayerController();if(!PC||!PC->GetPawn())return true;
        if(Stage==0)
        {
            for(TActorIterator<ATemperateHillsWorld> It(W);It;++It)Hills=*It;
            if(!Hills.IsValid()||!Hills->bReady||!Hills->GetVillageSite().bPlaced)return true;
            bool Chapel=false;for(TActorIterator<AChapelNun> It(W);It;++It)Chapel=true;
            if(!Chapel)return true;
            if(auto* C=Cast<ACharacter>(PC->GetPawn()))C->GetCharacterMovement()->DisableMovement();
            PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);Overview();OverviewFrame=GFrameCounter;
            if(GateOnly)
            {
                FText Failure;const bool Repaired=Hills->CompleteVillageWallRepair(Failure);Check(Repaired,TEXT("gate fixture repair ")+Failure.ToString());
                if(!Repaired)return Finish();
                for(TActorIterator<AVillageDefenseGate> It(W);It;++It)if(It->GetSectionId()==10000)Gate=*It;
                Stage=8;Next=Now+20.;return true;
            }
            Next=Now+55.;++Stage;return true;
        }
        if(Stage==1)
        {
            if(GFrameCounter-OverviewFrame<300)return true;
            for(TActorIterator<AVillagePlantingDisplay> It(W);It;++It)if(It->IsActorTickEnabled())return true;
        }
        Log(FString::Printf(TEXT("stage %d"),Stage));
        switch(Stage)
        {
        case 1:Shot(TEXT("overview-ruined"));break;
        case 2:View(Ground(-700,1150,190),Ground(2200,-1340,170),72);Next=Now+20.;++Stage;return true;
        case 3:Shot(TEXT("chapel-side"));break;
        case 4:View(Ground(4500,-3300,1000),Ground(2100,-1500,60),68);Next=Now+18.;++Stage;return true;
        case 5:Shot(TEXT("chapel-yard"));break;
        case 6:
        {
            FText Failure;const bool Repaired=Hills->CompleteVillageWallRepair(Failure);Check(Repaired,TEXT("repair saved and collision replaced ")+Failure.ToString());
            if(!Repaired)return Finish();Overview();Next=Now+18.;++Stage;return true;
        }
        case 7:
        {
            Shot(TEXT("overview-repaired"));int32 Bays=0,Gates=0;
            for(TActorIterator<AVillageDefenseSection> It(W);It;++It)
            {
                if(auto* G=Cast<AVillageDefenseGate>(*It)){++Gates;if(G->GetSectionId()==10000)Gate=G;}
                else {++Bays;if(!Wall.IsValid()&&It->GetMaximumHealth()==1200.f)Wall=*It;}
            }
            Check(Bays>140&&Gates==2,TEXT("independent wall segments and two gates"));
            double MinGap=DBL_MAX,MaxGap=-DBL_MAX;
            for(TActorIterator<AVillageDefenseGate> It(W);It;++It)
                for(double X:{-330.,0.,330.})
                {
                    const FVector P=It->GetActorTransform().TransformPosition(FVector(X,0,12));
                    const double Gap=P.Z-Hills->Height(P.X,P.Y);MinGap=FMath::Min(MinGap,Gap);MaxGap=FMath::Max(MaxGap,Gap);
                }
            Check(MinGap>=1.&&MaxGap<=25.,FString::Printf(TEXT("gate ground clearance min=%.1f max=%.1f cm"),MinGap,MaxGap));
            Check(Wall.IsValid()&&FMath::IsNearlyEqual(Wall->GetActorScale3D().Z,1.25),TEXT("repaired wall raised exactly 25 percent"));break;
        }
        case 8:View(Ground(-7800,-1500,550),Ground(-6500,0,110),66);Next=Now+15.;++Stage;return true;
        case 9:
        {
            Shot(TEXT("west-gate-closed"));FTimerHandle Delay;
            W->GetTimerManager().SetTimer(Delay,[this]{if(GateOnly){if(Gate.IsValid())Gate->ToggleDoor();}else{Check(OpenGateThroughInteraction(),TEXT("gate uses the E-key authority interaction entry"));View(Ground(-7800,-1500,550),Ground(-6500,0,110),66);}},1.f,false);
            Next=Now+5.;++Stage;return true;
        }
        case 10:
        {
            Check(Gate.IsValid()&&Gate->GetGateAngle()>85.f,FString::Printf(TEXT("west gate swings open angle=%.1f"),Gate.IsValid()?Gate->GetGateAngle():-1.f));Shot(TEXT("west-gate-open"));
            FTimerHandle Delay;const TWeakObjectPtr<AVillageDefenseGate> Door=Gate;
            W->GetTimerManager().SetTimer(Delay,[Door]{if(Door.IsValid())Door->ToggleDoor();},1.f,false);
            Next=Now+5.;++Stage;return true;
        }
        case 11:
        {
            Check(Gate.IsValid()&&Gate->GetGateAngle()<1.f,TEXT("west gate closes"));
            for(TActorIterator<AVillageDefenseGate> It(W);It;++It)if(It->GetSectionId()==10001)Gate=*It;
            View(Ground(7800,2000,500),Ground(6500,500,110),66);Next=Now+18.;++Stage;return true;
        }
        case 12:
        {
            Shot(TEXT("east-gate-closed"));FTimerHandle Delay;const TWeakObjectPtr<AVillageDefenseGate> Door=Gate;
            W->GetTimerManager().SetTimer(Delay,[Door]{if(Door.IsValid())Door->ToggleDoor();},1.f,false);
            Next=Now+5.;++Stage;return true;
        }
        case 13:
            Check(Gate.IsValid()&&Gate->GetGateAngle()>85.f,FString::Printf(TEXT("east gate swings open angle=%.1f"),Gate.IsValid()?Gate->GetGateAngle():-1.f));Shot(TEXT("east-gate-open"));
            if(GateOnly){Stage=20;Next=Now+3.;return true;}break;
        case 14:
        {
            if(!Wall.IsValid()){Check(false,TEXT("wall fixture"));return Finish();}
            const FVector Center=Wall->GetActorLocation();FVector Outward=(Center-Hills->GetVillageSite().Ground).GetSafeNormal2D();
            const FVector Point=Wall->TargetPoint(Center+Outward*500.+FVector(0,0,85));
            FActorSpawnParameters P;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Class=LoadClass<ANurseZombie>(nullptr,TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"));
            if(!Class){Check(false,TEXT("nurse blueprint loaded"));return Finish();}
            Monster=W->SpawnActor<ANurseZombie>(Class,FVector(Point.X,Point.Y,Center.Z)+Outward*105.+FVector(0,0,95),(Outward*-1.).Rotation(),P);
            if(auto* AI=Cast<AMonsterAIController>(Monster->GetController())){AI->UnPossess();AI->Destroy();}
            Monster->GetCharacterMovement()->DisableMovement();
            View(Center+Outward*1250.+FVector(0,0,700),Center+FVector(0,0,90),62);
            BeforeHealth=Wall->GetHealth();Next=Now+15.;++Stage;return true;
        }
        case 15:
        {
            Check(Monster.IsValid()&&Monster->AttackClip&&Monster->Combat,TEXT("real monster animation ready"));
            AttackRequested=Monster.IsValid()&&Monster->Combat->TryAttack(Wall.Get());Check(AttackRequested,TEXT("monster starts wall melee animation"));
            AttackAt=Now;Next=Now+5.;++Stage;return true;
        }
        case 16:
        {
            Check(Wall->GetHealth()<BeforeHealth,TEXT("animation contact deals wall damage"));Shot(TEXT("wall-damaged"));
            auto* State=W->GetSubsystem<UVillageDefenseState>();State->Flush();
            auto* Save=Cast<UVillageDefenseSave>(UGameplayStatics::LoadGameFromSlot(TEXT("VillageDefenses_")+Hills->WorldId.ToString(EGuidFormats::Digits),0));
            Check(Save&&Save->DamagedSections.FindRef(Wall->GetSectionId())==Wall->GetHealth(),TEXT("partial damage saved on disk"));
            FDamageEvent E;Wall->TakeDamage(FMath::Max(0.f,Wall->GetHealth()-Monster->AttackDamage*.5f),E,nullptr,nullptr);
            Next=Now+2.;++Stage;return true;
        }
        case 17:Monster->Combat->TryAttack(Wall.Get());Next=Now+3.;++Stage;return true;
        case 18:
        {
            Check(Wall->GetHealth()<=0.f,TEXT("monster destroys weakened wall"));
            int32 Fragments=0,Moving=0;for(TActorIterator<AVillageDefenseDebris> It(W);It;++It)for(auto* C:TInlineComponentArray<UStaticMeshComponent*>(*It))
            {Fragments+=C->IsSimulatingPhysics();Moving+=C->IsSimulatingPhysics()&&C->GetPhysicsLinearVelocity().Size()>1.;}
            Check(Fragments>0&&Moving>0,FString::Printf(TEXT("fractured stones simulate physics bodies=%d moving=%d"),Fragments,Moving));Check(Wall->GetMasonry()->GetCollisionEnabled()==ECollisionEnabled::NoCollision,TEXT("breach collision removed"));
            Shot(TEXT("wall-collapse"));Next=Now+14.;++Stage;return true;
        }
        case 19:
        {
            int32 Debris=0;for(TActorIterator<AVillageDefenseDebris> It(W);It;++It)++Debris;
            Check(Debris==0,TEXT("physical debris cleaned after lifetime"));Shot(TEXT("wall-breach-cleared"));
            auto* Save=Cast<UVillageDefenseSave>(UGameplayStatics::LoadGameFromSlot(TEXT("VillageDefenses_")+Hills->WorldId.ToString(EGuidFormats::Digits),0));
            Check(Save&&Save->DamagedSections.Contains(Wall->GetSectionId())&&Save->DamagedSections.FindRef(Wall->GetSectionId())==0.f,TEXT("destroyed section saved"));break;
        }
        case 20:return Finish();
        }
        ++Stage;Next=Now+2.;return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.VillageDefenseReview"),TEXT("Opt-in rendered village planting and defenses review"),FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{
    if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("VillageDefenseReview")))return;
    auto R=MakeShared<FRun>();R->World=W;FParse::Value(FCommandLine::Get(),TEXT("VillageDefenseOut="),R->Out);if(R->Out.IsEmpty())return;
    IFileManager::Get().MakeDirectory(*R->Out,true);FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float Dt){return R->Tick(Dt);}),.25f);
}));
}
#endif
