#include "UnknownJoinAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "../Monsters/UnknownHumanoidBow.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/LightningDamage.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSIceWall.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/NetDriver.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace UnknownJoin
{
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(),TEXT("UnknownJoinAudit"));
#endif
}
double Clock(UWorld* W){return W->GetGameState()?W->GetGameState()->GetServerWorldTimeSeconds():W->GetTimeSeconds();}
void Freeze(ACharacter* P)
{
    P->SetActorTickEnabled(false);P->GetCharacterMovement()->DisableMovement();P->GetCharacterMovement()->SetComponentTickEnabled(false);
    if(auto* Survival=P->FindComponentByClass<UFPSSurvivalComponent>())Survival->SetComponentTickEnabled(false);
}
void Write(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Passed,const FString& Role,UWorld* W)
{
    FString Root;FParse::Value(FCommandLine::Get(),TEXT("UnknownJoinOutput="),Root);
    if(Root.IsEmpty())return;
    IFileManager::Get().MakeDirectory(*Root,true);
    auto Data=MakeShared<FJsonObject>();Data->SetBoolField(TEXT("passed"),Passed);Data->SetArrayField(TEXT("cases"),Rows);
    Data->SetBoolField(TEXT("udp"),W->GetNetDriver()!=nullptr);Data->SetBoolField(TEXT("rendered"),false);
#if DO_ENABLE_NET_TEST
    if(auto* Net=W->GetNetDriver()){Data->SetNumberField(TEXT("lag_ms"),Net->PacketSimulationSettings.PktLag);Data->SetNumberField(TEXT("loss_percent"),Net->PacketSimulationSettings.PktLoss);}
#endif
    FString Json;FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(Root/(Role+TEXT(".json"))));
}
TArray<TSharedPtr<FJsonValue>> ClientRows;
bool ClientPassed=true;
}

