#include "UnknownNetworkAudit.h"
#include "../Monsters/UnknownHumanoidBow.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSHolyLightEffect.h"
#include "NiagaraSystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace UnknownWire
{
constexpr int32 Steps=6,Count=Steps*4*3+2;
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(),TEXT("UnknownNetworkAudit"));
#endif
}
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Passed,const TCHAR* Role)
{
    FString Root;FParse::Value(FCommandLine::Get(),TEXT("UnknownNetworkOutput="),Root);
    if(Root.IsEmpty())Root=FPaths::ProjectSavedDir()/TEXT("UnknownNetworkAudit");
    IFileManager::Get().MakeDirectory(*Root,true);
    auto Data=MakeShared<FJsonObject>();Data->SetBoolField(TEXT("passed"),Passed);
    Data->SetStringField(TEXT("scope"),TEXT("Real UDP replication; direct authority stimuli; 4 roles x 3 levels. No rendering, listening, navigation or player weapon input acceptance."));
    Data->SetArrayField(TEXT("cases"),Rows);
    FString Json;FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(Root/(FString(Role)+TEXT(".json"))));
    UE_LOG(LogTemp,Display,TEXT("UNKNOWN_WIRE_RESULT role=%s passed=%d cases=%d"),Role,Passed,Rows.Num());
}
}

