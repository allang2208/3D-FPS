#include "NurseZombieAudit.h"
#include "NurseZombie.h"
#include "FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HighResScreenshot.h"
#include "TimerManager.h"

void UNurseZombieAudit::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if (World.IsGameWorld() && FParse::Param(FCommandLine::Get(),TEXT("NurseAudit")))
        World.GetTimerManager().SetTimer(Timer,this,&UNurseZombieAudit::Step,.05f,true,4.f);
}
void UNurseZombieAudit::Deinitialize()
{
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(Timer);
    Super::Deinitialize();
}
void UNurseZombieAudit::Check(const TCHAR* Name,bool Passed)
{
    UE_LOG(LogTemp,Display,TEXT("NURSE_ASSERT %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Name);
    if (!Passed) ++Failures;
}
void UNurseZombieAudit::Capture(const TCHAR* Name)
{
    if (FParse::Param(FCommandLine::Get(),TEXT("NurseCapture")))
        FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("NurseZombie")/(FString(Name)+TEXT(".png")),true,false);
}
void UNurseZombieAudit::PlaceForMelee()
{
    Player->SetActorLocation(PlayerStart,false,nullptr,ETeleportType::TeleportPhysics);
    Nurse->SetActorLocation(PlayerStart+Player->GetActorForwardVector()*115.f+FVector(0,0,-4),false,nullptr,ETeleportType::TeleportPhysics);
    Nurse->GetCharacterMovement()->StopMovementImmediately();
    Nurse->AggroRadius=1200.f;
}
void UNurseZombieAudit::Step()
{
    Clock+=.05f;StageClock+=.05f;
    if (Clock>65.f)
    {
        Check(TEXT("completed_before_timeout"),false);
        FPlatformMisc::RequestExitWithStatus(false,1);return;
    }
    if (Stage==0)
    {
        Player=UGameplayStatics::GetPlayerCharacter(this,0);
        if (!Player.IsValid()) return;
        int32 Count=0;
        for (TActorIterator<ANurseZombie> It(GetWorld());It;++It)
        {
            ++Count;
            if (!Nurse.IsValid() || FVector::DistSquared(It->GetActorLocation(),Player->GetActorLocation())<FVector::DistSquared(Nurse->GetActorLocation(),Player->GetActorLocation())) Nurse=*It;
        }
        if (Count!=2) return;
        Check(TEXT("two_saved_nurses_spawned"),Count==2);
        for (TActorIterator<ANurseZombie> It(GetWorld());It;++It) if (*It!=Nurse.Get()) It->AggroRadius=0;
        Start=Nurse->SpawnPosition;PlayerStart=Player->GetActorLocation();
        if (auto* Controller=Cast<APlayerController>(Player->GetController()))
            Controller->SetControlRotation(FRotator(0,(Nurse->GetActorLocation()-PlayerStart).Rotation().Yaw,0));
        Check(TEXT("matching_mesh_clips"),Nurse->GetMesh()->GetSkeletalMeshAsset() && Nurse->IdleClip && Nurse->WalkClip && Nurse->AttackClip);
        Capture(TEXT("village-arrival"));Stage=1;StageClock=0;return;
    }
    if (!Player.IsValid() && Stage!=10) return;
    auto* Health=Player.IsValid()?Player->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    auto* PC=Player.IsValid()?Cast<APlayerController>(Player->GetController()):nullptr;
    if (Stage==1 && StageClock>4.f)
    {
        UE_LOG(LogTemp,Display,TEXT("NURSE_CHASE_DIAG state=%d moved=%.1f velocity=%s tick=%d move_tick=%d input=%s start=%s now=%s player=%s"),int32(Nurse->State),FVector::Dist2D(Start,Nurse->GetActorLocation()),*Nurse->GetVelocity().ToString(),Nurse->IsActorTickEnabled(),Nurse->GetCharacterMovement()->IsComponentTickEnabled(),*Nurse->GetPendingMovementInputVector().ToString(),*Start.ToString(),*Nurse->GetActorLocation().ToString(),*Player->GetActorLocation().ToString());
        Check(TEXT("chase_actual_displacement"),FVector::Dist2D(Start,Nurse->GetActorLocation())>50.f);
        Check(TEXT("nurse_grounded"),Nurse->GetCharacterMovement()->IsMovingOnGround());
        Check(TEXT("player_health_connected"),Health!=nullptr);
        if (!Health) {FPlatformMisc::RequestExitWithStatus(false,1);return;}
        PlaceForMelee();Nurse->InterruptAttack(.25f);Nurse->SuccessfulHits=0;
        BeforeHealth=Health->Health;SawAttack=false;Stage=2;StageClock=0;return;
    }
    if (Stage==2)
    {
        if (!SawAttack && Nurse->State==ENurseState::Attack) {SawAttack=true;StageClock=0;}
        if (!SawAttack) return;
        if (StageClock<1.25f && Health->Health!=BeforeHealth) {Check(TEXT("no_windup_damage"),false);StageClock=1.25f;}
        if (StageClock>1.75f)
        {
            Check(TEXT("one_contact_hit"),Health->Health==BeforeHealth-Nurse->AttackDamage && Nurse->SuccessfulHits==1);
            Capture(TEXT("nurse-attack"));Stage=3;StageClock=0;
        }
        return;
    }
    if (Stage==3 && StageClock>1.8f)
    {
        Check(TEXT("no_duplicate_hit_in_swing"),Health->Health==BeforeHealth-Nurse->AttackDamage && Nurse->SuccessfulHits==1);
        BeforeHealth=Health->Health;SawAttack=false;Stage=4;StageClock=0;return;
    }
    if (Stage==4)
    {
        if (!SawAttack && Nurse->State==ENurseState::Attack)
        {
            SawAttack=true;StageClock=0;
            Player->SetActorLocation(PlayerStart-Player->GetActorForwardVector()*300.f,false,nullptr,ETeleportType::TeleportPhysics);
        }
        if (SawAttack && StageClock>3.5f)
        {
            Check(TEXT("evaded_swing_no_damage"),Health->Health==BeforeHealth);
            PlaceForMelee();SawAttack=false;Stage=5;StageClock=0;
        }
        return;
    }
    if (Stage==5)
    {
        if (!SawAttack && Nurse->State==ENurseState::Attack)
        {
            SawAttack=true;StageClock=0;Nurse->InterruptAttack(2.f);
        }
        if (SawAttack && StageClock>1.7f)
        {
            Check(TEXT("interrupted_swing_no_damage"),Health->Health==BeforeHealth);
            Nurse->AggroRadius=0;Nurse->InterruptAttack(10.f);
            Nurse->SetActorLocation(PlayerStart+Player->GetActorForwardVector()*260.f,false,nullptr,ETeleportType::TeleportPhysics);
            FVector Eye;FRotator Rotation;PC->GetPlayerViewPoint(Eye,Rotation);
            PC->SetControlRotation((Nurse->GetMesh()->GetSocketLocation(TEXT("spine_03"))-Eye).Rotation());
            Capture(TEXT("nurse-front"));Stage=6;StageClock=0;
        }
        return;
    }
    if (Stage==6 && StageClock>.6f)
    {
        FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);
        UE_LOG(LogTemp,Display,TEXT("NURSE_AIM_DIAG tick=%d control=%s view=%s eye=%s nurse=%s spine=%s mesh=%s"),Player->IsActorTickEnabled(),*PC->GetControlRotation().ToString(),*View.ToString(),*Eye.ToString(),*Nurse->GetActorLocation().ToString(),*Nurse->GetMesh()->GetSocketLocation(TEXT("spine_03")).ToString(),*Nurse->GetMesh()->GetComponentTransform().ToString());
        BeforeHealth=Nurse->Health;
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.f));
        Stage=7;StageClock=0;return;
    }
    if (Stage==7 && StageClock>.12f)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));
        Check(TEXT("real_gun_input_damages_mesh"),Nurse->Health<BeforeHealth);
        Nurse->CorpseSeconds=2.f;
        UGameplayStatics::ApplyDamage(Nurse.Get(),1000.f,PC,Player.Get(),nullptr);
        Check(TEXT("death_disables_damage_collision"),Nurse->State==ENurseState::Dead && Nurse->GetCapsuleComponent()->GetCollisionEnabled()==ECollisionEnabled::NoCollision);
        Check(TEXT("ragdoll_enabled"),Nurse->GetMesh()->IsSimulatingPhysics());
        BeforeHealth=Health->Health;Stage=8;StageClock=0;return;
    }
    if (Stage==8 && StageClock>1.f)
    {
        Capture(TEXT("nurse-ragdoll"));Stage=9;StageClock=0;return;
    }
    if (Stage==9 && StageClock>1.3f)
    {
        Check(TEXT("corpse_removed"),!Nurse.IsValid());
        Check(TEXT("dead_nurse_cannot_hit"),Health->Health==BeforeHealth);
        UGameplayStatics::ApplyDamage(Player.Get(),1000.f,nullptr,nullptr,nullptr);
        Stage=10;StageClock=0;return;
    }
    if (Stage==10 && StageClock>2.7f)
    {
        ACharacter* NewPlayer=UGameplayStatics::GetPlayerCharacter(this,0);
        Check(TEXT("player_respawned"),NewPlayer && NewPlayer!=Player.Get() && NewPlayer->FindComponentByClass<UFPSCombatHealthComponent>()->Health==100.f);
        UE_LOG(LogTemp,Display,TEXT("NURSE_ACCEPTANCE_COMPLETE failures=%d"),Failures);
        FPlatformMisc::RequestExitWithStatus(false,Failures?1:0);
    }
}
