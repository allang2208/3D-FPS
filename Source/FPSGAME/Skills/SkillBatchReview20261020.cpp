#include "SkillNetworkAuditCommandlet.h"
#include "ColdSteelSkillRules.h"
#include "FPSFireMagicComponent.h"
#include "FPSFireballComponent.h"
#include "FPSLightningHasteComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

// Opt-in native fixture. No map BeginPlay, sockets, rendered/audio acceptance
// or user profile: RPC implementation/receipt calls below are direct calls.
int32 USkillNetworkAuditCommandlet::RunSkillBatchReview(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("SkillNetworkAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SkillNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("SkillBatchReview"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const FString& Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("SKILL_BATCH_REVIEW %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Seed.QuickBindings)B={};
    for(auto& Skill:Seed.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    Seed.NetworkProfileId=FGuid::NewGuid();Seed.DungeonRun={};Seed.LightningHasteCooldown=0;Seed.MeteorCooldown=0;
    auto Sword=Host->CreateItem(TEXT("ue_rune_sword"));Sword.Place=1;Sword.Cell=6;
    auto Hammer=Host->CreateItem(TEXT("ue_steel_warhammer"));
    auto Staff=Host->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=6;
    Seed.Items={Staff};
    auto* Shadow=Host->CreateShadowModel(Seed);
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=Health->MaxHealth;
    auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();
    auto* Hands=Pawn->FindComponentByClass<UFPSFireballComponent>();
    auto* Haste=Pawn->FindComponentByClass<UFPSLightningHasteComponent>();
    Check(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled()&&Pawn->IsPlayerControlled(),TEXT("remote authority fixture identity"));

    auto Old=Seed;Old.SkillProgressVersion=24;Old.Skills.Remove(TEXT("bluntMastery"));
    Old.Skills.FindChecked(TEXT("swordMastery")).Level=7;Old.Skills.FindChecked(TEXT("swordMastery")).Experience=123;
    Old.LightningHasteCooldown=13;Old.LightningHasteCooldownDuration=50;
    Check(ColdSteelSkills::Migrate(Old)&&Old.SkillProgressVersion==25&&Old.Skills.Contains(TEXT("bluntMastery"))
        &&Old.Skills.FindChecked(TEXT("swordMastery")).Level==7&&Old.Skills.FindChecked(TEXT("swordMastery")).Experience==123
        &&Old.LightningHasteCooldown==13,TEXT("v24 migration preserves existing progression and haste cooldown"));
    Check(!ColdSteelSkills::Migrate(Old),TEXT("migration is idempotent"));
    auto* Save=NewObject<UColdSteelProfileSave>();Save->Profile=Old;TArray<uint8> Blob;
    const bool Encoded=ColdSteelProfileTransfer::SaveToBlob(Save,Blob);
    auto* Decoded=Encoded?ColdSteelProfileTransfer::BlobToSave(Blob):nullptr;
    Check(Decoded&&Decoded->Profile.Skills.Contains(TEXT("bluntMastery"))
        &&Decoded->Profile.Skills.FindChecked(TEXT("swordMastery")).Experience==123&&Decoded->Profile.LightningHasteCooldown==13,
        TEXT("network profile serialization retains mastery and haste fields"));

    for(int32 L:{1,5,10,15,20})
    {
        Shadow->Current.Skills.FindChecked(TEXT("bluntMastery")).Level=L;
        Check(FMath::IsNearlyEqual(Shadow->AdditionalWeaponDamage(Hammer,100.f),100.f+1.25f*L,.001f),
            FString::Printf(TEXT("blunt level %d percentage damage without old flat bonus"),L));
    }
    Shadow->Current.Skills.FindChecked(TEXT("swordMastery")).Level=20;
    Check(Shadow->AdditionalWeaponDamage(Sword,100.f)==120.f&&Shadow->AdditionalWeaponDamage(Staff,100.f)==100.f,
        TEXT("sword flat damage remains scoped and does not leak to staff"));
    Check(FMath::IsNearlyEqual(Shadow->MeleeMasteryIntervalMultiplier(Hammer),.8f)
        &&Shadow->MeleeMasteryIntervalMultiplier(Staff)==1.f,TEXT("blunt interval bonus is scoped and reaches 0.8"));
    Shadow->Current=Seed;
    const auto Haste1=Shadow->LightningHasteStats(1),Haste20=Shadow->LightningHasteStats(20);
    Check(FMath::IsNearlyEqual(Haste1.MoveBonus,.1f)&&FMath::IsNearlyEqual(Haste1.ActionBonus,.05f)&&Haste1.Duration==20.f
        &&FMath::IsNearlyEqual(Haste20.MoveBonus,.29f)&&FMath::IsNearlyEqual(Haste20.ActionBonus,.145f)&&Haste20.Duration==29.5f,
        TEXT("haste initial and maximum growth match configured values"));
    TArray<APawn*> Enemies;
    for(int32 I=0;I<11;++I){auto* E=World->SpawnActor<APawn>();E->Tags.Add(TEXT("Enemy"));Enemies.Add(E);}
    auto* Friend=World->SpawnActor<APawn>();Friend->Tags.Add(TEXT("Friendly"));
    auto* Summon=World->SpawnActor<APawn>();Summon->Tags.Add(TEXT("Summoned"));
    for(int32 Count:{0,5,6,10,11})
    {
        const auto HostBefore=Host->MasteryProgress(TEXT("lightningHaste"));
        Shadow->Current=Seed;Haste->Start(Haste1,42+Count,Shadow);
        Check(FMath::IsNearlyEqual(Haste->ActionMultiplier(),1.05f)&&FMath::IsNearlyEqual(Haste->MoveMultiplier(),1.1f),
            FString::Printf(TEXT("haste %d-kill batch activates independent action/move speeds"),Count));
        Haste->ObserveKill(Friend);Haste->ObserveKill(Summon);
        for(int32 I=0;I<Count;++I){Haste->ObserveKill(Enemies[I]);Haste->ObserveKill(Enemies[I]);}
        Haste->FinishForRemoval();Haste->FinishForRemoval();
        const int32 Expected=1+3*Count+(Count>10?40:Count>5?15:0);
        Check(Shadow->MasteryProgress(TEXT("lightningHaste")).Experience==Expected
            &&Host->MasteryProgress(TEXT("lightningHaste")).Experience==HostBefore.Experience
            &&Haste->ActionMultiplier()==1.f&&Haste->MoveMultiplier()==1.f,
            FString::Printf(TEXT("haste %d kills: guest-only XP %d, no duplicates/allies, removal restores speed"),Count,Expected));
    }
    Shadow->Current=Seed;Haste->Start(Haste1,80,Shadow);Haste->State.StartedAt=Haste->Clock()-Haste1.Duration-1.;
    Haste->TickComponent(0.f,LEVELTICK_All,&Haste->PrimaryComponentTick);
    Check(Haste->Remaining()==0.f&&Haste->ActionMultiplier()==1.f&&Shadow->MasteryProgress(TEXT("lightningHaste")).Experience==1,
        TEXT("haste expiry settles once and restores speeds"));
    Shadow->Current=Seed;Haste->Start(Haste1,81,Shadow);Health->Health=0;
    Haste->TickComponent(0.f,LEVELTICK_All,&Haste->PrimaryComponentTick);Health->Health=Health->MaxHealth;
    Check(Haste->Remaining()==0.f&&Shadow->MasteryProgress(TEXT("lightningHaste")).Experience==1,
        TEXT("haste death cleanup settles earned cast experience"));

    // Receipt logic is exercised on the local GI profile, as on a client.
    // It deliberately does not claim that a packet crossed a NetDriver.
    const auto SetPaidMeteor=[&](uint32 Id)
    {
        Host->Current=Seed;Host->CurrentPawn.Reset();Host->Current.Mana=20.f;
        Host->Current.MeteorCooldown=Host->Current.MeteorCooldownDuration=30.f;
        Fire->MeteorLocalCastId=Id;Fire->MeteorResolvedCastId=0;Fire->MeteorPendingRefund=10.f;
        Fire->bMeteorAwaitingResult=true;Fire->CommittedSkill=NAME_None;
    };
    SetPaidMeteor(100);
    Fire->NetMeteorCastResult(1,7,100);const float Refunded=Host->Snapshot().Mana;
    Fire->NetMeteorCastResult(1,7,100);
    Check(Refunded==30.f&&Host->Snapshot().Mana==Refunded&&Host->FireMagicCooldown(TEXT("meteor"))==0.f&&!Fire->bMeteorAwaitingResult,
        TEXT("rejected meteor release refunds exact payment and clears cooldown once"));
    SetPaidMeteor(101);Fire->NetMeteorCastResult(1,7,100);
    Check(Host->Snapshot().Mana==20.f&&Host->FireMagicCooldown(TEXT("meteor"))==30.f&&Fire->bMeteorAwaitingResult,
        TEXT("old meteor receipt cannot refund or cancel a newer cast"));
    Fire->NetMeteorCastResult(1,0,101);Fire->NetMeteorCastResult(1,7,101);
    Check(Host->Snapshot().Mana==20.f&&Host->FireMagicCooldown(TEXT("meteor"))==30.f&&!Fire->bMeteorAwaitingResult,
        TEXT("accepted meteor cannot be refunded by a later rejection"));
    SetPaidMeteor(102);Fire->CommittedSkill=TEXT("meteor");Hands->RecordGesturePayment(30.f,20.f,true);
    Fire->CancelPending();Fire->NetMeteorCastResult(0,6,102);
    Check(Host->Snapshot().Mana==30.f&&Host->FireMagicCooldown(TEXT("meteor"))==0.f&&Fire->CommittedSkill.IsNone(),
        TEXT("meteor windup cancel refunds once despite a delayed prepare rejection"));
    Shadow->Current=Seed;PS->PendingCastSkill=TEXT("meteor");PS->PendingCastPaidMana=10.f;
    PS->PendingIdentifiedCastId=200;PS->PendingCastPawn=Pawn;Shadow->Current.Mana=20.f;
    FColdSteelNetCastRequest Cancel;Cancel.SkillId=TEXT("meteor");Cancel.Phase=2;Cancel.CastId=199;Cancel.SourcePawn=Pawn;
    PS->ExecuteCastRequest(Cancel);
    Check(PS->PendingCastSkill==TEXT("meteor")&&Shadow->Snapshot().Mana==20.f,TEXT("server ignores an old meteor cancellation"));
    Cancel.CastId=200;PS->ExecuteCastRequest(Cancel);PS->ExecuteCastRequest(Cancel);
    Check(PS->PendingCastSkill.IsNone()&&Shadow->Snapshot().Mana==30.f,TEXT("server cancels current meteor and refunds once"));
    auto Meteor=Shadow->FireMagicStats(TEXT("meteor"));
    FColdSteelNetCastRequest Release;Release.SkillId=TEXT("meteor");Release.CastId=201;Release.AimPoint=FVector(100,0,2000);Release.AimNormal=FVector::UpVector;
    Check(!Fire->NetRelease(Pawn,Release,Shadow,Meteor),TEXT("server rejects meteor at a hovering point without ground"));

    Shadow->Current=Seed;Shadow->Current.Items={Sword};
    auto* Blade=Pawn->FindComponentByClass<URuneSwordComponent>();Blade->Character=Pawn;
    Blade->SwingDamage=10.f;Blade->SwingTrainingHits=0;Blade->HitActors.Reset();
    Blade->SwingSkills=ColdSteelSkills::Snapshot(Pawn,&Sword);
    Blade->SwingSkills.CriticalRoll=1.f;Blade->SwingSkills.CriticalChance=0.f;
    auto* First=World->SpawnActor<ANurseZombie>(FVector(150,0,500),FRotator::ZeroRotator);
    auto* Second=World->SpawnActor<ANurseZombie>(FVector(170,50,500),FRotator::ZeroRotator);
    for(auto* Target:{First,Second})
    {
        // No BeginPlay/animation graph in this fixture. Death reward logic is
        // under test; the humanoid pose-snapshot death presentation is not.
        Target->Knockdown=nullptr;
        Target->Health=Target->MaxHealth=100000;
        Target->GetCharacterMovement()->Activate(true);
        Target->Combat->ConfigureToughnessBar(FMonsterToughnessBarTuning());
    }
    const auto Contact=[](ANurseZombie* Target)
    {return FHitResult(Target,Target->GetCapsuleComponent(),Target->GetActorLocation(),-FVector::ForwardVector);};
    Blade->ApplySwingHits({Contact(First),Contact(Second)},FVector::ForwardVector);
    Check(Blade->SwingTrainingHits==2&&Shadow->MasteryProgress(TEXT("swordMastery")).Experience==5,
        TEXT("sword actual hit path grants two hit XP plus one multi-target bonus"));
    Blade->ApplySwingHits({Contact(First),Contact(Second)},FVector::ForwardVector);
    Check(Shadow->MasteryProgress(TEXT("swordMastery")).Experience==5,TEXT("repeated sword contacts grant no duplicate XP"));
    Blade->HitActors.Reset();Blade->SwingTrainingHits=0;First->Health=1.f;
    Blade->ApplySwingHits({Contact(First)},FVector::ForwardVector);
    Check(First->Combat->IsDead()&&Blade->SwingTrainingHits==1,TEXT("lethal first sword contact remains in multi-target count"));
    First->Destroy();Second->Destroy();

    // Real physics queries, with an allied pawn in front of an enemy/wall.
    const auto Box=[&](AActor* A,const FVector& Location)
    {
        auto* B=NewObject<UBoxComponent>(A);A->AddInstanceComponent(B);A->SetRootComponent(B);
        B->SetBoxExtent(FVector(20));B->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        B->SetCollisionObjectType(ECC_WorldDynamic);B->SetCollisionResponseToAllChannels(ECR_Block);
        B->RegisterComponent();A->SetActorLocation(Location);return B;
    };
    Shadow->Current.Items={Staff};
    auto* Floor=World->SpawnActor<AActor>();Box(Floor,FVector(200,0,380))->SetBoxExtent(FVector(100,100,20));
    Release.AimPoint=FVector(200,0,400);
    Check(Fire->NetRelease(Pawn,Release,Shadow,Meteor),TEXT("server accepts meteor on visible real ground"));
    auto* MeteorWall=World->SpawnActor<AActor>();Box(MeteorWall,FVector(100,0,480))->SetBoxExtent(FVector(10,90,120));
    Release.CastId=202;
    Check(!Fire->NetRelease(Pawn,Release,Shadow,Meteor),TEXT("server rejects meteor ground behind a solid wall"));
    Fire->FinishFireMagicForRemoval();Floor->Destroy();MeteorWall->Destroy();
    Box(Friend,FVector(1000,0,500));Box(Enemies[0],FVector(1200,0,500));
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(SkillBatchFriendly),false,Pawn);
    Check(RangedAttackQuery::LineTraceSingle(World,Pawn,Hit,FVector(900,0,500),FVector(1500,0,500),ECC_Visibility,Q)
        &&Hit.GetActor()==Enemies[0],TEXT("ranged line skips allied pawn and reaches enemy"));
    auto* Wall=World->SpawnActor<AActor>();Box(Wall,FVector(1100,0,500));
    Check(RangedAttackQuery::SweepSingle(World,Pawn,Hit,FVector(900,0,500),FVector(1500,0,500),FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(8),Q)
        &&Hit.GetActor()==Wall,TEXT("ranged sweep skips ally but still stops at wall"));
    TArray<FHitResult> Hits;
    RangedAttackQuery::SweepMulti(World,Pawn,Hits,FVector(900,0,500),FVector(1500,0,500),FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(8),Q);
    Check(!Hits.IsEmpty()&&Hits.Last().GetActor()==Wall
        &&!Hits.ContainsByPredicate([&](const auto& H){return H.GetActor()==Friend||H.GetActor()==Enemies[0];}),
        TEXT("ranged multi-sweep retains solid cover after allied blocker"));

    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);
    Root->SetBoolField(TEXT("real_network_transport"),false);Root->SetBoolField(TEXT("map_begin_play"),false);
    Root->SetArrayField(TEXT("results"),Rows);FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    const FString Path=FPaths::ProjectDir()/TEXT("SourceAssets/SkillBatchReview20261020/native-result.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
