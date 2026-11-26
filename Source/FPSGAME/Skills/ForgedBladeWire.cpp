#include "SkillWireAudit.h"
#include "ColdSteelSkillRules.h"
#include "Components/CapsuleComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelGenericMelee.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Serialization/JsonSerializer.h"

namespace ForgedBladeWire
{
bool Executioner(){ return FParse::Param(FCommandLine::Get(),TEXT("Executioner")); }
bool SnapshotCase(){return FParse::Param(FCommandLine::Get(),TEXT("ForgedBladeSnapshot"));}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,bool Modified,bool Fishtail=false)
{
    auto P=Model->Snapshot();
    P.Items.Reset(); P.ActiveWeaponSlot=6; P.ActiveProductionTool.Reset(); P.DungeonRun={};
    P.Stamina=100;P.bSprintExhausted=false;
    auto Item=Model->CreateItem(TEXT("ue_forged_steel_greatsword"));
    Item.InstanceId=TEXT("ForgedBladeWire");Item.Place=1;Item.Cell=6;
    if(Modified)
    {
        TSharedPtr<FJsonObject> Data;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return P;
        auto Mods=MakeShared<FJsonObject>();
        Mods->SetStringField(TEXT("blade_1"),Executioner()?TEXT("executioner_blade"):TEXT("hollow_blade"));
        if(Fishtail)Mods->SetStringField(TEXT("pommel"),TEXT("fishtail_pommel"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Mods);
        Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    }
    P.Items.Add(Item);return P;
}
void Freeze(ACharacter* P)
{
    P->SetActorTickEnabled(false);
    P->GetCharacterMovement()->SetComponentTickEnabled(false);
}
int32 Stacks(AActor* Target)
{
    if(const auto* Effects=Target->FindComponentByClass<UStatusEffectsComponent>())
        for(const auto& Effect:Effects->Snapshot())if(Effect.Type==TEXT("bleed"))return Effect.Stacks;
    return 0;
}
bool Modifiers(const FMeleeWeaponStats& Base,const FMeleeWeaponStats& Mod)
{
    const bool Exec=Executioner();
    return FMath::IsNearlyEqual(Mod.PhysicalAttack,Base.PhysicalAttack*(Exec?2.:1.05),.002)
        &&FMath::IsNearlyEqual(Mod.AttackSeconds,Base.AttackSeconds/(Exec?.5:1.2),.002)
        &&FMath::IsNearlyEqual(Mod.AttackStamina,Base.AttackStamina*(Exec?1.3:.85),.002)
        &&FMath::IsNearlyEqual(Mod.Modifiers.ToughnessDamage,Exec?1.5:1.,.002)
        &&Mod.Modifiers.MeleeHitBleedStacks==(Exec?0:2);
}
// Each fresh target starts with full toughness and without a previous reaction.
int32 SampleUnbroken(AFPSGAMECharacter* Attacker,UColdSteelStatusModel* Model,int32 Count)
{
    const FColdSteelItem Item=*Model->Equipped();
    const auto Stats=ColdSteelMelee::Evaluate(Item,Model);
    auto Shot=ColdSteelSkills::Snapshot(Attacker,&Item);
    Shot.AttackMeta=1;
    int32 Stunned=0;
    for(int32 i=0;i<Count;++i)
    {
        FActorSpawnParameters Spawn;
        Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Target=Attacker->GetWorld()->SpawnActor<ANurseZombie>(FVector(220,140,160),FRotator::ZeroRotator,Spawn);
        if(!Target)return INDEX_NONE;
        Target->SetReplicates(false);
        Target->Health=Target->MaxHealth=100000;
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        FMonsterToughnessBarTuning Tuning;Tuning.Maximum=100000;
        Combat->ConfigureToughnessBar(Tuning);
        const FHitResult Hit(Target,Target->GetCapsuleComponent(),Target->GetActorLocation(),-FVector::ForwardVector);
        const float Applied=ColdSteelSkills::ApplyHit(Attacker,Hit,Stats.Damage,FVector::ForwardVector,Shot);
        const bool bValid=Applied>0.f&&!Combat->IsToughnessBroken()&&Combat->LastAttackForm==EMonsterAttackForm::Blunt
            &&(!Combat->bStunned||FMath::IsNearlyEqual(Combat->NetStunSeconds,1.f,.02f));
        Stunned+=Combat->bStunned?1:0;
        Target->Destroy();
        if(!bValid)return INDEX_NONE;
    }
    return Stunned;
}
void Write(const TCHAR* Role,bool Stats,bool State,int32 Left,int32 Right,bool Extra,int32 Trials=0,int32 Stuns=0)
{
    auto O=MakeShared<FJsonObject>();O->SetStringField(TEXT("role"),Role);
    O->SetStringField(TEXT("blade"),Executioner()?TEXT("executioner"):TEXT("hollow"));
    O->SetBoolField(TEXT("passive_stats"),Stats);O->SetBoolField(TEXT("both_targets_status"),State);
    O->SetNumberField(TEXT("first_bleed_stacks"),Left);O->SetNumberField(TEXT("second_bleed_stacks"),Right);
    O->SetBoolField(TEXT("peer_or_local_contact_gate"),Extra);
    O->SetBoolField(TEXT("swapped_parts_during_swing_case"),SnapshotCase());
    if(Trials)
    {
        O->SetNumberField(TEXT("authority_unbroken_trials"),Trials);
        O->SetNumberField(TEXT("authority_unbroken_stuns"),Stuns);
    }
    O->SetBoolField(TEXT("passed"),Stats&&State&&Extra&&(!Trials||(Stuns>0&&Stuns<Trials)));
    FString Json,Path;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Json));
    if(FParse::Value(FCommandLine::Get(),TEXT("SkillWireOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
    UE_LOG(LogTemp,Display,TEXT("FORGED_BLADE_WIRE %s"),*Json);
}

bool CheckFishtail(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Model,ANurseZombie* Target)
{
    const auto Sword=Seed(Model,true,true).Items[0];
    const auto Stock=Seed(Model,true).Items[0];
    const auto Stats=ColdSteelMelee::Evaluate(Sword,Model);
    const double ExpectedAttack=ColdSteelMelee::Evaluate(Stock,Model).PhysicalAttack*1.08;
    UE_LOG(LogTemp,Display,TEXT("FORGED_FISHTAIL_PASSIVE actual=%.4f expected=%.4f"),Stats.PhysicalAttack,ExpectedAttack);
    if(!FMath::IsNearlyEqual(Stats.PhysicalAttack,ExpectedAttack,.002))return false;
    auto Shot=ColdSteelSkills::Snapshot(Pawn,&Sword);
    Shot.DamagePanel={80.,12.,20.,8.};Shot.CriticalRoll=1.f;
    const FHitResult Contact(Target,Target->GetCapsuleComponent(),Target->GetActorLocation(),-FVector::ForwardVector);
    const auto Probe=[&](uint8 Meta,double Multiplier)
    {
        Shot.AttackMeta=Meta;
        FWeaponDamageResult Result;
        ColdSteelSkills::ApplyHit(Pawn,Contact,120.f,FVector::ForwardVector,Shot,&Result);
        const auto& Incoming=Result.BeforeDefense;
        UE_LOG(LogTemp,Display,TEXT("FORGED_FISHTAIL_CONTACT meta=%u expected_scale=%.2f outgoing=%.2f/%.2f/%.2f/%.2f resolved=%d"),
            Meta,Multiplier,Incoming.BasePhysical,Incoming.AddedPhysical,Incoming.BaseMagic,Incoming.AddedMagic,Result.bResolved);
        return Result.bResolved&&FMath::IsNearlyEqual(Incoming.BasePhysical,80.*Multiplier,.002)
            &&FMath::IsNearlyEqual(Incoming.AddedPhysical,20.*Multiplier,.002)
            &&FMath::IsNearlyEqual(Incoming.BaseMagic,12.,.002)&&FMath::IsNearlyEqual(Incoming.AddedMagic,8.,.002);
    };
    auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
    UE_LOG(LogTemp,Display,TEXT("FORGED_FISHTAIL_SETUP snapshot=%d broken_before=%d"),Shot.bFishtailPommel,Combat->IsToughnessBroken());
    if(!Shot.bFishtailPommel||Combat->IsToughnessBroken()||!Probe(1,1.))return false;
    FMonsterToughnessBarTuning Tuning;Tuning.Maximum=1.f;Tuning.BrokenSeconds=30.f;Combat->ConfigureToughnessBar(Tuning);
    UGameplayStatics::ApplyDamage(Target,2000.f,Pawn->GetController(),Pawn,nullptr);
    return Combat->IsToughnessBroken()&&Probe(1,1.25)&&Probe(0x10,1.25)&&Probe(0x16,1.);
}
}

void ASkillWireAuditController::SetupForgedBlade(ANurseZombie* First,ANurseZombie* Second)
{
    if(HasAuthority()||bSetup||!First||!Second)return;
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());auto* PS=GetPlayerState<AColdSteelPlayerState>();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!P||!PS||PS->GetPawn()!=P||!Model||!Model->IsAudit())return;
    Model->CurrentPawn=P;Model->Current=ForgedBladeWire::Seed(Model,false);
    if(!Model->Equipped())return;
    const auto Base=ColdSteelMelee::Evaluate(*Model->Equipped(),Model);
    Model->Current=ForgedBladeWire::Seed(Model,true);
    const auto Mod=ColdSteelMelee::Evaluate(*Model->Equipped(),Model);
    bPaid=ForgedBladeWire::Modifiers(Base,Mod);
    for(ACharacter* C:TArray<ACharacter*>{P,First,Second})ForgedBladeWire::Freeze(C);
    P->SetActorLocation(FVector(0,0,100));First->SetActorLocation(FVector(120,-30,160));Second->SetActorLocation(FVector(120,30,160));
    Subject=First;ConversationSecond=Second;ExpectedCost=(RuneSwordRhythm::ContactStart+RuneSwordRhythm::ContactEnd)*.5f/Mod.AttackRate;
    Weapon=Model->Equipped()->InstanceId;Started=GetWorld()->GetTimeSeconds();bSetup=true;
}

