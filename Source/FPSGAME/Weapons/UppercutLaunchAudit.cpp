#include "RuneSwordAuditCommandlet.h"
#include "RuneSwordComponent.h"
#include "FPSMeleeLightningComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/WarhammerUppercutMotion.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Skills/MeleeToughnessTuning.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/WolfMonster.h"
#include "../Monsters/HeQueMonster.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterCoreStats.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

#if WITH_EDITOR
static FAutoConsoleCommand UppercutLaunchAuditCommand(
    TEXT("fps.AuditUppercutLaunch"),TEXT("Run the isolated uppercut launch commandlet fixtures without starting PIE."),
    FConsoleCommandDelegate::CreateLambda([]()
    {
        auto* Audit=NewObject<URuneSwordAuditCommandlet>();Audit->AddToRoot();
        const int32 Result=Audit->Main(TEXT("-UppercutLaunchOnly"));Audit->RemoveFromRoot();
        UE_LOG(LogTemp,Display,TEXT("UPPERCUT_LAUNCH_AUDIT exit=%d"),Result);
    }));
#endif

// Explicitly invoked, isolated headless regression. No player save or map startup.
int32 URuneSwordAuditCommandlet::AuditUppercutLaunch()
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("UppercutLaunchAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("UppercutLaunchAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("UppercutLaunchAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    const auto Shutdown=[&](){GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);};
    int32 Failed=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString())
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Row->SetStringField(TEXT("detail"),Detail);Rows.Add(MakeShared<FJsonValueObject>(Row));Failed+=!OK;
        UE_LOG(LogTemp,Display,TEXT("UPPERCUT_LAUNCH_AUDIT %s %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);
    };
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Seed.QuickBindings)B={};
    Seed.Stamina=150;Seed.bSprintExhausted=false;Seed.SwordUppercutCooldown=0;Seed.DungeonRun={};
    for(auto& Pair:Seed.Skills){Pair.Value.Level=1;Pair.Value.Experience=0;}
    auto* Player=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    Player->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();PC->Possess(Player);
    auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword->Character=Player;
    Sword->Camera=Player->FindComponentByClass<UCameraComponent>();
    // Load the real uppercut clip/compatible rig for the public sword entry gate.
    Sword->Viewmodel=NewObject<USkeletalMeshComponent>(Player);Player->AddInstanceComponent(Sword->Viewmodel);
    Sword->Viewmodel->SetupAttachment(Sword->Camera);Sword->Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Sword->Viewmodel->RegisterComponent();
    Sword->Viewmodel->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny")));
    Sword->UppercutStandard.LoadSynchronous();
    auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();Tool->Character=Player;
    uint32 Serial=0;
    for(const bool Hammer:{false,true})
    {
        const FString Weapon=Hammer?TEXT("warhammer"):TEXT("two_handed_sword");
        auto Item=Model->CreateItem(Hammer?TEXT("ue_steel_warhammer"):TEXT("ue_rune_sword"));Item.Place=1;Item.Cell=6;
        Seed.Items={Item};Check(Model->CommitState(Seed),Weapon+TEXT(" isolated equipment"),Model->ResultMessage());
        Sword->InstanceId=Hammer?FString():Item.InstanceId;
        for(int32 Species=0;Species<3;++Species)
        for(int32 Scenario=0;Scenario<5;++Scenario)
        {
            static const TCHAR* SpeciesNames[]={TEXT("nurse_capsule_fallback"),TEXT("wolf"),TEXT("heque_native_airborne")};
            static const TCHAR* ScenarioNames[]={TEXT("normal"),TEXT("already_broken"),TEXT("exact_break_this_hit"),TEXT("guarded"),TEXT("recovering")};
            const FString Name=Weapon+TEXT("/")+SpeciesNames[Species]+TEXT("/")+ScenarioNames[Scenario];
            Sword->bUppercut=false;Tool->bBluntUppercut=false;Tool->BluntServerReadyAt=0.f;
            if(Hammer)Tool->ServerBeginBluntUppercut_Implementation(++Serial);
            else Sword->BeginUppercut();
            const bool Started=Hammer?Tool->bBluntUppercut:Sword->bUppercut;
            const auto& Shot=Hammer?Tool->BluntUppercutShot:Sword->SwingSkills;
            Check(Started&&Shot.bMelee&&Shot.AttackMeta==SwordUppercut::AttackMeta,Name+TEXT(" real attack entry"),
                FString::Printf(TEXT("started=%d melee=%d meta=%d status=%s"),Started,Shot.bMelee,Shot.AttackMeta,*Sword->UppercutStatusText()));
            if(!Started)continue;
            // Remove random criticals only; retain each real weapon's damage,
            // form, toughness multipliers and production hit path.
            if(Hammer)Tool->BluntUppercutShot.CriticalChance=-100.f;else Sword->SwingSkills.CriticalChance=-100.f;
            const FTransform Aim=Player->GetMeleeAimTransform();
            const FVector Position=Aim.TransformPosition(FVector(115,0,0));
            ACharacter* Target=nullptr;
            const EMonsterRank Rank=Scenario==0?EMonsterRank::Normal:EMonsterRank::Elite;
            if(Species==0){auto* N=World->SpawnActor<ANurseZombie>(Position,FRotator::ZeroRotator);N->Health=N->MaxHealth=100000;N->Rank=Rank;Target=N;}
            if(Species==1){auto* W=World->SpawnActor<AWolfMonster>(Position,FRotator::ZeroRotator);W->Health=W->MaxHealth=100000;W->Rank=Rank;Target=W;}
            if(Species==2){auto* H=World->SpawnActor<AHeQueMonster>(Position,FRotator::ZeroRotator);H->Health=H->MaxHealth=100000;H->Rank=Rank;Target=H;}
            auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
            MonsterCoreStats::ApplyToughnessProfile(Target);
            // Exact boundary includes resistance and the actual weapon modifier.
            const float PerHit=MeleeToughness::Uppercut*(1.f-FMath::Clamp(Combat->ToughnessResistance(Shot.AttackForm),0.f,.9f))*Shot.ToughnessDamageMultiplier;
            if(Scenario!=0)
            {
                FMonsterToughnessBarTuning Tuning;Tuning.Maximum=PerHit*3.f;Tuning.BrokenSeconds=3.f;Tuning.RefillSeconds=4.f;
                Combat->ConfigureToughnessBar(Tuning);
            }
            const auto Prime=[&](float Base)
            {
                Combat->ApplyHitWithToughnessScale(1.f,[&](){Combat->ReceiveHit(1.f,Player,EMonsterAttackForm::Impact);return 1.f;},
                    Base/(1.f-FMath::Clamp(Combat->ImpactResistance,0.f,.9f)));
            };
            if(Scenario==1||Scenario==4)Prime(Combat->ToughnessThreshold);
            if(Scenario==2)Prime(Combat->ToughnessThreshold-PerHit);
            if(Scenario==4){for(int32 I=0;I<33;++I)World->Tick(LEVELTICK_TimeOnly,.1f);Combat->CanReceiveLaunchOrKnockdown();}
            const auto PhaseBefore=Combat->GetToughnessPhase();const float RemainingBefore=Combat->DisplayToughness();
            const int32 BreaksBefore=Combat->Breaks;
            auto* Move=Target->GetCharacterMovement();Move->bRunPhysicsWithNoController=true;
            // Empty commandlet worlds do not run actor/component BeginPlay.
            // Supply the movement activation normally done by that lifecycle.
            UE_LOG(LogTemp,Display,TEXT("UPPERCUT_FIXTURE %s active=%d valid=%d enemy=%d"),*Name,Move->IsActive(),Move->HasValidData(),UFPSMeleeLightningComponent::IsEnemy(Target,Player));
            Move->SetUpdatedComponent(Target->GetCapsuleComponent());Move->Activate(true);
            Check(Move->IsActive()&&Move->HasValidData()&&UFPSMeleeLightningComponent::IsEnemy(Target,Player),Name+TEXT(" movement/enemy fixture"));
            Target->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
            const FVector Before=Target->GetActorLocation();
            if(Hammer)
            {
                // Match the production sub-frame arc, not a single chord joining
                // the low/right windup and high/left end of the whole stroke.
                for(float T=WarhammerUppercutMotion::LoadedSource;T<RuneSwordUppercutMotion::Finish&&Tool->BluntUppercutHitActors.IsEmpty();T+=1.f/240.f)
                    Tool->SweepBluntUppercut(T,FMath::Min(T+1.f/240.f,RuneSwordUppercutMotion::Finish),Aim,Aim);
            }
            else
            {
                FHitResult Hit(Target,Target->GetCapsuleComponent(),Position,FVector(-1,0,0));
                Sword->ApplySwingHits({Hit},FVector::ForwardVector);
            }
            const bool Contact=Hammer?Tool->BluntUppercutHitActors.Contains(Target):Sword->HitActors.Contains(Target);
            const bool Launched=Move->HandlePendingLaunch();const FVector Velocity=Move->Velocity;
            const bool Expected=Scenario<=2;
            const bool PhaseOK=Scenario==0?PhaseBefore==EMonsterToughnessPhase::Legacy:
                Scenario==1?PhaseBefore==EMonsterToughnessPhase::Broken:
                Scenario==4?PhaseBefore==EMonsterToughnessPhase::Recovering:PhaseBefore==EMonsterToughnessPhase::Guarded;
            const bool BreakOK=Scenario!=2||(FMath::IsNearlyEqual(RemainingBefore,PerHit,.001f)&&Combat->Breaks==BreaksBefore+1&&Combat->IsToughnessBroken());
            Check(Contact&&PhaseOK&&BreakOK&&Launched==Expected&&(!Expected||FMath::IsNearlyEqual(Velocity.Z,SwordUppercut::LaunchUpCM,1.f)),Name,
                FString::Printf(TEXT("contact=%d phase=%d->%d remaining=%.3f perHit=%.3f breaks=%d->%d launched=%d velocity=%s"),
                    Contact,int32(PhaseBefore),int32(Combat->GetToughnessPhase()),RemainingBefore,PerHit,BreaksBefore,Combat->Breaks,Launched,*Velocity.ToString()));
            if(Expected&&Launched)
            {
                for(int32 I=0;I<6;++I)
                {
                    Combat->TickComponent(1.f/60.f,LEVELTICK_All,&Combat->PrimaryComponentTick);
                    Move->TickComponent(1.f/60.f,LEVELTICK_All,&Move->PrimaryComponentTick);
                }
                const FVector Travel=Target->GetActorLocation()-Before;
                Check(Travel.Z>10.f&&Travel.Size2D()<30.f,Name+TEXT(" movement survives follow-up reaction"),Travel.ToString());
            }
            Target->Destroy();Sword->bUppercut=false;Tool->bBluntUppercut=false;
        }
    }
    auto Root=MakeShared<FJsonObject>();Root->SetStringField(TEXT("profile"),Slot);Root->SetNumberField(TEXT("checks"),Rows.Num());
    Root->SetNumberField(TEXT("failed"),Failed);Root->SetArrayField(TEXT("results"),Rows);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    const FString Output=FPaths::ProjectSavedDir()/TEXT("UppercutLaunchAudit20261015/result.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);FFileHelper::SaveStringToFile(Json,*Output);
    Shutdown();return Failed?1:0;
}
