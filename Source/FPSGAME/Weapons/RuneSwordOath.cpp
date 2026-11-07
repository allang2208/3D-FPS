#include "RuneSwordComponent.h"
#include "OathJudgmentVisualComponent.h"
#include "HighlandRidgeThrust.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundBase.h"
#include "Components/StaticMeshComponent.h"

void URuneSwordComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    // Owner predicts from the very same charge duration / input timestamp.
    // Skipping its cosmetic echo avoids an older charge packet replacing its
    // already-released or cancelled local presentation. Damage stays authoritative.
    DOREPLIFETIME_CONDITION(URuneSwordComponent,OathState,COND_SkipOwner);
    DOREPLIFETIME(URuneSwordComponent,GaleSwiftUntil);
}

double URuneSwordComponent::OathClock() const
{
    const auto* W=GetWorld();if(!W)return 0.;
    const auto* GS=W->GetGameState();return GS?GS->GetServerWorldTimeSeconds():W->GetTimeSeconds();
}

void URuneSwordComponent::RefreshOath(const FColdSteelItem* Item)
{
    // Observer state comes from replication, even if its local inventory refreshes.
    if(GetOwner()->GetLocalRole()==ROLE_SimulatedProxy)return;
    const auto* G=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const bool Installed=HighlandOathRune::Installed(G,Item);
    if(!Installed||(OathState.Phase&&Item&&OathState.Weapon!=Item->InstanceId))
    {
        ClearOath();
        if(OathVisual)OathVisual->Hide();
    }
    bOathInstalled=Installed;
    if(!Installed||GetNetMode()==NM_DedicatedServer||!Character.IsValid()||!Character->IsLocallyControlled())return;
    if(!OathRiftMaterial && Character.IsValid() && Character->IsLocallyControlled())
    {
        const FString Path=FString(HighlandOathRune::Root)+TEXT("M_OathJudgmentRift");
        if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Path))
            OathRiftMaterial=UMaterialInstanceDynamic::Create(Material,this);
    }
    if(!OathVisual)OathVisual=UOathJudgmentVisualComponent::CreateFor(GetOwner(),true);
    if(OathSoundLoad||OathReadySound)return;
    TArray<FSoftObjectPath> Paths;
    Paths.Emplace(FString(HighlandOathRune::Root)+TEXT("S_OathReady.S_OathReady"));
    Paths.Emplace(FString(HighlandOathRune::Root)+TEXT("S_OathImpact.S_OathImpact"));
    OathSoundLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this,[this,Paths]()
        {OathReadySound=Cast<USoundBase>(Paths[0].ResolveObject());OathHitSound=Cast<USoundBase>(Paths[1].ResolveObject());}));
}

void URuneSwordComponent::BeginOathCharge(double Start,float Duration)
{
    GaleChargePaid=0.f;
    ClearOath();
    if(!bOathInstalled)return;
    OathState.Weapon=InstanceId;OathState.Phase=1;OathState.Duration=Duration;OathState.FullAt=Start+Duration;
    if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
}

void URuneSwordComponent::ClearOath()
{
    if(GetOwner()->GetLocalRole()==ROLE_SimulatedProxy)return;
    const bool Changed=OathState.Phase!=0;
    OathState=FHighlandOathPresentation{};bOathChimed=false;bOathRefunded=false;
    OathAttackSerial=0;OathReceiptUntil=0.;OathPaidRelease=0.f;OathReleaseStamp=0.;
    OathImpactAt=-100.;
    if(OathVisual)OathVisual->Hide(false);
    if(Changed&&GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
}

void URuneSwordComponent::CommitOathRelease(double ReleasedAt,uint32 Serial)
{
    if(!bOathInstalled||!Serial||OathState.Phase!=1||OathState.Weapon!=InstanceId)return;
    const double Now=OathClock();
    // Receipt timestamps may cross actor channels. Validate the same bounded
    // synchronized clock as heavy charge; never grant a second window/receipt.
    if(!FMath::IsFinite(ReleasedAt)||ReleasedAt>Now+.1||Now-ReleasedAt>.9)return;
    if(!HighlandOathRune::InWindow(ReleasedAt,OathState.FullAt))
    {
        OathState={};
        if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
        return;
    }
    OathState.Phase=2;OathState.ReleaseAt=ReleasedAt;OathAttackSerial=Serial;
    OathReceiptUntil=ReleasedAt+1.6;bOathRefunded=false;
    if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
}

float URuneSwordComponent::OathWindowRemaining() const
{
    if(!bOathInstalled||!bCharging||OathState.Phase!=1||OathState.Weapon!=InstanceId)return 0.f;
    const double Now=OathClock();
    return HighlandOathRune::InWindow(Now,OathState.FullAt)?float(OathState.FullAt+HighlandOathRune::Window-Now):0.f;
}

float URuneSwordComponent::OathReleaseFlash() const
{
    return bOathInstalled&&OathState.Phase==2?float(FMath::Clamp(1.-(OathClock()-OathState.ReleaseAt)/.28,0.,1.)):0.f;
}

void URuneSwordComponent::ApplyOathToShot(FColdSteelSkillShot& Shot) const
{
    const auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* G=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!HighlandOathRune::Installed(G,Item)||Model->ActiveProductionTool()||Shot.ItemInstance!=Item->InstanceId||
        Shot.bRicochet||(Shot.AttackMeta!=0x10&&Shot.AttackMeta!=0x15))return;
    Shot.OathPhysicalMultiplier=float(G->Calculate(Item->Definition,G->Installed(*Item)).Melee.OathHeavyPhysical);
    if(Shot.AttackMeta==0x10&&OathState.Phase==2&&OathState.Weapon==InstanceId&&
        Shot.GuardAttackSerial==OathAttackSerial&&OathAttackSerial&&OathClock()<=OathReceiptUntil)
    {
        Shot.OathPhysicalMultiplier*=HighlandOathRune::JudgmentPhysical;
        Shot.ToughnessDamageMultiplier*=HighlandOathRune::JudgmentToughness;
    }
}