void ASkillWireAuditController::TickForgedBlade()
{
    if(HasAuthority()||!IsLocalController()||!bSetup)return;
    const double Age=GetWorld()->GetTimeSeconds()-Started;
    if(bDone){if(Age>ExitAt)FPlatformMisc::RequestExit(false);return;}
    APawn* P=GetPawn();auto* PS=GetPlayerState<AColdSteelPlayerState>();if(!P||!PS)return;
    const double JoinWarmup=FParse::Param(FCommandLine::Get(),TEXT("ForgedBladeImmediateInput"))?0.:3.;
    if(ObservedChainCuts==INDEX_NONE&&Age>=JoinWarmup)
    {
        ObservedChainCuts=PS->RequestGenericMeleeStart(P,Weapon,ColdSteelGenericMelee::Sword,1);
        StarStatusFirstSeen=Age;
        UE_LOG(LogTemp,Display,TEXT("FORGED_BLADE_START serial=%d server=%.3f contactAfter=%.3f"),ObservedChainCuts,
            GetWorld()->GetGameState()->GetServerWorldTimeSeconds(),ExpectedCost);
        return;
    }
    if(!bHit&&ObservedChainCuts>0&&Age>=StarStatusFirstSeen+ExpectedCost)
    {
        FColdSteelNetHitReport Hit;Hit.ItemInstance=Weapon;Hit.ItemDefinition=TEXT("ue_forged_steel_greatsword");Hit.AttackMeta=1;Hit.Flags=(1<<3);
        Hit.GuardAttackSerial=1;Hit.GenericMeleeSerial=ObservedChainCuts;Hit.AimOrigin=P->GetPawnViewLocation();Hit.Direction=FVector::ForwardVector;
        Hit.HitNormal=-FVector::ForwardVector;Hit.ClientFireTime=GetWorld()->GetGameState()->GetServerWorldTimeSeconds();
        UE_LOG(LogTemp,Display,TEXT("FORGED_BLADE_CONTACT serial=%d stamp=%.3f"),ObservedChainCuts,Hit.ClientFireTime);
        for(auto* T:{Subject.Get(),Subject.Get(),ConversationSecond.Get()})
        {
            Hit.Target=T;Hit.ImpactPoint=T->GetActorLocation();PS->ServerReportHit(Hit);
        }
        bHit=true;
    }
    const bool Exec=ForgedBladeWire::Executioner();
    const int32 L=ForgedBladeWire::Stacks(Subject),R=ForgedBladeWire::Stacks(ConversationSecond);
    const auto* A=Subject->FindComponentByClass<UMonsterCombatComponent>();const auto* B=ConversationSecond->FindComponentByClass<UMonsterCombatComponent>();
    const bool Seen=Exec?(A->bStunned&&B->bStunned&&A->IsToughnessBroken()&&B->IsToughnessBroken()):(L==2&&R==2);
    if(Seen||Age>16.)
    {
        const bool Start=bHit&&ObservedChainCuts>0;
        ForgedBladeWire::Write(TEXT("client"),bPaid,Seen,L,R,Start);ServerResult(bPaid,Seen,Start,true,true);
        bDone=true;ExitAt=Age+3;
    }
}