struct FUnknownNetworkAuditAccess
{
    static void AgedLight(AUnknownNetworkAuditController& PC)
    {
        PC.Light=PC.GetWorld()->SpawnActor<AFPSHolyLightEffect>();
        FHolyLightCast Spell;Spell.Duration=60.f;
        PC.Light->InitializeLight(PC.Subject,LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/HolyLight/NS_HolyLightMotes.NS_HolyLightMotes")),Spell);
        PC.Light->NetStartedAt-=10.;PC.Light->bAlwaysRelevant=true;PC.Light->ForceNetUpdate();
    }
    static AUnknownHumanoid* Spawn(UWorld* World,EUnknownRole Role,int32 Level)
    {
        const FTransform At(FRotator::ZeroRotator,FVector(0,0,200));
        auto* A=World->SpawnActorDeferred<AUnknownHumanoid>(AUnknownHumanoid::StaticClass(),At,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!A||!A->Configure(Role,Level)){if(A)A->Destroy();return nullptr;}
        A->AutoPossessAI=EAutoPossessAI::Disabled;A->bAlwaysRelevant=true;
        UGameplayStatics::FinishSpawningActor(A,At);
        A->SetActorTickEnabled(false);A->GetCharacterMovement()->DisableMovement();
        A->HealthRegen=0;A->SetAction(EUnknownAction::Ready);
        return A;
    }
    static bool Prepare(AUnknownHumanoid& A,AUnknownNetworkAuditController& PC,int32 Step)
    {
        auto* Target=PC.GetPawn().Get();if(!Target)return false;
        const auto Role=A.Loadout.Role;
        if(Step==1)
        {
            A.SetAction(Role==EUnknownRole::Melee?EUnknownAction::Swing:Role==EUnknownRole::Gun?EUnknownAction::Fire:
                Role==EUnknownRole::Bow?EUnknownAction::DrawBow:EUnknownAction::Cast,60.f);
            A.Motion.Windup=20.f;A.Motion.Preparation=.3f;A.Motion.Recovery=.2f;
            if(Role==EUnknownRole::Gun){A.bGunTracking=true;A.GunAimPoint=FVector(750,300,500);}
            if(Role==EUnknownRole::Magic)
            {
                A.Motion.Skill=TEXT("iceArmor");
                auto* Armor=A.FindComponentByClass<UFPSIceArmorComponent>();if(!Armor)return false;
                auto Spell=A.Sheet->IceArmorStats(3);Spell.Duration=120.f;Spell.PulseSeconds=120.f;
                FColdSteelNetCastRequest Req;Req.SkillId=TEXT("iceArmor");Req.CastId=111;Req.SourcePawn=&A;
                if(!Armor->NetRelease(&A,Req,A.Sheet,Spell))return false;
            }
        }
        if(Step==2)
        {
            Target->SetActorLocation(FVector(200,0,200));
            const int32 ChillBefore=UCombatStatusFormula::GetOrAdd(Target)->ChillCount();
            CombatFormulaRuntime::WeaponHit Hit;Hit.Target=&A;Hit.Incoming.BasePhysical=100;Hit.bMelee=true;
            TGuardValue<CombatFormulaRuntime::WeaponHit*> Scope(CombatFormulaRuntime::ActiveWeaponHit,&Hit);
            FDamageEvent Event;Event.DamageTypeClass=UDamageType::StaticClass();
            const float Before=A.Health,Applied=A.TakeDamage(100,Event,&PC,Target);
            if(Applied<=0||!FMath::IsNearlyEqual(Before-A.Health,Applied,.01f))return false;
            if(Role==EUnknownRole::Magic)
            {
                const auto* Armor=A.FindComponentByClass<UFPSIceArmorComponent>();
                if(!Armor||!Armor->Impact.Serial||Armor->Experience!=Armor->State.Cast.CastExperience||
                    UCombatStatusFormula::GetOrAdd(Target)->ChillCount()!=ChillBefore+1)return false;
            }
            A.SetAction(EUnknownAction::Ready);
        }
        if(Step==3)
        {
            if(Role==EUnknownRole::Gun){A.Magazine=0;A.SetAction(EUnknownAction::Reload,60.f);}
            else if(Role==EUnknownRole::Bow)
            {
                const float HP=A.Health,SP=A.Stamina;
                A.UpdateBowTactics(Target,true);
                if(!A.bBowBlades||A.Health>HP||A.Stamina>SP)return false;
            }
            else A.SetAction(EUnknownAction::Stagger,60.f);
        }
        if(Step==4)
        {
            if(Role==EUnknownRole::Gun)
            {
                A.Motion.Started=A.ServerTime()-61.f;A.Tick(.001f);
                if(A.Magazine!=A.Capacity||A.Magazine<=0||A.Motion.Action!=EUnknownAction::Ready)return false;
            }
            else if(Role==EUnknownRole::Bow)
            {
                const float HP=A.Health,SP=A.Stamina;
                Target->SetActorLocation(FVector(1500,0,200));A.SetAction(EUnknownAction::Ready);
                A.Archery->SafeSince=A.ServerTime()-1.;A.Archery->SwitchAfter=A.ServerTime()-1.;
                A.UpdateBowTactics(Target,true);
                if(A.bBowBlades||A.Health>HP||A.Stamina>SP)return false;
            }
            else
            {
                A.SetAction(EUnknownAction::Ready);
                if(auto* Armor=A.FindComponentByClass<UFPSIceArmorComponent>())Armor->FinishForRemoval();
            }
        }
        if(Step==5)
        {FDamageEvent Event;A.TakeDamage(100000000.f,Event,&PC,Target);if(!A.Dead())return false;}
        A.ForceNetUpdate();return true;
    }
    static void Expect(AUnknownHumanoid& A,AUnknownNetworkAuditController& PC)
    {
        PC.Subject=&A;PC.ExpectedLoadout=A.Loadout;PC.ExpectedMotion=A.Motion;
        PC.ExpectedHealth=A.Health;PC.ExpectedBlades=A.bBowBlades;PC.ExpectedArmor=false;PC.ExpectedImpact=0;
        if(const auto* Armor=A.FindComponentByClass<UFPSIceArmorComponent>())
        {PC.ExpectedArmor=Armor->Remaining()>0;PC.ExpectedImpact=Armor->Impact.Serial;}
    }
    static bool Observe(AUnknownHumanoid& A,const AUnknownNetworkAuditController& PC,FString& Detail)
    {
        const auto& L=A.Loadout;const auto& E=PC.ExpectedLoadout;const auto& M=A.Motion;const auto& N=PC.ExpectedMotion;
        bool OK=!A.HasAuthority()&&!A.EquipmentModel()&&L.Role==E.Role&&L.Level==E.Level&&L.Body==E.Body&&
            L.Weapon==E.Weapon&&L.Offhand==E.Offhand&&L.BackupBlade==E.BackupBlade&&L.Outfit.Num()==E.Outfit.Num();
        if(OK)for(int32 I=0;I<L.Outfit.Num();++I)OK&=L.Outfit[I].Slot==E.Outfit[I].Slot&&L.Outfit[I].Definition==E.Outfit[I].Definition;
        OK&=M.Serial==N.Serial&&M.Action==N.Action&&M.Skill==N.Skill&&M.Windup==N.Windup&&M.Duration==N.Duration&&
            FMath::IsNearlyEqual(A.Health,PC.ExpectedHealth,.01f)&&A.bBowBlades==PC.ExpectedBlades;
        if(L.Role==EUnknownRole::Gun&&PC.Case%UnknownWire::Steps>=1)
            OK&=A.bGunTracking&&FVector::Dist(A.GunAimPoint,FVector(750,300,500))<1.f;
        if(L.Role==EUnknownRole::Magic)
        {
            TInlineComponentArray<UActorComponent*> Components;A.GetComponents(Components);
            for(const TCHAR* Name:{TEXT("FPSIceSpikeComponent"),TEXT("FPSIceWallComponent"),TEXT("FPSBlizzardComponent"),
                TEXT("FPSLightningComponent"),TEXT("FPSHolyLightComponent"),TEXT("FPSIceArmorComponent"),
                TEXT("FPSLightningHasteComponent"),TEXT("FPSFireMagicComponent"),TEXT("FPSElectricMagicComponent")})
                OK&=Components.ContainsByPredicate([Name](const UActorComponent* C){return C->GetClass()->GetFName()==FName(Name);});
            const auto* Armor=A.FindComponentByClass<UFPSIceArmorComponent>();
            OK&=Armor&&(Armor->Remaining()>0)==PC.ExpectedArmor&&Armor->Impact.Serial==PC.ExpectedImpact;
        }
        if(A.Dead())OK&=A.GetCapsuleComponent()->GetCollisionEnabled()==ECollisionEnabled::NoCollision;
        if(PC.Case==UnknownWire::Count-1)OK&=PC.Light&&PC.Light->bNetInit&&PC.Light->Age>=8.f;
        Detail=FString::Printf(TEXT("role=%d level=%d weapon=%s action=%d serial=%u/%u hp=%.2f/%.2f blades=%d armor=%d"),
            int32(L.Role),L.Level,*L.Weapon,int32(M.Action),M.Serial,N.Serial,A.Health,PC.ExpectedHealth,A.bBowBlades,PC.ExpectedArmor);
        return OK;
    }
};

void AUnknownNetworkAuditController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AUnknownNetworkAuditController,Subject);DOREPLIFETIME(AUnknownNetworkAuditController,ExpectedLoadout);
    DOREPLIFETIME(AUnknownNetworkAuditController,Light);
    DOREPLIFETIME(AUnknownNetworkAuditController,ExpectedMotion);DOREPLIFETIME(AUnknownNetworkAuditController,ExpectedHealth);
    DOREPLIFETIME(AUnknownNetworkAuditController,ExpectedBlades);DOREPLIFETIME(AUnknownNetworkAuditController,ExpectedArmor);
    DOREPLIFETIME(AUnknownNetworkAuditController,ExpectedImpact);DOREPLIFETIME(AUnknownNetworkAuditController,Case);
}
void AUnknownNetworkAuditController::Tick(float Delta)
{
    Super::Tick(Delta);if(!UnknownWire::Enabled()||!IsLocalController()||HasAuthority())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Case<0||Reported==Case)return;
    if(Watching!=Case){Watching=Case;Started=Now;}
    FString Detail;const bool Passed=IsValid(Subject)&&Subject->HasActorBegunPlay()&&FUnknownNetworkAuditAccess::Observe(*Subject,*this,Detail);
    if(!Passed&&Now-Started<20.)return;
    Reported=Case;AllPassed&=Passed;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("case"),Case);Row->SetBoolField(TEXT("passed"),Passed);Row->SetStringField(TEXT("detail"),Detail);
    Results.Add(MakeShared<FJsonValueObject>(Row));ServerObserved(Case,Passed,Detail);
}
void AUnknownNetworkAuditController::ServerObserved_Implementation(int32 Index,bool Passed,const FString& Detail)
{
    if(!UnknownWire::Enabled()||Index!=Case||Finished>=Index)return;
    Finished=Index;AllPassed&=Passed;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("case"),Index);Row->SetBoolField(TEXT("passed"),Passed);Row->SetStringField(TEXT("detail"),Detail);
    Results.Add(MakeShared<FJsonValueObject>(Row));
    UE_LOG(LogTemp,Display,TEXT("UNKNOWN_WIRE_CASE %d passed=%d %s"),Index,Passed,*Detail);
}
void AUnknownNetworkAuditController::ClientFinish_Implementation(bool Passed)
{if(UnknownWire::Enabled()){UnknownWire::Save(Results,Passed&&AllPassed,TEXT("client"));ExitAt=GetWorld()->GetRealTimeSeconds()+1.;}}
AUnknownNetworkAuditGameMode::AUnknownNetworkAuditGameMode()
{PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AUnknownNetworkAuditController::StaticClass();DefaultPawnClass=ACharacter::StaticClass();HUDClass=nullptr;}
void AUnknownNetworkAuditGameMode::StartPlay()
{Super::StartPlay();Started=GetWorld()->GetRealTimeSeconds();if(UnknownWire::Enabled())UE_LOG(LogTemp,Display,TEXT("UNKNOWN_WIRE_HOST_READY"));}
void AUnknownNetworkAuditGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);
    if(UnknownWire::Enabled()&&!Player->IsLocalController())Guest=Cast<AUnknownNetworkAuditController>(Player);
}
void AUnknownNetworkAuditGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!UnknownWire::Enabled())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest){if(Now-Started>180.)FPlatformMisc::RequestExit(false);return;}
    if(auto* Pawn=Cast<ACharacter>(Guest->GetPawn()))
    {
        Pawn->GetCharacterMovement()->DisableMovement();
        if(!Pawn->FindComponentByClass<UFPSCombatHealthComponent>())
        {
            auto* HP=NewObject<UFPSCombatHealthComponent>(Pawn);
            Pawn->AddInstanceComponent(HP);HP->SetIsReplicated(true);HP->RegisterComponent();
        }
    }
    if(!Passed||Guest->Finished>=UnknownWire::Count-1||Now-Started>600.)
    {
        Passed&=Guest->AllPassed&&Guest->Finished==UnknownWire::Count-1;
        Guest->ClientFinish(Passed);UnknownWire::Save(Guest->Results,Passed,TEXT("host"));ExitAt=Now+3.;return;
    }
    const int32 Next=Guest->Finished+1,Step=Next%UnknownWire::Steps;
    if(Prepared==Next)return;Prepared=Next;
    if(Next==UnknownWire::Count-1)
    {FUnknownNetworkAuditAccess::AgedLight(*Guest);Guest->Case=Next;Guest->ForceNetUpdate();return;}
    if(Step==0)
    {
        if(IsValid(Subject))Subject->Destroy();
        const bool Late=Next==UnknownWire::Count-2;
        const auto MonsterRole=Late?EUnknownRole::Magic:EUnknownRole((Next/UnknownWire::Steps)%4);
        Subject=FUnknownNetworkAuditAccess::Spawn(GetWorld(),MonsterRole,Late?30:10+10*(Next/(UnknownWire::Steps*4)));
        if(!Subject){Passed=false;return;}
        if(Late)Passed&=FUnknownNetworkAuditAccess::Prepare(*Subject,*Guest,5); // Initial actor channel already contains death.
    }
    else Passed&=FUnknownNetworkAuditAccess::Prepare(*Subject,*Guest,Step);
    if(!Passed)UE_LOG(LogTemp,Error,TEXT("UNKNOWN_WIRE_AUTHORITY_FAILED case=%d step=%d"),Next,Step);
    FUnknownNetworkAuditAccess::Expect(*Subject,*Guest);Guest->Case=Next;Guest->ForceNetUpdate();
}