void URuneSwordComponent::ConfirmOathHit(const FColdSteelSkillShot& Shot,float Applied,const FVector& Point)
{
    if(!GetOwner()->HasAuthority()||Applied<=0.f||bOathRefunded||!bOathInstalled||Shot.bRicochet||
        Shot.AttackMeta!=0x10||!OathAttackSerial||Shot.GuardAttackSerial!=OathAttackSerial||
        OathState.Phase!=2||OathState.Weapon!=InstanceId||Shot.ItemInstance!=InstanceId||OathClock()>OathReceiptUntil)return;
    bOathRefunded=true;
    const float Refund=OathPaidRelease*HighlandOathRune::Refund;
    if(auto* Model=ColdSteelAuthority::ForPawn(Character.Get()))
    {
        FGalePayment* Payment=GalePayments.Find(GaleWing::Key(GaleWing::EAttack::Heavy,OathAttackSerial));
        if(Payment && Payment->Weapon!=Shot.ItemInstance)Payment=nullptr;
        const float Before=Model->Stamina();
        const float Available=Payment?FMath::Min(Refund,Payment->Unreturned):Refund;
        const double Total=Model->RefundOathStamina(Available);
        if(Payment)Payment->Unreturned=FMath::Max(0.f,Payment->Unreturned-(Model->Stamina()-Before));
        if(Character.IsValid()&&!Character->IsLocallyControlled())ClientOathRefund(OathAttackSerial,Total);
    }
    MulticastOathImpact(InstanceId,OathState.ReleaseAt,OathClock(),Point);
}

void URuneSwordComponent::ClientOathRefund_Implementation(uint32 Serial,double Total)
{
    if(!Character.IsValid()||Character->HasAuthority()||!Character->IsLocallyControlled()||
        !Serial||int32(Serial-OathRefundReceipt)<=0)return;
    OathRefundReceipt=Serial;
    if(auto* Model=ColdSteelAuthority::ForPawn(Character.Get()))Model->ApplyOathRefundReceipt(Total);
}

double URuneSwordComponent::OathImpactTime(const FHighlandOathPresentation& State) const
{
    return State.Phase==2 && OathImpactWeapon==State.Weapon && FMath::IsNearlyEqual(OathImpactRelease,State.ReleaseAt,.001)
        ?OathImpactAt:-100.;
}

void URuneSwordComponent::MulticastOathImpact_Implementation(const FString& Weapon,double ReleaseAt,double HitAt,FVector_NetQuantize Point)
{
    // The hit RPC and presentation property can arrive in either order. Keep
    // the server timestamp so an old impact cannot start a new flash on arrival.
    if(HitAt<OathImpactAt)return;
    OathImpactWeapon=Weapon;OathImpactRelease=ReleaseAt;OathImpactAt=HitAt;OathImpactPoint=Point;
}

void URuneSwordComponent::TickOath()
{
    if(!Character.IsValid())return;
    if(OathState.Phase&&GetOwner()->HasAuthority()&&
        (!CanMaintainHeavyCharge()||(OathState.Phase==2&&OathClock()>OathReceiptUntil)))ClearOath();
    if(!Character->IsLocallyControlled()||!bOathInstalled)return;
    if(OathState.Phase==2&&!bAttacking)ClearOath();
    if(OathWindowRemaining()>0.f&&!bOathChimed)
    {bOathChimed=true;if(OathReadySound)UGameplayStatics::PlaySound2D(this,OathReadySound,.65f);}
    if(!OathVisual)return;
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    FVector Base,Tip;
    if(!CanPresent()||(Body&&Body->IsThirdPersonViewEnabled())||!GetFireMagicBladePoints(Base,Tip))
    {OathVisual->Hide();return;}
    const bool RidgeCut=bAttacking && CurrentClip==HighlandRidgeThrust::Release &&
        Elapsed>=ContactStart && (Elapsed<=ContactEnd+.035f ||
        (Elapsed<=ContactEnd+HighlandRidgeThrust::HoldSeconds && OathVisual->NeedsThrustEndpoint(OathState)));
    OathVisual->Present(ModularSword,Base,Tip,OathState,OathClock(),OathImpactTime(OathState),OathImpactPoint,
        RidgeCut?EOathStroke::Thrust:EOathStroke::None);
}