void ASkillWireAuditGameMode::TickForgedBlade()
{
    const double Now=GetWorld()->GetTimeSeconds();
    if(ExitAt>=0.){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest)return;
    auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!P||!PS||!Host||!Host->IsAudit())return;
    const bool Exec=ForgedBladeWire::Executioner();
    if(!GuestModel)
    {
        GuestModel=Host->CreateShadowModel(ForgedBladeWire::Seed(Host,false));GuestModel->CurrentPawn=P;PS->ShadowModel=GuestModel;P->NetShadowProfile=GuestModel;
        const auto Base=ColdSteelMelee::Evaluate(*GuestModel->Equipped(),GuestModel);
        GuestModel->Current=ForgedBladeWire::Seed(GuestModel,true);
        bStarPassed=ForgedBladeWire::Modifiers(Base,ColdSteelMelee::Evaluate(*GuestModel->Equipped(),GuestModel));
        PS->SetActorTickEnabled(false);ForgedBladeWire::Freeze(P);P->SetActorLocation(FVector(0,0,100));P->ForceNetUpdate();
        P->FindComponentByClass<UFPSCombatHealthComponent>()->Health=1000;
        Target=GetWorld()->SpawnActor<ANurseZombie>(FVector(120,-30,160),FRotator::ZeroRotator);
        ConversationSecond=GetWorld()->SpawnActor<ANurseZombie>(FVector(120,30,160),FRotator::ZeroRotator);
        for(auto* T:{Target.Get(),ConversationSecond.Get()})
        {
            T->Health=T->MaxHealth=100000;ForgedBladeWire::Freeze(T);
            if(auto* AI=Cast<AMonsterAIController>(T->GetController()))AI->SetDecisionEnabled(false);
            auto* Combat=T->FindComponentByClass<UMonsterCombatComponent>();
            FMonsterToughnessBarTuning Tune;Tune.Maximum=Exec?1.f:100000.f;Tune.BrokenSeconds=30.f;Combat->ConfigureToughnessBar(Tune);
            Combat->BladeResistance=.8f;Combat->BluntResistance=.1f;
        }
        if(Exec)UGameplayStatics::ApplyDamage(ConversationSecond,2000.f,Guest,P,nullptr);
        bSawThirdPersonMotion=!ForgedBladeWire::SnapshotCase()&&(!Exec||ConversationSecond->FindComponentByClass<UMonsterCombatComponent>()->IsToughnessBroken());
        Target->ForceNetUpdate();ConversationSecond->ForceNetUpdate();ConversationStarted=Now;
    }
    if(ForgedBladeWire::SnapshotCase()&&!bSawThirdPersonMotion)
        if(const auto* Swing=PS->GenericMeleeReceipts.Find(1);Swing&&Swing->Targets.IsEmpty())
        {
            auto& Equipped=GuestModel->Current.Items[0];
            Equipped.Data=GuestModel->CreateItem(Equipped.Definition).Data;
            bSawThirdPersonMotion=true;
            UE_LOG(LogTemp,Display,TEXT("FORGED_BLADE_SAME_INSTANCE_SWITCH before contact"));
        }
    if(Now-LastSetup>.5)
    {
        LastSetup=Now;Guest->ClientSetupConversation(0,Target,ConversationSecond,nullptr);
        if(const auto* R=PS->GenericMeleeReceipts.Find(1))
            UE_LOG(LogTemp,Display,TEXT("FORGED_BLADE_RECEIPT from=%.3f until=%.3f acceptedTargets=%d"),R->ContactFrom,R->ContactUntil,R->Targets.Num());
    }
    const auto* A=Target->FindComponentByClass<UMonsterCombatComponent>();const auto* B=ConversationSecond->FindComponentByClass<UMonsterCombatComponent>();
    const int32 L=ForgedBladeWire::Stacks(Target),R=ForgedBladeWire::Stacks(ConversationSecond);
    if(Exec)bSawThirdPersonFlame|=A->bStunned&&B->bStunned&&A->IsToughnessBroken()&&B->IsToughnessBroken()&&
        A->LastAttackForm==EMonsterAttackForm::Blunt&&B->LastAttackForm==EMonsterAttackForm::Blunt&&FMath::IsNearlyEqual(A->NetStunSeconds,1.f,.02f);
    else bSawThirdPersonFlame|=L==2&&R==2&&A->LastAttackForm==EMonsterAttackForm::Blade;
    if(Guest->bReported||Now-ConversationStarted>26.)
    {
        bool Peers=Guest->bReported&&Guest->bPassed&&bSawThirdPersonMotion;
        if(ForgedBladeWire::SnapshotCase()&&Peers)
        {
            const bool Fishtail=ForgedBladeWire::CheckFishtail(P,GuestModel,Target);
            UE_LOG(LogTemp,Display,TEXT("FORGED_FISHTAIL_AUTHORITY physical_only normal_and_heavy=%d"),Fishtail);
            Peers=Fishtail;
        }
        const int32 Trials=Exec&&Peers?32:0;
        const int32 Stuns=Trials?ForgedBladeWire::SampleUnbroken(P,GuestModel,Trials):0;
        ForgedBladeWire::Write(TEXT("host"),bStarPassed,bSawThirdPersonFlame,L,R,Peers,Trials,Stuns);ExitAt=Now+3;
    }
}