struct FUnknownJoinAuditAccess
{
    static AUnknownHumanoid* Spawn(UWorld* W,EUnknownRole Role,int32 Level,int32 Index)
    {
        const FTransform At(FRotator::ZeroRotator,FVector(20000+Index*1000,0,200));
        auto* A=W->SpawnActorDeferred<AUnknownHumanoid>(AUnknownHumanoid::StaticClass(),At,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!A||!A->Configure(Role,Level)){if(A)A->Destroy();return nullptr;}
        A->AutoPossessAI=EAutoPossessAI::Disabled;A->bAlwaysRelevant=true;
        UGameplayStatics::FinishSpawningActor(A,At);UnknownJoin::Freeze(A);A->HealthRegen=0;
        return A;
    }
    static bool Start(AUnknownHumanoid* A)
    {
        const auto Role=A->Loadout.Role;
        A->SetAction(Role==EUnknownRole::Melee?EUnknownAction::Swing:Role==EUnknownRole::Gun?EUnknownAction::Reload:
            Role==EUnknownRole::Bow?EUnknownAction::SwapWeapon:EUnknownAction::Cast,600.f);
        A->Motion.Windup=500.f;A->Motion.Preparation=2.f;A->Motion.Recovery=.4f;
        if(Role==EUnknownRole::Bow){A->bBowBlades=true;A->OnRep_BowMode();}
        if(Role!=EUnknownRole::Magic)return true;
        A->Motion.Skill=TEXT("dragonBreath");
        FColdSteelNetCastRequest R;R.SourcePawn=A;R.CastId=401;
        auto* M=A->Sheet.Get();bool OK=true;
        R.SkillId=TEXT("iceArmor");auto Ice=M->IceArmorStats(2);Ice.Duration=600;Ice.PulseSeconds=600;
        OK&=A->FindComponentByClass<UFPSIceArmorComponent>()->NetRelease(A,R,M,Ice);
        R.SkillId=TEXT("lightningHaste");++R.CastId;auto Haste=M->LightningHasteStats(2);Haste.Duration=600;
        OK&=A->FindComponentByClass<UFPSLightningHasteComponent>()->NetRelease(A,R,M,Haste);
        R.SkillId=TEXT("flameArmor");++R.CastId;auto Fire=M->FireMagicStats(R.SkillId,2);Fire.Duration=600;
        OK&=A->FindComponentByClass<UFPSFireMagicComponent>()->NetRelease(A,R,M,Fire);
        R.SkillId=TEXT("stormDomain");++R.CastId;auto Domain=M->ElectricMagicStats(R.SkillId,2);Domain.Duration=600;
        OK&=A->FindComponentByClass<UFPSElectricMagicComponent>()->NetRelease(A,R,M,Domain);
        R.SkillId=TEXT("dragonBreath");++R.CastId;R.AimPoint=FVector(70,0,45);
        Fire=M->FireMagicStats(R.SkillId,2);Fire.Duration=600;
        OK&=A->FindComponentByClass<UFPSFireMagicComponent>()->NetRelease(A,R,M,Fire);
        return OK;
    }
    static void End(AUnknownHumanoid* A)
    {
        A->SetAction(EUnknownAction::Ready);
        if(A->Loadout.Role==EUnknownRole::Bow){A->bBowBlades=false;A->OnRep_BowMode();}
        if(auto* C=A->FindComponentByClass<UFPSIceArmorComponent>())C->FinishForRemoval();
        if(auto* C=A->FindComponentByClass<UFPSLightningHasteComponent>())C->FinishForRemoval();
        if(auto* C=A->FindComponentByClass<UFPSFireMagicComponent>())C->FinishFireMagicForRemoval();
        if(auto* C=A->FindComponentByClass<UFPSElectricMagicComponent>())C->FinishDomainForRemoval();
        A->ForceNetUpdate();
    }
    static void Publish(AUnknownJoinAuditController& C)
    {
        C.Loadouts.Reset();C.Motions.Reset();
        for(const auto& A:C.Subjects){C.Loadouts.Add(A->Loadout);C.Motions.Add(A->Motion);}
    }
    static AFPSIceWall* ExistingWall(AUnknownHumanoid* Caster)
    {
        auto* W=Caster->GetWorld()->SpawnActor<AFPSIceWall>();W->SetActorTickEnabled(false);W->bAlwaysRelevant=true;
        W->NetTuning=Caster->EquipmentModel()->IceWallStats(2);W->NetTuning.Duration=600;
        W->NetPlan.bValid=true;W->NetPlan.bHostileCaster=true;W->NetPlan.Location=FVector(40000,0,200);
        FIceWallSection S;S.MinAlong=-150;S.MaxAlong=150;S.Top=200;W->NetPlan.Sections.Add(S);
        W->NetComponent=Caster->FindComponentByClass<UFPSIceWallComponent>();
        W->NetState=uint8(AFPSIceWall::EState::Solid);W->NetStateAge=0;W->NetStateAt=UnknownJoin::Clock(Caster->GetWorld());
        W->NetHealth=50;W->SetActorLocation(W->NetPlan.Location);return W;
    }
    static bool Observe(AUnknownJoinAuditController& C,FString& Detail)
    {
        if(C.Phase<2)
        {
            Detail=FString::Printf(TEXT("wall=%d initialized=%d age=%.2f stamp=%.2f"),IsValid(C.Wall),C.Wall&&C.Wall->bNetInit,C.Wall?C.Wall->Age:-1,C.Wall?C.Wall->NetStateAt:-1);
            if(!C.Wall||!C.Wall->bNetInit||C.Wall->Age<8.f||
                FMath::Abs(C.Wall->Age-C.Wall->NetworkAge())>1.f)return false;
        }
        else if(IsValid(C.Wall))return false;
        if(C.Subjects.Num()!=4||C.Loadouts.Num()!=4||C.Motions.Num()!=4)return false;
        for(int32 I=0;I<4;++I)
        {
            auto* A=C.Subjects[I].Get();if(!A)return false;
            Detail=FString::Printf(TEXT("actor=%d body=%s ready=%d mesh=%s anim=%s"),I,*A->Loadout.Body.ToString(),A->bVisualReady,
                *GetNameSafe(A->GetMesh()->GetSkeletalMeshAsset()),*GetNameSafe(A->GetMesh()->GetAnimInstance()));
            if(!FUnknownLoadout::StaticStruct()->CompareScriptStruct(&A->Loadout,&C.Loadouts[I],0)||
                !FUnknownMotion::StaticStruct()->CompareScriptStruct(&A->Motion,&C.Motions[I],0))return false;
            if(A->Loadout.Role==EUnknownRole::Bow&&A->bBowBlades!=(C.Phase<2))return false;
            if(!A->bVisualReady||!A->GetMesh()->GetSkeletalMeshAsset()||!A->GetMesh()->GetAnimInstance())return false;
            if(A->Loadout.Role==EUnknownRole::Gun&&(!A->HeldGun||!A->HeldGun->GetSkinnedAsset()))return false;
            if(A->Loadout.Role==EUnknownRole::Melee&&!A->HeldWeapon->GetStaticMesh())return false;
            if(A->Loadout.Role==EUnknownRole::Bow)
            {
                if(!A->BackupLeft||!A->BackupRight||!A->BackupLeft->GetStaticMesh()||!A->BackupRight->GetStaticMesh())return false;
                if(A->BackupLeft->IsVisible()!=A->bBowBlades||A->BackupRight->IsVisible()!=A->bBowBlades||A->HeldWeapon->IsVisible()==A->bBowBlades)return false;
            }
            if(A->Loadout.Role==EUnknownRole::Magic)
            {
                bool Book=false;
                TArray<UStaticMeshComponent*> Meshes;A->GetComponents(Meshes);
                for(auto* Mesh:Meshes)Book|=Mesh->GetFName()==TEXT("HeldSpellbook")&&Mesh->GetStaticMesh()!=nullptr;
                if(!Book)return false;
            }
        }
        auto* A=C.Subjects[2].Get();
        auto* Ice=A->FindComponentByClass<UFPSIceArmorComponent>();auto* Haste=A->FindComponentByClass<UFPSLightningHasteComponent>();
        auto* Fire=A->FindComponentByClass<UFPSFireMagicComponent>();auto* Electric=A->FindComponentByClass<UFPSElectricMagicComponent>();
        if(!Ice||!Haste||!Fire||!Electric)return false;
        const float Expected=FMath::Max(0.,C.EndsAt-UnknownJoin::Clock(C.GetWorld()));
        const bool Active=C.Phase<2;
        const bool Buffs=Active?FMath::Abs(Ice->Remaining()-Expected)<2&&FMath::Abs(Haste->Remaining()-Expected)<2&&
            FMath::Abs(Fire->ArmorRemaining()-Expected)<2&&FMath::Abs(Electric->DomainRemaining()-Expected)<2&&Fire->IsDragonBreathActive():
            Ice->Remaining()<=0&&Haste->Remaining()<=0&&Fire->ArmorRemaining()<=0&&Electric->DomainRemaining()<=0&&!Fire->IsDragonBreathActive();
        Detail=FString::Printf(TEXT("phase=%d buffs=%d ice=%.2f haste=%.2f fire=%.2f domain=%.2f breath=%d remaining=%.2f"),
            C.Phase,Buffs,Ice->Remaining(),Haste->Remaining(),Fire->ArmorRemaining(),Electric->DomainRemaining(),Fire->IsDragonBreathActive(),Expected);
        return Buffs;
    }
    static bool Damage(AUnknownHumanoid& A,AFPSGAMECharacter& P,UColdSteelStatusModel& Model,float& Expected,FString& Detail)
    {
        const auto Role=A.Loadout.Role;auto* HP=P.FindComponentByClass<UFPSCombatHealthComponent>();
        const float Raw=Role==EUnknownRole::Magic?FMath::FloorToFloat(A.Spell.Damage*(1+A.Spell.MagicDamageBonus)):float(A.WeaponDamage.Total());
        const float Magic=Role==EUnknownRole::Magic?Raw:Raw*A.WeaponMagicFraction();
        const float Pen=Role==EUnknownRole::Magic?A.Spell.MagicPenetration:A.MagicPenetration;
        const float Damage=CoreCombatFormula::Defense(Raw-Magic,Model.Derived(TEXT("def")),false,A.PhysicalPenetration)+
            CoreCombatFormula::Defense(Magic,Model.Derived(TEXT("mdef")),true,Pen);
        HP->Health=HP->MaxHealth*.75f;const float Before=HP->Health;Expected=FMath::Max(0.f,Before-Damage);
        FHitResult Hit(&P,P.GetCapsuleComponent(),P.GetActorLocation(),FVector::BackwardVector);Hit.BoneName=TEXT("spine_02");
        float Applied=0;
        if(Role==EUnknownRole::Melee)Applied=UGameplayStatics::ApplyPointDamage(&P,Raw,FVector::ForwardVector,Hit,nullptr,&A,UEnemyMeleeDamage::StaticClass());
        if(Role==EUnknownRole::Gun)Applied=A.HitWithRound(Hit,Raw,FVector::ForwardVector,101.f);
        if(Role==EUnknownRole::Bow)
        {
            FColdSteelSkillShot Shot;Shot.DamagePanel=A.WeaponDamage;Shot.ArmorPenetration=A.PhysicalPenetration;Shot.MagicPenetration=A.MagicPenetration;
            // Exercise the projectile's captured panel after the archer swaps weapons.
            A.bBowBlades=true;A.Sheet=A.BladeSheet;A.CacheStats();
            Applied=A.HitWithArrow(Hit,Raw,FVector::ForwardVector,Shot);
        }
        if(Role==EUnknownRole::Magic)
        {
            const bool Accepted=UnknownSpell::Hit(&A,&P,Raw,0,0,0,Pen,ULightningDamage::StaticClass());
            Applied=Accepted?Before-HP->Health:0;
        }
        Detail=FString::Printf(TEXT("role=%d level=%d raw=%.2f def=%.1f mdef=%.1f expected=%.2f actual=%.2f receipt=%.2f"),
            int32(Role),A.Loadout.Level,Raw,Model.Derived(TEXT("def")),Model.Derived(TEXT("mdef")),Damage,Before-HP->Health,Applied);
        return Damage>0&&FMath::IsNearlyEqual(HP->Health,Expected,.02f)&&FMath::IsNearlyEqual(Applied,FMath::Min(Before,Damage),.02f);
    }
    static bool Unbound(AColdSteelPlayerState& PS,AFPSGAMECharacter& P,AUnknownHumanoid& Source,UColdSteelStatusModel& Host)
    {
        auto* HP=P.FindComponentByClass<UFPSCombatHealthComponent>();const float Before=HP->Health;
        TGuardValue<TObjectPtr<UColdSteelStatusModel>> Shadow(PS.ShadowModel,nullptr),PawnShadow(P.NetShadowProfile,nullptr);
        TGuardValue<double> Immunity(Host.MoonshadowUntil,1.e12);
        const float UnboundArmor=HP->DamageAfterArmor(20.f,GetDefault<UEnemyRangedDamage>(),&Source);
        const float Applied=UGameplayStatics::ApplyDamage(&P,20.f,nullptr,&Source,UEnemyRangedDamage::StaticClass());
        return FMath::IsNearlyEqual(UnboundArmor,20.f)&&Applied==0.f&&Before==HP->Health;
    }
};

