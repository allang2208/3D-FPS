#include "BowSkillTrainingAuditCommandlet.h"
#include "ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowArrow.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 UBowSkillTrainingAuditCommandlet::Main(const FString& Params)
{
    UE_LOG(LogTemp,Display,TEXT("BOW_SKILL_AUDIT revision=5 (explicit local controller identity)"));
    const FString OriginalCommand=FCommandLine::Get();
    const FString ProfileName=TEXT("BowSkillAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("BowSkillTrainingAudit -ColdSteelProfile=")+ProfileName));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("BowSkillAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+ProfileName)return 2;
    auto Shutdown=[&](){GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*OriginalCommand);};
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failed=0;
    auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString())
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Row->SetStringField(TEXT("detail"),Detail);Rows.Add(MakeShared<FJsonValueObject>(Row));if(!OK)++Failed;
        UE_LOG(LogTemp,Display,TEXT("BOW_SKILL_AUDIT %s %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);
    };
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);
    for(auto& Binding:Seed.QuickBindings)Binding={};
    Seed.Level=20;Seed.Experience=0;Seed.Kills=0;Seed.Stamina=100;Seed.DungeonRun={};
    auto Item=Model->CreateItem(TEXT("bow_dark"));Item.Place=1;Item.Cell=6;Seed.Items.Add(Item);
    const FString Ammo=Model->AmmoDefinitionFor(Item);Seed.AmmoPouch.FindOrAdd(Ammo)=100;
    for(auto& Pair:Seed.Skills){Pair.Value.Level=1;Pair.Value.Experience=0;}
    const bool Seeded=Model->CommitState(Seed);Check(Seeded,TEXT("isolated profile seed"),Model->ResultMessage());
    if(!Seeded){Shutdown();return 2;}
    const auto Baseline=Model->Snapshot();
    auto* Player=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    // No viewport/ULocalPlayer is created by an unattended commandlet. Production
    // SetPlayer establishes this flag; make the same ownership explicit here.
    PC->SetAsLocalPlayerController();
    auto* LocalPS=World->SpawnActor<AColdSteelPlayerState>();LocalPS->SetOwner(PC);PC->SetPlayerState(LocalPS);PC->Possess(Player);
    Player->SetPlayerState(LocalPS);
    Check(Player->IsPlayerControlled()&&Player->IsLocallyControlled(),TEXT("fixture is a real local player for kill attribution"));
    auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();Bow->Character=Player;
    Bow->Camera=Player->FindComponentByClass<UCameraComponent>();Bow->InstanceId=Item.InstanceId;Bow->ArrowId=Ammo;
    auto Reset=[&](UColdSteelStatusModel* M)
    {M->Current=Baseline;M->RewardedVictims.Reset();M->CurrentPawn.Reset();M->bTrainingDirty=false;};
    bool SpeedsOK=true;double MaxError=0.;
    const double Base=ColdSteelInventory::Number(Item,TEXT("draw_seconds"),1.4);
    for(int32 Hands=1;Hands<=20;++Hands)for(int32 Mastery=1;Mastery<=20;++Mastery)
    {
        Model->Current.Skills.FindChecked(TEXT("dexterousHands")).Level=Hands;
        Model->Current.Skills.FindChecked(TEXT("bowMastery")).Level=Mastery;
        const double Expected=FMath::Max(.3,Base/(1.+Hands*.0125)*(1.-Mastery*.01));
        const auto Stats=ColdSteelBow::Evaluate(Item,Model);Bow->SetStage(EBowStage::Drawing,0.f);
        const double Error=FMath::Max(FMath::Abs(Stats.Draw-Expected),FMath::Abs(double(Bow->DrawSeconds)-Expected));
        MaxError=FMath::Max(MaxError,Error);SpeedsOK&=Error<1.e-5;
    }
    Check(SpeedsOK,TEXT("400 level pairs: panel and real draw clock stack once"),FString::Printf(TEXT("maxError=%.9f; both20=%.6fs"),MaxError,Bow->DrawSeconds));
    const float Full=Bow->DrawSeconds;
    Check(!ColdSteelBow::IsPerfectRelease(Full-.001f,Full)&&ColdSteelBow::IsPerfectRelease(Full,Full)
        &&ColdSteelBow::IsPerfectRelease(Full+.2f,Full)&&!ColdSteelBow::IsPerfectRelease(Full+.201f,Full),TEXT("perfect window follows shortened draw, retains 0.20s"));
    Reset(Model);
    // Exercise the actual standalone launch, then retain its immutable shot for impacts.
    Bow->bArrowNocked=true;Bow->bSteadyHeld=true;Bow->AimProgress=1.f;
    Check(Bow->LooseArrow(1.f,true),TEXT("standalone perfect arrow launch"));
    ABowArrow* Fired=nullptr;for(TActorIterator<ABowArrow> It(World);It;++It)if(It->GetOwner()==Player)Fired=*It;
    if(!Fired){Check(false,TEXT("arrow exists"));Shutdown();return 3;}
    auto Shot=Fired->Shot;Shot.CriticalChance=-100.f;
    Check(Shot.bPerfectBowRelease&&Shot.MasteryId==TEXT("bowMastery"),TEXT("launch snapshot carries both perfect and mastery identity"));
    Fired->Destroy();
    auto SpawnTarget=[&]()
    {
        auto* Target=World->SpawnActor<ANurseZombie>(FVector(0,5000,500),FRotator::ZeroRotator);
        // No BeginPlay/rendered animation proxy in this empty commandlet world.
        // Keep the production TakeDamage/kill callbacks, skip the corpse animation owner.
        Target->Knockdown=nullptr;
        Target->Health=Target->MaxHealth=10000;Target->ExperienceReward=1;return Target;
    };
    auto Impact=[&](AFPSGAMECharacter* Shooter,ANurseZombie* Target,FColdSteelSkillShot FiredShot,bool Critical,float Damage=100.f)
    {
        FActorSpawnParameters Spawn;Spawn.Owner=Shooter;Spawn.Instigator=Shooter;
        auto* Arrow=World->SpawnActor<ABowArrow>(FVector(0,4000,500),FRotator::ZeroRotator,Spawn);
        Arrow->Damage=Damage;Arrow->Shot=FiredShot;Arrow->Velocity=FVector(9800,0,0);
        FHitResult Hit(Target,Target->GetMesh(),Target->GetActorLocation(),FVector(-1,0,0));
        Hit.BoneName=Critical?FName(TEXT("head")):NAME_None;
        Arrow->ApplyHit(Hit);return TPair<ABowArrow*,FHitResult>(Arrow,Hit);
    };
    auto XP=[&](UColdSteelStatusModel* M,int32 Hands,int32 Mastery,const FString& Name)
    {
        const auto H=M->DexterousHandsProgress();const auto B=M->MasteryProgress(TEXT("bowMastery"));
        Check(H.Experience==Hands&&B.Experience==Mastery,Name,
            FString::Printf(TEXT("hands=%d/%d bow=%d/%d"),H.Experience,Hands,B.Experience,Mastery));
    };
    for(int32 Perfect=0;Perfect<2;++Perfect)for(int32 Critical=0;Critical<2;++Critical)for(int32 Kill=0;Kill<2;++Kill)
    {
        Reset(Model);auto* Target=SpawnTarget();if(Kill)Target->Health=1;
        auto S=Shot;S.bPerfectBowRelease=Perfect!=0;auto Contact=Impact(Player,Target,S,Critical!=0);
        const FString Case=FString::Printf(TEXT("impact perfect=%d critical=%d kill=%d"),Perfect,Critical,Kill);
        const int32 H=Perfect?(Kill?10:4):0,B=(Kill?10:1)+(Critical?4:0);
        XP(Model,H,B,Case);Contact.Key->ApplyHit(Contact.Value);XP(Model,H,B,Case+TEXT(" duplicate callback"));
        if(Kill){Model->AwardKill(Target,1);XP(Model,H,B,Case+TEXT(" duplicate kill callback"));}
        Contact.Key->Destroy();Target->Destroy();
    }
    Reset(Model);
    auto* SequenceTarget=SpawnTarget();auto A=Impact(Player,SequenceTarget,Shot,false);A.Key->Destroy();
    SequenceTarget->Health=1;A=Impact(Player,SequenceTarget,Shot,false);A.Key->Destroy();SequenceTarget->Destroy();
    XP(Model,14,11,TEXT("separate hit then kill adds 4+10 / 1+10 exactly"));
    for(const FName Tag:{FName(TEXT("Summoned")),FName(TEXT("NoSkillTraining")),FName(TEXT("Friendly")),FName(TEXT("Companion"))})
    {
        Reset(Model);auto* Target=SpawnTarget();Target->Tags.Add(Tag);auto Contact=Impact(Player,Target,Shot,false);
        XP(Model,0,0,TEXT("excluded target ")+Tag.ToString());Contact.Key->Destroy();Target->Destroy();
    }
    Reset(Model);auto* Corpse=SpawnTarget();Corpse->Health=0;Corpse->State=ENurseState::Dead;
    A=Impact(Player,Corpse,Shot,false);XP(Model,0,0,TEXT("corpse awards neither skill"));A.Key->Destroy();Corpse->Destroy();
    Reset(Model);auto* Immune=SpawnTarget();
    A=Impact(Player,Immune,Shot,false,0.f);XP(Model,0,0,TEXT("no applied damage awards neither skill"));A.Key->Destroy();Immune->Destroy();
    Reset(Model);auto* DotTarget=SpawnTarget();A=Impact(Player,DotTarget,Shot,false);A.Key->Destroy();
    DotTarget->Health=0;DotTarget->State=ENurseState::Dead;Model->AwardKill(DotTarget,1);
    XP(Model,4,1,TEXT("later kill outside arrow scope does not add direct-hit training"));DotTarget->Destroy();
    for(const FName Capped:{FName(TEXT("dexterousHands")),FName(TEXT("bowMastery"))})
    {
        Reset(Model);Model->Current.Skills.FindChecked(Capped).Level=20;auto* Target=SpawnTarget();Target->Health=1;
        A=Impact(Player,Target,Shot,false);XP(Model,Capped==TEXT("dexterousHands")?0:10,Capped==TEXT("bowMastery")?0:10,TEXT("cap independent: ")+Capped.ToString());
        A.Key->Destroy();Target->Destroy();
    }
    Reset(Model);Model->Current.Skills.FindChecked(TEXT("dexterousHands")).Experience=298;
    Model->Current.Skills.FindChecked(TEXT("bowMastery")).Experience=299;
    auto* LevelTarget=SpawnTarget();A=Impact(Player,LevelTarget,Shot,false);
    Check(Model->DexterousHandsProgress().Level==2&&Model->DexterousHandsProgress().Experience==2
        &&Model->MasteryProgress(TEXT("bowMastery")).Level==2&&Model->MasteryProgress(TEXT("bowMastery")).Experience==0,TEXT("one hit levels both skills without losing remainder"));
    Check(Model->CommitState(Model->Snapshot()),TEXT("isolated training persisted"));
    Check(Model->ReloadProfile()&&Model->DexterousHandsProgress().Experience==2&&Model->MasteryProgress(TEXT("bowMastery")).Level==2,TEXT("both progress values survive reload"));
    A.Key->Destroy();LevelTarget->Destroy();
    // A remote-owner model checks attribution through the production server bow path.
    Reset(Model);auto GuestBaseline=Baseline;GuestBaseline.NetworkProfileId=FGuid::NewGuid();
    auto* Shadow=Model->CreateShadowModel(GuestBaseline);
    auto* RemotePC=World->SpawnActor<ABowSkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    PS->SetOwner(RemotePC);PS->ShadowModel=Shadow;PS->SlotName=TEXT("ColdSteel_")+ProfileName+TEXT("_Guest");RemotePC->SetPlayerState(PS);
    auto* Remote=World->SpawnActor<AFPSGAMECharacter>(FVector(1000,0,0),FRotator::ZeroRotator);RemotePC->Possess(Remote);
    Remote->SetPlayerState(PS);Remote->NetShadowProfile=Shadow;Shadow->CurrentPawn=Remote;
    // World clamps a single large delta; advance several bounded frames instead.
    for(int32 Frame=0;Frame<60;++Frame)World->Tick(LEVELTICK_TimeOnly,.1f);
    Check(World->GetTimeSeconds()>2.f&&Remote->IsPlayerControlled()&&!Remote->IsLocallyControlled(),TEXT("remote player identity and positive draw-start clock"));
    for(const bool Perfect:{false,true})
    {
        Shadow->Current=GuestBaseline;Shadow->RewardedVictims.Reset();PS->LastBowShotAt=-100.;
        PS->ServerSetBowDraw_Implementation(Remote,Item.InstanceId,true,0.f);
        const float Release=PS->BowDrawSeconds+.1f;PS->BowDrawStartedAt=World->GetTimeSeconds()-Release;
        FColdSteelInventoryRequest Request;Request.Item=Item.InstanceId;Request.Pawn=Remote;Request.Charge=1.f;
        Request.Eye=Remote->GetPawnViewLocation();Request.Origin=Request.Eye;Request.Direction=Remote->GetBaseAimRotation().Vector();
        Request.BowReleaseElapsed=Perfect?Release:-1.f;FString Reason;
        Check(PS->ExecuteBowShot(Request,Shadow,Reason),Perfect?TEXT("authority perfect release"):TEXT("authority ordinary release"),Reason);
        ABowArrow* RemoteArrow=nullptr;for(TActorIterator<ABowArrow> It(World);It;++It)if(It->GetOwner()==Remote&&!It->IsActorBeingDestroyed())RemoteArrow=*It;
        if(RemoteArrow)
        {
            Check(RemoteArrow->Shot.bPerfectBowRelease==Perfect,TEXT("authority snapshot carries verified timing"));
            RemoteArrow->Shot.CriticalChance=-100;auto* Target=SpawnTarget();Target->Health=1;
            FHitResult Hit(Target,Target->GetMesh(),Target->GetActorLocation(),FVector(-1,0,0));RemoteArrow->ApplyHit(Hit);
            XP(Shadow,Perfect?10:0,10,TEXT("authority kill credits guest only"));XP(Model,0,0,TEXT("host is untouched by guest arrow"));
            RemoteArrow->Destroy();Target->Destroy();
        }
        else Check(false,TEXT("authority arrow exists"));
    }
    auto Root=MakeShared<FJsonObject>();Root->SetStringField(TEXT("profile"),ProfileName);Root->SetNumberField(TEXT("speedPairs"),400);
    Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failed"),Failed);Root->SetArrayField(TEXT("results"),Rows);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    FString Dir=FPaths::ProjectSavedDir()/TEXT("BowSkillTrainingAudit20261013");FParse::Value(*Params,TEXT("ReportDir="),Dir);
    IFileManager::Get().MakeDirectory(*Dir,true);FFileHelper::SaveStringToFile(Json,*(Dir/TEXT("result.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp,Display,TEXT("BOW_SKILL_AUDIT_DONE checks=%d failed=%d"),Rows.Num(),Failed);
    Shutdown();
    return Failed?1:0;
}
