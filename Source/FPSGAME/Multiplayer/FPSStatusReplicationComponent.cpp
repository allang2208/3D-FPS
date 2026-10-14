#include "FPSStatusReplicationComponent.h"
#include "GameFramework/Controller.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/PoisonMaggotProjectile.h"
#include "../Monsters/HandBrainFearComponent.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"
UFPSStatusReplicationComponent::UFPSStatusReplicationComponent()
{SetIsReplicatedByDefault(true);PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickInterval=.1f;}
double UFPSStatusReplicationComponent::ServerTime() const
{const auto* GS=GetWorld()->GetGameState();return GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}
void UFPSStatusReplicationComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UFPSStatusReplicationComponent,State);}
void UFPSStatusReplicationComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!GetOwner()->HasAuthority()){ApplyState(false);return;}
    if(GetNetMode()==NM_Standalone)return;
    const double Now=ServerTime();
    const auto Quantize=[](double T){return FMath::RoundToDouble(T*20.)/20.;};
    FFPSStatusNetState Next;
    if(const auto* C=GetOwner()->FindComponentByClass<UCombatStatusFormula>())
    {
        Next.bHasCombat=true;Next.bImmune=C->bImmune;Next.ZhenmoMovement=C->ZhenmoMovementMultiplier();
        Next.ElectrifiedTime=C->ElectrifiedTime>0.f?Quantize(Now+C->ElectrifiedTime):0.;
        Next.ChillTime=C->ChillTime>0.f?Quantize(Now+C->ChillTime):0.;
        Next.FrozenTime=C->FrozenTime>0.f?Quantize(Now+C->FrozenTime):0.;
        Next.HasteTime=C->HasteTime>0.f?Quantize(Now+C->HasteTime):0.;
        Next.ChainTime=C->ChainTime>0.f?Quantize(Now+C->ChainTime):0.;
        Next.CorrosionTime=C->CorrosionTime>0.f?Quantize(Now+C->CorrosionTime):0.;
        Next.ShredTime=C->ShredTime>0.f?Quantize(Now+C->ShredTime):0.;
        Next.WardTime=C->WardTime>0.f?Quantize(Now+C->WardTime):0.;
        Next.VulnerabilityTime=C->VulnerabilityTime>0.f?Quantize(Now+C->VulnerabilityTime):0.;
        Next.BleedTime=C->BleedTime>0.f?Quantize(Now+C->BleedTime):0.;
        Next.RuneVulnerabilityTime=C->RuneVulnerabilityTime>0.f?Quantize(Now+C->RuneVulnerabilityTime):0.;
        Next.RiposteTime=C->RiposteTime>0.f?Quantize(Now+C->RiposteTime):0.;
        Next.StunTime=C->StunTime>0.f?Quantize(Now+C->StunTime):0.;
        Next.BindTime=C->BindTime>0.f?Quantize(Now+C->BindTime):0.;
        Next.SlowTime=C->SlowTime>0.f?Quantize(Now+C->SlowTime):0.;
        Next.WaxTime=C->WaxTime>0.f?Quantize(Now+C->WaxTime):0.;
        Next.WeaponHasteTime=C->WeaponHasteTime>0.f?Quantize(Now+C->WeaponHasteTime):0.;
        Next.PetrifyTime=C->PetrifyTime>0.f?Quantize(Now+C->PetrifyTime):0.;
        Next.MarkedTime=C->MarkedTime>0.f?Quantize(Now+C->MarkedTime):0.;
        Next.InspireTime=C->InspireTime>0.f?Quantize(Now+C->InspireTime):0.;
        Next.CamelTime=C->CamelTime>0.f?Quantize(Now+C->CamelTime):0.;
        Next.ImmuneTime=C->ImmuneTime>0.f?Quantize(Now+C->ImmuneTime):0.;
        Next.MineTime=C->MineTime>0.f?Quantize(Now+C->MineTime):0.;
        Next.TigerRoarEndsAt=C->TigerRoarEndsAt>0.?Quantize(C->TigerRoarEndsAt):0.;
        Next.PhysicalVulnerabilityEndsAt=C->PhysicalVulnerabilityEndsAt>0.?Quantize(C->PhysicalVulnerabilityEndsAt):0.;
        Next.BerserkDecayAt=C->BerserkDecayAt>0.?Quantize(C->BerserkDecayAt):0.;
        Next.WagerEndsAt=C->WagerEndsAt>0.?Quantize(C->WagerEndsAt):0.;
        Next.ComposureEndsAt=C->ComposureEndsAt>0.?Quantize(C->ComposureEndsAt):0.;
        Next.ElectrifiedBonus=C->ElectrifiedBonus;
        Next.ChillSlow=C->ChillSlow;
        Next.CorrosionDuration=C->CorrosionDuration;
        Next.CorrosionReduction=C->CorrosionReduction;
        Next.Shred=C->Shred;
        Next.Ward=C->Ward;
        Next.RuneVulnerability=C->RuneVulnerability;
        Next.TigerRoarBonus=C->TigerRoarBonus;
        Next.PhysicalVulnerabilityBonus=C->PhysicalVulnerabilityBonus;
        Next.RiposteSpeed=C->RiposteSpeed;
        Next.RiposteStamina=C->RiposteStamina;
        Next.SlowPct=C->SlowPct;
        Next.WaxPct=C->WaxPct;
        Next.WeaponHasteMul=C->WeaponHasteMul;
        Next.PetrifyMul=C->PetrifyMul;
        Next.MarkedValue=C->MarkedValue;
        Next.InspireSpeed=C->InspireSpeed;
        Next.InspireAtk=C->InspireAtk;
        Next.CamelReduction=C->CamelReduction;
        Next.BerserkPeriod=C->BerserkPeriod;
        Next.BerserkSpeedPerStack=C->BerserkSpeedPerStack;
        Next.WagerPeriod=C->WagerPeriod;
        Next.WagerBonusPerStack=C->WagerBonusPerStack;
        Next.ComposurePeriod=C->ComposurePeriod;
        Next.ComposureStabilityPerStack=C->ComposureStabilityPerStack;
        Next.ComposureRecoilReductionPerStack=C->ComposureRecoilReductionPerStack;
        Next.ElectrifiedStacks=C->ElectrifiedStacks;
        Next.ChillStacks=C->ChillStacks;
        Next.HasteStacks=C->HasteStacks;
        Next.ChainStacks=C->ChainStacks;
        Next.CorrosionStacks=C->CorrosionStacks;
        Next.VulnerabilityStacks=C->VulnerabilityStacks;
        Next.BleedStacks=C->BleedStacks;
        Next.BerserkStacks=C->BerserkStacks;
        Next.BerserkLimit=C->BerserkLimit;
        Next.WagerStacks=C->WagerStacks;
        Next.ComposureStacks=C->ComposureStacks;
    }
    if(const auto* I=GetOwner()->FindComponentByClass<UProgressiveInfectionComponent>())
    {Next.Infection=I->State;Next.InfectedAt=Next.Infection.bActive?Quantize(Now-Next.Infection.ElapsedSeconds):0.;Next.Infection.ElapsedSeconds=0.f;}
    if(const auto* P=GetOwner()->FindComponentByClass<UMaggotPoisonComponent>())
    {Next.PoisonStacks=P->Stacks;Next.PoisonDecayAt=P->Stacks>0?Quantize(Now+P->DecayLeft):0.;}
    if(const auto* F=GetOwner()->FindComponentByClass<UHandBrainFearComponent>())
    {Next.FearExpirations=F->Expirations;Next.FearThreat=F->Threat.Get();}
    if(const auto* Display=GetOwner()->FindComponentByClass<UStatusEffectsComponent>())
        for(const auto& R:Display->Records)
        {
            const auto& V=R.View;if(!V.Persistent&&V.Battles<0&&R.End<=Now)continue;
            auto& D=Next.Display.AddDefaulted_GetRef();D.Type=V.Type;D.End=Quantize(R.End);D.Duration=V.Duration;
            D.Stacks=V.Stacks;D.Battles=V.Battles;D.Persistent=V.Persistent;D.DurationText=V.DurationText;
            const auto Base=UStatusEffectsComponent::Definition(V.Type);
            if(V.Name!=Base.Name)D.Name=V.Name;if(V.Icon!=Base.Icon)D.Icon=V.Icon;if(V.Color!=Base.Color)D.Color=V.Color;
        }
    State=MoveTemp(Next);
}
void UFPSStatusReplicationComponent::OnRep_State(){ApplyState(true);}
void UFPSStatusReplicationComponent::ApplyState(bool bPublishDisplay)
{
    if(GetOwner()->HasAuthority())return;
    const double Now=ServerTime(),LocalNow=GetWorld()->GetTimeSeconds();
    if(State.bHasCombat)
    {
        auto* C=UCombatStatusFormula::GetOrAdd(GetOwner());C->bImmune=State.bImmune;C->NetworkZhenmoMovement=State.ZhenmoMovement;
        C->ElectrifiedTime=State.ElectrifiedTime>0.?FMath::Max(0.,State.ElectrifiedTime-Now):0.f;
        C->ChillTime=State.ChillTime>0.?FMath::Max(0.,State.ChillTime-Now):0.f;
        C->FrozenTime=State.FrozenTime>0.?FMath::Max(0.,State.FrozenTime-Now):0.f;
        C->HasteTime=State.HasteTime>0.?FMath::Max(0.,State.HasteTime-Now):0.f;
        C->ChainTime=State.ChainTime>0.?FMath::Max(0.,State.ChainTime-Now):0.f;
        C->CorrosionTime=State.CorrosionTime>0.?FMath::Max(0.,State.CorrosionTime-Now):0.f;
        C->ShredTime=State.ShredTime>0.?FMath::Max(0.,State.ShredTime-Now):0.f;
        C->WardTime=State.WardTime>0.?FMath::Max(0.,State.WardTime-Now):0.f;
        C->VulnerabilityTime=State.VulnerabilityTime>0.?FMath::Max(0.,State.VulnerabilityTime-Now):0.f;
        C->BleedTime=State.BleedTime>0.?FMath::Max(0.,State.BleedTime-Now):0.f;
        C->RuneVulnerabilityTime=State.RuneVulnerabilityTime>0.?FMath::Max(0.,State.RuneVulnerabilityTime-Now):0.f;
        C->RiposteTime=State.RiposteTime>0.?FMath::Max(0.,State.RiposteTime-Now):0.f;
        C->StunTime=State.StunTime>0.?FMath::Max(0.,State.StunTime-Now):0.f;
        C->BindTime=State.BindTime>0.?FMath::Max(0.,State.BindTime-Now):0.f;
        C->SlowTime=State.SlowTime>0.?FMath::Max(0.,State.SlowTime-Now):0.f;
        C->WaxTime=State.WaxTime>0.?FMath::Max(0.,State.WaxTime-Now):0.f;
        C->WeaponHasteTime=State.WeaponHasteTime>0.?FMath::Max(0.,State.WeaponHasteTime-Now):0.f;
        C->PetrifyTime=State.PetrifyTime>0.?FMath::Max(0.,State.PetrifyTime-Now):0.f;
        C->MarkedTime=State.MarkedTime>0.?FMath::Max(0.,State.MarkedTime-Now):0.f;
        C->InspireTime=State.InspireTime>0.?FMath::Max(0.,State.InspireTime-Now):0.f;
        C->CamelTime=State.CamelTime>0.?FMath::Max(0.,State.CamelTime-Now):0.f;
        C->ImmuneTime=State.ImmuneTime>0.?FMath::Max(0.,State.ImmuneTime-Now):0.f;
        C->MineTime=State.MineTime>0.?FMath::Max(0.,State.MineTime-Now):0.f;
        C->TigerRoarEndsAt=State.TigerRoarEndsAt>0.?LocalNow+State.TigerRoarEndsAt-Now:0.;
        C->PhysicalVulnerabilityEndsAt=State.PhysicalVulnerabilityEndsAt>0.?LocalNow+State.PhysicalVulnerabilityEndsAt-Now:0.;
        C->BerserkDecayAt=State.BerserkDecayAt>0.?LocalNow+State.BerserkDecayAt-Now:0.;
        C->WagerEndsAt=State.WagerEndsAt>0.?LocalNow+State.WagerEndsAt-Now:0.;
        C->ComposureEndsAt=State.ComposureEndsAt>0.?LocalNow+State.ComposureEndsAt-Now:0.;
        C->ElectrifiedBonus=State.ElectrifiedBonus;
        C->ChillSlow=State.ChillSlow;
        C->CorrosionDuration=State.CorrosionDuration;
        C->CorrosionReduction=State.CorrosionReduction;
        C->Shred=State.Shred;
        C->Ward=State.Ward;
        C->RuneVulnerability=State.RuneVulnerability;
        C->TigerRoarBonus=State.TigerRoarBonus;
        C->PhysicalVulnerabilityBonus=State.PhysicalVulnerabilityBonus;
        C->RiposteSpeed=State.RiposteSpeed;
        C->RiposteStamina=State.RiposteStamina;
        C->SlowPct=State.SlowPct;
        C->WaxPct=State.WaxPct;
        C->WeaponHasteMul=State.WeaponHasteMul;
        C->PetrifyMul=State.PetrifyMul;
        C->MarkedValue=State.MarkedValue;
        C->InspireSpeed=State.InspireSpeed;
        C->InspireAtk=State.InspireAtk;
        C->CamelReduction=State.CamelReduction;
        C->BerserkPeriod=State.BerserkPeriod;
        C->BerserkSpeedPerStack=State.BerserkSpeedPerStack;
        C->WagerPeriod=State.WagerPeriod;
        C->WagerBonusPerStack=State.WagerBonusPerStack;
        C->ComposurePeriod=State.ComposurePeriod;
        C->ComposureStabilityPerStack=State.ComposureStabilityPerStack;
        C->ComposureRecoilReductionPerStack=State.ComposureRecoilReductionPerStack;
        C->ElectrifiedStacks=State.ElectrifiedStacks;
        C->ChillStacks=State.ChillStacks;
        C->HasteStacks=State.HasteStacks;
        C->ChainStacks=State.ChainStacks;
        C->CorrosionStacks=State.CorrosionStacks;
        C->VulnerabilityStacks=State.VulnerabilityStacks;
        C->BleedStacks=State.BleedStacks;
        C->BerserkStacks=State.BerserkStacks;
        C->BerserkLimit=State.BerserkLimit;
        C->WagerStacks=State.WagerStacks;
        C->ComposureStacks=State.ComposureStacks;

    }
    if(State.Infection.bActive||GetOwner()->FindComponentByClass<UProgressiveInfectionComponent>())
    {
        auto* I=UProgressiveInfectionComponent::GetOrAdd(GetOwner());const auto Before=I->State.Stage();
        I->State=State.Infection;if(I->State.bActive)I->State.ElapsedSeconds=FMath::Max(0.,Now-State.InfectedAt);
        I->Publish(Before!=I->State.Stage());
    }
    if(State.PoisonStacks>0||GetOwner()->FindComponentByClass<UMaggotPoisonComponent>())
    {
        auto* P=GetOwner()->FindComponentByClass<UMaggotPoisonComponent>();
        if(!P){P=NewObject<UMaggotPoisonComponent>(GetOwner());GetOwner()->AddInstanceComponent(P);P->RegisterComponent();}
        const int32 Elapsed=FMath::Max(0,FMath::FloorToInt((Now-State.PoisonDecayAt)/5.)+1);
        P->Stacks=FMath::Max(0,State.PoisonStacks-Elapsed);P->DecayLeft=P->Stacks>0?FMath::Max(0.,State.PoisonDecayAt+Elapsed*5.-Now):0.f;
    }
    if(!State.FearExpirations.IsEmpty()||GetOwner()->FindComponentByClass<UHandBrainFearComponent>())
    {
        auto* F=GetOwner()->FindComponentByClass<UHandBrainFearComponent>();
        if(!F){F=NewObject<UHandBrainFearComponent>(GetOwner());GetOwner()->AddInstanceComponent(F);F->RegisterComponent();}
        F->Expirations.Reset();for(double End:State.FearExpirations)if(End>Now)F->Expirations.Add(LocalNow+End-Now);
        F->Stacks=F->Expirations.Num();F->Threat=State.FearThreat;
        if(F->Stacks>0)
        {
            if(auto* Pawn=Cast<ACharacter>(GetOwner());Pawn&&Pawn->IsLocallyControlled())
            {
                if(!F->LockedController.IsValid()&&Pawn->GetController()){F->LockedController=Pawn->GetController();F->LockedController->SetIgnoreMoveInput(true);}
                Pawn->GetCharacterMovement()->AddTickPrerequisiteComponent(F);F->SetComponentTickEnabled(true);
            }
        }
        else F->Release();
    }
    if(bPublishDisplay)
    {
        auto* Display=UStatusEffectsComponent::GetOrCreate(GetOwner());Display->Records.Reset();
        for(const auto& D:State.Display)
        {
            auto& R=Display->Records.AddDefaulted_GetRef();R.View=UStatusEffectsComponent::Definition(D.Type);
            R.End=LocalNow+D.End-Now;R.View.Duration=D.Duration;R.View.Stacks=D.Stacks;
            R.View.Battles=D.Battles;R.View.Persistent=D.Persistent;R.View.DurationText=D.DurationText;
            if(!D.Name.IsEmpty())R.View.Name=D.Name;if(!D.Icon.IsEmpty())R.View.Icon=D.Icon;if(D.Color!=FLinearColor::Transparent)R.View.Color=D.Color;
        }
        Display->OnChanged.Broadcast();
    }
}