void AUnknownJoinAuditController::BeginPlay()
{
    Super::BeginPlay();if(!UnknownJoin::Enabled()||!IsLocalController())return;
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->IsAudit())return;
    auto P=M->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
    P.Level=30;P.Points=0;P.Attributes.Reset();
    for(FName K:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")})P.Attributes.Add(K,10);
    P.Attributes[TEXT("con")]=HasAuthority()?80:40;P.Health=300;P.Mana=300;P.Stamina=150;
    auto Weapon=M->CreateItem(TEXT("ue_rune_sword"));Weapon.InstanceId=TEXT("unknown_join_guest_sword");Weapon.Place=1;Weapon.Cell=6;P.Items.Add(Weapon);
    auto Armor=M->CreateItem(TEXT("ue_chainmail_shirt"));Armor.InstanceId=TEXT("unknown_join_guest_armor");Armor.Place=1;Armor.Cell=7;P.Items.Add(Armor);
    FString Id;if(!HasAuthority()&&FParse::Value(FCommandLine::Get(),TEXT("UnknownJoinIdentity="),Id))FGuid::Parse(Id,P.NetworkProfileId);
    M->AdoptNetMirror(P);Seeded=true;
}
void AUnknownJoinAuditController::Tick(float Delta)
{
    Super::Tick(Delta);if(!UnknownJoin::Enabled()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!P||!M||!Seeded)return;
    if(!Attached){M->AttachPawn(P);P->ApplyColdSteelProfile(M);Attached=true;}
    UnknownJoin::Freeze(P);
    if(HasAuthority()||Probe<0||Probe==Reported)return;
    if(Watching!=Probe){Watching=Probe;Started=Now;}
    auto* HP=P->FindComponentByClass<UFPSCombatHealthComponent>();FString Detail;
    bool OK=FUnknownJoinAuditAccess::Observe(*this,Detail)&&HP&&FMath::IsNearlyEqual(HP->Health,ExpectedHP,.03f);
    const auto* Other=Wounded?Wounded->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    OK&=Other&&FMath::IsNearlyEqual(Other->Health,17.f,.01f);
    if(Probe==16&&HP)
    {
        const float Before=HP->Health;
        OK&=UGameplayStatics::ApplyDamage(P,70.f,nullptr,Subjects[2],ULightningDamage::StaticClass())==0.f&&HP->Health==Before;
    }
    if(OK||Now-Started>100.)
    {
        Detail+=FString::Printf(TEXT(" hp=%.2f expected_hp=%.2f initial_other_hp=%.2f"),HP?HP->Health:-1,ExpectedHP,Other?Other->Health:-1);
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("probe"),Probe);Row->SetBoolField(TEXT("passed"),OK);Row->SetStringField(TEXT("detail"),Detail);
        UnknownJoin::ClientRows.Add(MakeShared<FJsonValueObject>(Row));UnknownJoin::ClientPassed&=OK;
        Reported=Probe;ServerObserved(Probe,OK,Detail);
    }
}
void AUnknownJoinAuditController::ServerObserved_Implementation(int32 Index,bool OK,const FString& Detail)
{
    if(!UnknownJoin::Enabled()||Index!=Probe||Index<=Finished)return;
    Finished=Index;Passed&=OK;
    if(auto* G=GetWorld()->GetAuthGameMode<AUnknownJoinAuditGameMode>())G->Observe(Index,OK,Detail);
}
void AUnknownJoinAuditController::ClientExit_Implementation()
{
    if(!UnknownJoin::Enabled())return;
    FString Peer;FParse::Value(FCommandLine::Get(),TEXT("UnknownJoinPeer="),Peer);
    UnknownJoin::Write(UnknownJoin::ClientRows,UnknownJoin::ClientPassed,Peer,GetWorld());ExitAt=GetWorld()->GetRealTimeSeconds()+1.;
}
void AUnknownJoinAuditController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AUnknownJoinAuditController,Subjects);DOREPLIFETIME(AUnknownJoinAuditController,Loadouts);
    DOREPLIFETIME(AUnknownJoinAuditController,Motions);DOREPLIFETIME(AUnknownJoinAuditController,Wounded);
    DOREPLIFETIME(AUnknownJoinAuditController,ExpectedHP);DOREPLIFETIME(AUnknownJoinAuditController,EndsAt);
    DOREPLIFETIME(AUnknownJoinAuditController,Phase);DOREPLIFETIME(AUnknownJoinAuditController,Probe);
    DOREPLIFETIME(AUnknownJoinAuditController,Wall);
}
AUnknownJoinAuditGameMode::AUnknownJoinAuditGameMode()
{
    PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AUnknownJoinAuditController::StaticClass();
    PlayerStateClass=AColdSteelPlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();HUDClass=nullptr;
}
void AUnknownJoinAuditGameMode::StartPlay()
{
    Super::StartPlay();if(!UnknownJoin::Enabled())return;Started=GetWorld()->GetRealTimeSeconds();
    for(int32 I=0;I<4;++I)
    {
        auto* A=FUnknownJoinAuditAccess::Spawn(GetWorld(),EUnknownRole(I),10+10*(I%3),I);
        if(!A){Passed=false;Save();ExitAt=Started+1.;return;}
        Subjects.Add(A);Passed&=FUnknownJoinAuditAccess::Start(A);
    }
    EndsAt=UnknownJoin::Clock(GetWorld())+600.;
    Wall=FUnknownJoinAuditAccess::ExistingWall(Subjects[2]);
    Wounded=GetWorld()->SpawnActor<AFPSGAMECharacter>(FVector(6000,0,200),FRotator::ZeroRotator);Wounded->bAlwaysRelevant=true;
    UnknownJoin::Freeze(Wounded);Wounded->FindComponentByClass<UFPSCombatHealthComponent>()->Health=17;
    UE_LOG(LogTemp,Display,TEXT("UNKNOWN_JOIN_HOST_READY passed=%d"),Passed);
}
void AUnknownJoinAuditGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);if(!UnknownJoin::Enabled()||Player->IsLocalController())return;
    Guest=Cast<AUnknownJoinAuditController>(Player);Prepared=-1;Leaving=false;
}
void AUnknownJoinAuditGameMode::Logout(AController* Player)
{
    const bool Ours=Player==Guest;Super::Logout(Player);
    if(!UnknownJoin::Enabled()||!Ours)return;Guest=nullptr;++Phase;
    UE_LOG(LogTemp,Display,TEXT("UNKNOWN_JOIN_DISCONNECTED phase=%d"),Phase);
    if(Phase>=3){Save();ExitAt=GetWorld()->GetRealTimeSeconds()+1.;}
}
void AUnknownJoinAuditGameMode::Observe(int32 Index,bool OK,const FString& Detail)
{
    Passed&=OK;auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Phase);Row->SetNumberField(TEXT("probe"),Index);
    Row->SetBoolField(TEXT("passed"),OK);Row->SetStringField(TEXT("detail"),Detail);Rows.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp,Display,TEXT("UNKNOWN_JOIN_PROBE phase=%d probe=%d passed=%d %s"),Phase,Index,OK,*Detail);
    if(!OK){Save();if(Guest)Guest->ClientExit();ExitAt=GetWorld()->GetRealTimeSeconds()+3.;}
}
void AUnknownJoinAuditGameMode::Save()
{
    UnknownJoin::Write(Rows,Passed,TEXT("host"),GetWorld());UE_LOG(LogTemp,Display,TEXT("UNKNOWN_JOIN_RESULT passed=%d cases=%d"),Passed,Rows.Num());
}
void AUnknownJoinAuditGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!UnknownJoin::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Now-Started>900.){Passed=false;Save();ExitAt=Now+1.;return;}
    if(!Guest||Leaving)return;
    auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    auto* M=PS?PS->GetShadowModel():nullptr;if(!P||!M||M->RuntimePawn()!=P)return;
    UnknownJoin::Freeze(P);PS->SetActorTickEnabled(false);
    if(Prepared>=0&&Guest->Finished<Prepared)return;
    const int32 Next=Prepared+1;
    if((Phase==0&&Next>16)||(Phase==1&&Next>0)||(Phase==2&&Next>1))
    {
        SavedHP=P->FindComponentByClass<UFPSCombatHealthComponent>()->Health;PreviousModel=M;PreviousPawn=P;
        if(Phase==1){for(const auto& A:Subjects)FUnknownJoinAuditAccess::End(A);Wall->Destroy();Wall=nullptr;}
        Leaving=true;Guest->ClientExit();return;
    }
    bool OK=true;FString Detail;auto* HP=P->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Phase==2&&Next==1)
    {
        HP->Health=1.f;
        const float Applied=UGameplayStatics::ApplyDamage(P,100.f,nullptr,Subjects[2],ULightningDamage::StaticClass());
        OK=HP->IsDead()&&FMath::IsNearlyEqual(Applied,1.f,.01f);
        Observe(201,OK,TEXT("lethal magic returns accepted remaining health and replicates death"));
    }
    if(Next==0&&Phase>0)
    {
        OK=M==PreviousModel&&!PreviousPawn.IsValid()&&FMath::IsNearlyEqual(HP->Health,SavedHP,.05f)&&
            M->Equipped()&&M->Equipped()->InstanceId==TEXT("unknown_join_guest_sword");
        Detail=FString::Printf(TEXT("cached_model=%d old_pawn_gone=%d saved_hp=%.2f restored_hp=%.2f"),M==PreviousModel,!PreviousPawn.IsValid(),SavedHP,HP->Health);
        Observe(-1,OK,Detail);
    }
    if(Next>=1&&Next<=12&&Phase==0)
    {
        auto* A=FUnknownJoinAuditAccess::Spawn(GetWorld(),EUnknownRole((Next-1)/3),10+((Next-1)%3)*10,10);
        float Expected=0;
        OK=A&&FUnknownJoinAuditAccess::Damage(*A,*P,*M,Expected,Detail);if(A)A->Destroy();Observe(Next+100,OK,Detail);
    }
    if(Next==13)
    {
        TGuardValue<double> Immunity(M->MoonshadowUntil,1.e12);const float Before=HP->Health;
        OK=!UnknownSpell::Hit(Subjects[2],P,50,0,0,0,0,ULightningDamage::StaticClass())&&Before==HP->Health;
        auto* Status=UCombatStatusFormula::GetOrAdd(P);const int32 Chill=Status->ChillCount();
        auto* Caster=Subjects[2]->EquipmentModel();auto Spike=Caster->IceSpikeStats(2);Spike.ChillSlow=.3f;
        FIceSpikeRewards Rewards;FHitResult Hit(P,P->GetCapsuleComponent(),P->GetActorLocation(),FVector::BackwardVector);
        Caster->ApplyIceSpikeHit(Subjects[2],Hit,Spike,Rewards);
        OK&=Before==HP->Health&&Rewards.Hits==0&&Status->ChillCount()==Chill;
        Observe(113,OK,TEXT("immune spell rejects contact; ice spike applies no chill or hit reward"));
    }
    if(Next==14)
    {
        OK=FUnknownJoinAuditAccess::Unbound(*PS,*P,*Subjects[1],*GetGameInstance()->GetSubsystem<UColdSteelStatusModel>());
        Observe(114,OK,TEXT("unbound guest waits for its own profile; no host armor/protection fallback"));
    }
    if(Next==15)
    {
        const float Before=HP->Health;
        auto* Status=UCombatStatusFormula::GetOrAdd(P);Status->SetComponentTickEnabled(false);
        Status->AddBurn(Subjects[2],20.f,1,20.f,1.f,1.f);Status->AddBurn(Subjects[2],20.f,1,20.f,1.f,1.f);
        const float TickDamage=CoreCombatFormula::Defense(20.f,M->Derived(TEXT("mdef")),true,Subjects[2]->Penetration(true));
        for(int32 I=0;I<3;++I)Status->TickComponent(1.01f,LEVELTICK_All,nullptr);
        OK=FMath::IsNearlyEqual(Before-HP->Health,TickDamage*3,.01f);
        Status->PurgeTransient();Status->SetComponentTickEnabled(true);
        Observe(115,OK,FString::Printf(TEXT("same-caster burn refresh; three authority ticks expected=%.2f actual=%.2f"),TickDamage*3,Before-HP->Health));
    }
    Passed&=OK;Prepared=Next;Guest->Subjects=Subjects;Guest->Wounded=Wounded;Guest->Wall=Wall;Guest->Phase=Phase;
    Guest->EndsAt=EndsAt;Guest->ExpectedHP=HP->Health;FUnknownJoinAuditAccess::Publish(*Guest);Guest->Probe=Next;
    P->ForceNetUpdate();Guest->ForceNetUpdate();
}
