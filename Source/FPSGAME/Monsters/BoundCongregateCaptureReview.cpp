#include "BoundCongregate.h"
#include "BoundCongregateCaptureComponent.h"
#include "MonsterCombatComponent.h"
#include "../Development/DevelopmentSpawnComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

// Explicit user-requested review. Transient world, no BeginPlay, AI, map or saves.
int32 ReviewBoundCongregateCaptureV31()
{
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("CongregateCaptureReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 1;
    UClass* Type=LoadClass<ABoundCongregate>(nullptr,TEXT("/Game/Monsters/BoundCongregate/BP_BoundCongregate.BP_BoundCongregate_C"));
    if(!Type){World->DestroyWorld(false);return 1;}
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Monster=World->SpawnActor<ABoundCongregate>(Type,FVector(0,0,225),FRotator::ZeroRotator,Spawn);
    auto* Victim=World->SpawnActor<ACharacter>(ACharacter::StaticClass(),FVector(1000,0,96),FRotator::ZeroRotator,Spawn);
    if(!Monster||!Victim){World->DestroyWorld(false);return 1;}
    Monster->GetMesh()->bDisableClothSimulation=true;
    FString Report=TEXT("Scope: saved blueprint references and production capture transitions in a transient world; no BeginPlay, AI, multiplayer transport, animation render or player save.\n");
    int32 Failed=0,Count=0;
    auto Check=[&](const TCHAR* Name,bool Good)
    {++Count;if(!Good)++Failed;Report+=FString::Printf(TEXT("%s %s\n"),Good?TEXT("PASS"):TEXT("FAIL"),Name);};
    Check(TEXT("saved tuning: move 240, pull 195, turn 100, range 3000, health 300"),
        FMath::IsNearlyEqual(Monster->WalkSpeed,240.f)&&FMath::IsNearlyEqual(Monster->TentaclePullSpeed,195.f)&&
        FMath::IsNearlyEqual(Monster->GetCharacterMovement()->RotationRate.Yaw,100.f)&&
        FMath::IsNearlyEqual(Monster->TentacleRange,3000.f)&&FMath::IsNearlyEqual(Monster->TentacleMaxHealth,300.f));
    Check(TEXT("V29 visual / V28 flurry and bite retained"),Monster->VisualMesh&&Monster->BiteClip&&Monster->FlurryClip&&
        Monster->VisualMesh->GetPathName().Contains(TEXT("TentacleReachV29"))&&Monster->BiteClip->GetPathName().Contains(TEXT("CombatV28"))&&
        Monster->FlurryClip->GetPathName().Contains(TEXT("CombatV28")));
    bool Clips=true;
    for(const auto* Clip:{Monster->IdleClip.Get(),Monster->MoveClip.Get(),Monster->TurnLeftClip.Get(),Monster->TurnRightClip.Get(),
        Monster->BiteClip.Get(),Monster->FlurryClip.Get(),Monster->HitClip.Get(),Monster->DeathClip.Get()})
    {
        const auto* Skeleton=Monster->VisualMesh?Monster->VisualMesh->GetSkeleton():nullptr;
        Clips&=Clip&&Clip->GetSkeleton()&&Skeleton&&(Clip->GetSkeleton()==Skeleton||
            Skeleton->GetCompatibleSkeletons().ContainsByPredicate([&](const TSoftObjectPtr<USkeleton>& Other){return Other.Get()==Clip->GetSkeleton();}));
    }
    Check(TEXT("eight required clips present on same or declared-compatible skeletons"),Clips);
    float Health=0,MaxHealth=0;FText Name;
    Check(TEXT("vitals display name"),Monster->Combat->GetVitals(Health,MaxHealth,Name)&&Name.ToString()==TEXT("缚群 M-88"));
    auto* Catalog=NewObject<UDevelopmentSpawnComponent>();
    const auto* Entry=Catalog->GetMonsters().FindByPredicate([](const FDevelopmentMonsterEntry& E){return E.Id==TEXT("BoundCongregate");});
    Check(TEXT("F6 name and stable class path"),Entry&&Entry->Name.ToString()==TEXT("缚群 M-88")&&Entry->CharacterClass.ToString().Contains(TEXT("BP_BoundCongregate")));
    auto* Capture=UBoundCongregateCaptureComponent::GetOrAdd(Victim);
    auto SetCapture=[&]()
    {
        Monster->NetState.TentacleRecoveryStartedAt=-1.;Monster->TentacleHealth=300.f;
        Monster->NetState.State=EBoundCongregateState::TentacleDrag;Monster->NetState.StartedAt=World->GetTimeSeconds();
        Monster->NetState.CapturedTarget=Victim;Monster->NetState.TentacleAim=Victim->GetActorLocation();
        Monster->SetTarget(Victim);
        return Capture&&Capture->Capture(Monster);
    };
    Check(TEXT("capture starts"),SetCapture());
    const auto Effects=UStatusEffectsComponent::GetOrCreate(Victim)->Snapshot();
    Check(TEXT("persistent entangled debuff"),Effects.ContainsByPredicate([](const FStatusEffectView& V){return V.Type==TEXT("tentacleEntangled")&&V.Persistent;}));
    Monster->InterruptAttack(2.f);
    Check(TEXT("stagger retains capture and pauses drag"),Capture->IsHeld()&&Monster->Controlled()&&Monster->CapturePullVelocity(Victim).IsNearlyZero());
    Victim->SetActorLocation(FVector(0,1000,96));const float BeforeYaw=Monster->GetActorRotation().Yaw;
    Monster->Tick(.1f);
    Check(TEXT("stagger cannot turn toward target"),FMath::IsNearlyEqual(BeforeYaw,Monster->GetActorRotation().Yaw));
    FHitResult Hit;Hit.HitObjectHandle=FActorInstanceHandle(Monster);Hit.BoneName=TEXT("attack_tentacle_40");
    Hit.ImpactPoint=Monster->GetMesh()->GetSocketLocation(Hit.BoneName);Hit.Location=Hit.ImpactPoint;
    FColdSteelSkillShot Shot;Shot.bRifle=true;Shot.BulletSpeedCM=10000.f;
    auto* GI=NewObject<UGameInstance>();auto* Model=NewObject<UColdSteelStatusModel>(GI);
    const float BodyBefore=Monster->Health;
    auto Shotgun=Shot;Shotgun.bRifle=false;Shotgun.BulletSpeedCM=0.f;Shotgun.MasteryId=TEXT("shotgunMastery");
    Check(TEXT("shotgun without shatter enchantment damages tentacle"),
        Model->ApplySkillWeaponHit(Victim,Hit,99.f,FVector::ForwardVector,Shotgun)==99.f&&Monster->TentacleHealth==201.f);
    auto MachineGun=Shotgun;MachineGun.MasteryId=TEXT("machineGunMastery");
    Check(TEXT("machine gun without shatter enchantment damages tentacle"),
        Model->ApplySkillWeaponHit(Victim,Hit,100.f,FVector::ForwardVector,MachineGun)==100.f&&Monster->TentacleHealth==101.f);
    Check(TEXT("299 total gun damage leaves one tentacle HP and retains capture"),
        Model->ApplySkillWeaponHit(Victim,Hit,100.f,FVector::ForwardVector,Shot)==100.f&&Monster->TentacleHealth==1.f&&Capture->IsHeld());
    Check(TEXT("final HP breaks capture without torso damage"),
        Model->ApplySkillWeaponHit(Victim,Hit,1.f,FVector::ForwardVector,Shot)==1.f&&!Capture->IsHeld()&&Monster->Health==BodyBefore);
    Check(TEXT("escape during stagger keeps body reaction and smooth coil recovery"),Monster->Controlled()&&Monster->TentacleRecovering()&&Monster->NetState.ReleasedWrap==1.f);
    Check(TEXT("late part report never falls through to torso damage"),
        Model->ApplySkillWeaponHit(Victim,Hit,100.f,FVector::ForwardVector,Shot)==0.f&&Monster->Health==BodyBefore);
    ColdSteelCombat::OnHit(Hit,Victim,3);
    Check(TEXT("part contact cannot poison torso after break"),!Monster->FindComponentByClass<UColdSteelPoisonComponent>());
    Check(TEXT("second capture starts"),SetCapture());
    Capture->HitRestraintWithQuickMelee();
    Check(TEXT("one quick-melee contact releases (V32)"),!Capture->IsHeld()&&Monster->TentacleRecovering());
    Check(TEXT("contact after release cannot count again"),!Capture->HitRestraintWithQuickMelee());
    Check(TEXT("third capture starts"),SetCapture());
    Victim->SetActorLocation(FVector(340,0,96));Monster->Tick(0.f);
    Check(TEXT("close capture releases into bite and retains independent recovery"),
        !Capture->IsHeld()&&Monster->NetState.State==EBoundCongregateState::Bite&&Monster->TentacleRecovering());
    Report+=FString::Printf(TEXT("checks=%d failed=%d\n"),Count,Failed);
    const FString Directory=FPaths::ProjectDir()/TEXT("SourceAssets/BoundCongregateMeshy20261006/ReviewV31");
    IFileManager::Get().MakeDirectory(*Directory,true);
    FFileHelper::SaveStringToFile(Report,*(Directory/TEXT("capture-review.txt")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp,Display,TEXT("BOUND_CAPTURE_V31 checks=%d failed=%d"),Count,Failed);
    Victim->Destroy();Monster->Destroy();World->DestroyWorld(false);
    return Failed?1:0;
}
