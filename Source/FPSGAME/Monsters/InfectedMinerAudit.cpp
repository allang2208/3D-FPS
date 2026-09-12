#include "InfectedMinerAudit.h"
#include "InfectedMiner.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "MonsterSurfaceAudit.h"
#include "FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Animation/AnimSequence.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraActor.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HighResScreenshot.h"
#include "TimerManager.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "NavigationSystem.h"
#include "BehaviorTree/BlackboardComponent.h"

void UInfectedMinerAudit::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if(World.IsGameWorld()&&FParse::Param(FCommandLine::Get(),TEXT("MinerAudit")))World.GetTimerManager().SetTimer(Timer,this,&UInfectedMinerAudit::Step,.05f,true,6.f);
}
void UInfectedMinerAudit::Deinitialize(){if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(Timer);Super::Deinitialize();}
void UInfectedMinerAudit::Check(const TCHAR* Name,bool Passed)
{
    if(auto* Existing=Checks.FindByPredicate([Name](const auto& Item){return Item.Key==Name;}))
    {if(Existing->Value&&!Passed){Existing->Value=false;++Failures;}return;}
    Checks.Emplace(Name,Passed);if(!Passed)++Failures;UE_LOG(LogTemp,Display,TEXT("MINER_ASSERT %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Name);
}
void UInfectedMinerAudit::Capture(const TCHAR* Name){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("InfectedMiner")/(FString(Name)+TEXT(".png")),true,false);}
void UInfectedMinerAudit::Next(int32 Value){Stage=Value;StageClock=0;Started=false;}
void UInfectedMinerAudit::Place(float Distance)
{
    Player->SetActorLocation(PlayerStart,false,nullptr,ETeleportType::TeleportPhysics);
    Miner->SetActorLocation(PlayerStart+Forward*Distance+FVector(0,0,-4),false,nullptr,ETeleportType::TeleportPhysics);
    Miner->SetActorRotation((-Forward).Rotation());Miner->GetCharacterMovement()->StopMovementImmediately();
}
void UInfectedMinerAudit::Finish()
{
    FString Json=FString::Printf(TEXT("{\"failures\":%d,\"map\":\"%s\",\"checks\":["),Failures,*GetWorld()->GetMapName());
    for(int32 I=0;I<Checks.Num();++I){if(I)Json+=TEXT(",");Json+=FString::Printf(TEXT("{\"name\":\"%s\",\"passed\":%s}"),*Checks[I].Key,Checks[I].Value?TEXT("true"):TEXT("false"));}
    Json+=TEXT("]}");FFileHelper::SaveStringToFile(Json,*(FPaths::ProjectSavedDir()/TEXT("InfectedMiner/acceptance.json")));
    UE_LOG(LogTemp,Display,TEXT("MINER_ACCEPTANCE_COMPLETE failures=%d"),Failures);FPlatformMisc::RequestExitWithStatus(false,Failures?1:0);
}
void UInfectedMinerAudit::Step()
{
    const float Now=GetWorld()->GetTimeSeconds();const float Dt=LastStepTime<0?.05f:Now-LastStepTime;if(Dt<=SMALL_NUMBER)return;LastStepTime=Now;
    Clock+=Dt;StageClock+=Dt;
    if(Clock>100){Check(TEXT("completed_before_timeout"),false);Finish();return;}
    if(Stage==0)
    {
        Player=UGameplayStatics::GetPlayerCharacter(this,0);if(!Player.IsValid())return;
        for(TActorIterator<AInfectedMinerSpawner> It(GetWorld());It;++It){Spawner=*It;if(IsValid(It->LiveMiner))Miner=It->LiveMiner;}
        if(!Miner.IsValid())return;
        for(TActorIterator<APawn> It(GetWorld());It;++It)if(*It!=Player.Get()&&*It!=Miner.Get()&&It->ActorHasTag(TEXT("Enemy"))){It->SetActorTickEnabled(false);It->SetActorHiddenInGame(true);It->SetActorEnableCollision(false);if(auto* AI=Cast<AMonsterAIController>(It->GetController()))AI->SetDecisionEnabled(false);}
        if(GEngine)GEngine->Exec(GetWorld(),TEXT("DisableAllScreenMessages"));
        Check(TEXT("owned_mesh_and_clips"),Miner->VisualMesh&&Miner->IdleClip&&Miner->WalkClip&&Miner->AttackClip&&Miner->Combat->HitClip&&Miner->VisualMesh->GetPathName().StartsWith(TEXT("/Game/Monsters/InfectedMiner/")));
        Check(TEXT("shared_behavior_tree"),Cast<AMonsterAIController>(Miner->GetController())!=nullptr);
        UE_LOG(LogTemp,Display,TEXT("MINER_RUNTIME_ASSETS mesh=%s attack=%s"),*Miner->VisualMesh->GetPathName(),*Miner->AttackClip->GetPathName());
        PlayerStart=Player->GetActorLocation();Forward=(Miner->GetActorLocation()-PlayerStart).GetSafeNormal2D();Start=Miner->GetActorLocation();
        if(auto* PC=Cast<APlayerController>(Player->GetController()))PC->SetControlRotation(Forward.Rotation());
        if(auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>())H->Health=H->MaxHealth;
        Capture(TEXT("village-arrival"));Next(1);return;
    }
    if(!Player.IsValid())return;
    if(FMath::Fmod(StageClock,2.f)<.05f&&Miner.IsValid())
    {
        auto* AI=Cast<AMonsterAIController>(Miner->GetController());
        auto* BB=AI?AI->GetBlackboardComponent():nullptr;
        UE_LOG(LogTemp,Display,TEXT("MINER_AUDIT_STATE stage=%d state=%d target=%s action=%s enabled=%d visible=%d returning=%d distance=%.1f pos=%s"),Stage,int(Miner->State),*GetNameSafe(BB?BB->GetValueAsObject(TEXT("Target")):nullptr),AI?*AI->ActiveAction:TEXT("none"),AI?AI->bDecisionEnabled:0,BB?BB->GetValueAsBool(TEXT("Visible")):0,BB?BB->GetValueAsBool(TEXT("Returning")):0,FVector::Dist2D(Miner->GetActorLocation(),Player->GetActorLocation()),*Miner->GetActorLocation().ToString());
    }
    auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    auto* PC=Cast<APlayerController>(Player->GetController());
    auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Stage==1&&StageClock>5.f)
    {
        Check(TEXT("ai_chase_displacement"),FVector::Dist2D(Start,Miner->GetActorLocation())>60);
        Check(TEXT("walking_grounded"),Miner->GetCharacterMovement()->IsMovingOnGround());
        Check(TEXT("player_health_connected"),Health!=nullptr);if(!Health){Finish();return;}
        Place(145);Miner->InterruptAttack(.25f);BeforeHealth=Health->Health;BeforeHits=Miner->SuccessfulHits;
        ExpectedDamage=FMath::Max(1.f,Miner->AttackDamage-(Model?Model->Derived(TEXT("def")):0.f));Next(2);return;
    }
    if(Stage==2)
    {
        if(!Started&&Miner->State==ENurseState::Attack){Started=true;StageClock=0;}
        if(!Started)return;
        if(StageClock<Miner->ContactTime*.75f)Check(TEXT("windup_no_damage"),Health->Health==BeforeHealth);
        if(StageClock>Miner->ContactEnd+.3f){Check(TEXT("pickaxe_contact_damage_once"),FMath::IsNearlyEqual(Health->Health,BeforeHealth-ExpectedDamage)&&Miner->SuccessfulHits==BeforeHits+1);Capture(TEXT("pickaxe-contact"));Next(3);}return;
    }
    if(Stage==3&&StageClock>1.f)
    {
        Check(TEXT("no_duplicate_swing_damage"),Miner->SuccessfulHits==BeforeHits+1);
        Miner->InterruptAttack(.3f);Place(145);BeforeHits=Miner->SuccessfulHits;Next(4);return;
    }
    if(Stage==4)
    {
        if(!Started&&Miner->State==ENurseState::Attack){Started=true;StageClock=0;Place(650);}
        if(Started&&StageClock>2.f){Check(TEXT("dodge_avoids_damage"),Miner->SuccessfulHits==BeforeHits);Miner->InterruptAttack(.3f);Place(145);Next(5);}return;
    }
    if(Stage==5)
    {
        if(!Started&&Miner->State==ENurseState::Attack){Started=true;StageClock=0;BeforeHits=Miner->SuccessfulHits;Miner->InterruptAttack(1.8f);Check(TEXT("hit_reaction_entered"),Miner->State==ENurseState::Stagger);}
        if(Started&&StageClock>2.1f){Check(TEXT("interruption_cancels_pending_hit"),Miner->SuccessfulHits==BeforeHits);Check(TEXT("control_released"),Miner->State!=ENurseState::Stagger);Miner->InterruptAttack(.3f);Place(145);Next(6);}return;
    }
    if(Stage==6)
    {
        if(!Started&&Miner->State==ENurseState::Attack)
        {
            Started=true;StageClock=0;BeforeHits=Miner->SuccessfulHits;
            Wall=GetWorld()->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Wall.Get());Wall->SetRootComponent(Box);Box->SetBoxExtent(FVector(8,200,200));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();
            Wall->SetActorLocation((Miner->GetActorLocation()+Player->GetActorLocation())*.5);Wall->SetActorRotation(Forward.Rotation());
        }
        if(Started&&StageClock>1.85f){Check(TEXT("wall_blocks_damage"),Miner->SuccessfulHits==BeforeHits);Wall->Destroy();Miner->InterruptAttack(.3f);Place(320);Next(7);}return;
    }
    if(Stage==7&&StageClock>.4f)
    {
        auto* AI=Cast<AMonsterAIController>(Miner->GetController());if(AI)AI->SetDecisionEnabled(false);
        // Keep the weapon check separate from the following death/reward check,
        // even if a render hitch lets the held automatic input fire extra rounds.
        Miner->Health=10000.f;BeforeHealth=Miner->Health;
        if(PC){FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);PC->SetControlRotation((Miner->GetMesh()->GetSocketLocation(TEXT("spine_03"))-Eye).Rotation());PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.f));}
        Next(8);return;
    }
    if(Stage==8&&StageClock>.18f)
    {
        if(PC)PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));
        Next(81);return;
    }
    if(Stage==81&&StageClock>.6f)
    {
        Check(TEXT("real_weapon_input_hits_miner"),Miner->Health<BeforeHealth);Capture(TEXT("miner-front"));Next(9);return;
    }
    if(Stage==9&&StageClock>.7f)
    {
        Place(300);Miner->CorpseSeconds=6.f;Spawner->RespawnSeconds=1.f;
        DeathFloor=Miner->GetCharacterMovement()->CurrentFloor.HitResult.GetComponent();BeforeKills=Model->Kills();BeforeHits=Miner->SuccessfulHits;
        CalfLengthBefore=FVector::Distance(Miner->GetMesh()->GetSocketLocation(TEXT("calf_l")),Miner->GetMesh()->GetSocketLocation(TEXT("foot_l")));
        UGameplayStatics::ApplyDamage(Miner.Get(),10000,PC,Player.Get(),nullptr);UGameplayStatics::ApplyDamage(Miner.Get(),10000,PC,Player.Get(),nullptr);
        Check(TEXT("death_and_reward_once"),Miner->State==ENurseState::Dead&&Model->Kills()==BeforeKills+1);Check(TEXT("ragdoll_enabled"),Miner->GetMesh()->IsSimulatingPhysics());Next(10);return;
    }
    if(Stage==10&&StageClock>3.f)
    {
        auto Surface=MonsterSurfaceAudit::Ground(Miner->GetMesh(),DeathFloor.Get());
        // A corpse can cross a landscape component boundary. Keep the same
        // surface test, but query the actual world for samples outside that tile.
        if(Surface.Missing)
        {
            Surface=MonsterSurfaceAudit::FGroundResult();const auto Vertices=MonsterSurfaceAudit::WorldVertices(Miner->GetMesh());
            FCollisionQueryParams Q(SCENE_QUERY_STAT(MinerCorpseTerrain),true,Miner.Get());for(TActorIterator<APawn> It(GetWorld());It;++It)Q.AddIgnoredActor(*It);
            for(const auto& V:Vertices)Surface.Bounds+=V;
            for(int32 I=0;I<Vertices.Num();I+=17)
            {
                const auto V=Vertices[I];FHitResult Hit;
                const bool OnPrimary=DeathFloor.IsValid()&&DeathFloor->LineTraceComponent(Hit,V+FVector(0,0,400),V-FVector(0,0,600),Q)&&!Hit.bStartPenetrating&&Hit.ImpactNormal.Z>.6;
                // Start the fallback only 3cm above the sampled surface, so a
                // nearby wall cap or doorway above the corpse is not its floor.
                bool OnNeighbor=false;
                if(!OnPrimary)
                {
                    TArray<FHitResult> Hits;GetWorld()->LineTraceMultiByObjectType(Hits,V+FVector(0,0,3),V-FVector(0,0,600),FCollisionObjectQueryParams(ECC_WorldStatic),Q);
                    for(const auto& Candidate:Hits)if(!Candidate.bStartPenetrating&&Candidate.ImpactNormal.Z>.6&&(!OnNeighbor||Candidate.ImpactPoint.Z>Hit.ImpactPoint.Z)){Hit=Candidate;OnNeighbor=true;}
                    if(!OnNeighbor)UE_LOG(LogTemp,Display,TEXT("MINER_GROUND_MISSING point=%s floor=%s hits=%d"),*V.ToString(),*GetNameSafe(DeathFloor.Get()),Hits.Num());
                }
                if(OnPrimary||OnNeighbor)
                {const float Gap=V.Z-Hit.ImpactPoint.Z;Surface.Minimum=FMath::Min(Surface.Minimum,Gap);++Surface.Samples;if(Gap< -3)++Surface.Underground;}
                else ++Surface.Missing;
            }
        }
        const float CalfLengthAfter=FVector::Distance(Miner->GetMesh()->GetSocketLocation(TEXT("calf_l")),Miner->GetMesh()->GetSocketLocation(TEXT("foot_l")));
        UE_LOG(LogTemp,Display,TEXT("MINER_PHYSICS_LENGTH calf_before=%.3f calf_after=%.3f scale=%s"),CalfLengthBefore,CalfLengthAfter,*Miner->GetMesh()->GetSocketTransform(TEXT("calf_l"),RTS_Component).GetScale3D().ToString());
        Check(TEXT("corpse_limb_length_preserved"),FMath::Abs(CalfLengthAfter-CalfLengthBefore)<2.f);
        UE_LOG(LogTemp,Display,TEXT("MINER_SURFACE min=%.3f samples=%d missing=%d below=%d"),Surface.Minimum,Surface.Samples,Surface.Missing,Surface.Underground);
        Check(TEXT("corpse_render_surface_grounded"),Surface.Samples>100&&Surface.Missing==0&&Surface.Minimum> -3&&Surface.Minimum<20);
        Check(TEXT("death_cancels_damage"),Miner->SuccessfulHits==BeforeHits);
        const FVector Look=Surface.Bounds.GetCenter();const FVector Pos=Look+FVector(250,-280,220);auto* Cam=GetWorld()->SpawnActor<ACameraActor>(Pos,(Look-Pos).Rotation());if(PC)PC->SetViewTarget(Cam);
        Next(11);return;
    }
    if(Stage==11&&StageClock>.3f){Capture(TEXT("miner-corpse"));Next(12);return;}
    if(Stage==12&&StageClock>4.f){Check(TEXT("corpse_recycled"),!Miner.IsValid());Check(TEXT("one_new_miner_respawned"),Spawner.IsValid()&&IsValid(Spawner->LiveMiner)&&Spawner->LiveMiner!=Miner.Get());Finish();}
}
