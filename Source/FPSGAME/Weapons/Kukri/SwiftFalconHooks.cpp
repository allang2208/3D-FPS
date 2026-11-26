#include "KukriWeaponComponent.h"
#include "../../Combat/FPSAttackQuery.h"
#include "SwiftFalconHeavy.h"
#include "SwiftFalconHookVisual.h"
#include "../../FPSGAMECharacter.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Multiplayer/ColdSteelAuthorityContext.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../MeleeWeaponStats.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "TimerManager.h"

void UKukriWeaponComponent::ResetFalconHooks()
{
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(FalconDrawTimer);
    if(GetOwner()&&GetOwner()->HasAuthority() &&
       (FalconHookTargets[0].IsValid()||FalconHookTargets[1].IsValid()))
        MulticastClearFalconHooks();
    FalconHookTargets[0].Reset();FalconHookTargets[1].Reset();
    bFalconHooksDrawn=false;
}

void UKukriWeaponComponent::ConfirmFalconHook(const FColdSteelSkillShot& BladeShot,const FHitResult& Contact)
{
    auto* P=Pawn();auto* Target=Contact.GetActor();
    if(!P||!P->HasAuthority()||!IsValid(Target)||bFalconHooksDrawn||Target->ActorHasTag(TEXT("Friendly")))return;
    const bool Remote=!P->IsLocallyControlled();
    if(Remote && (!bServerFalconRelease||!IsNetworkHeavyReleaseWindowOpen(BladeShot.ItemInstance)))return;
    if(!Remote && (!bHeavyAttack||!bFalconHeavy||Shot.MeleeDamagePhase!=0))return;
    const FString& Main=Remote?ServerHeavyWeapon:InstanceId;
    const FString& Off=Remote?ServerHeavyOffhandWeapon:HeavyOffhandWeapon;
    const int32 Hand=BladeShot.ItemInstance==Main?0:1;
    if(Hand==1&&(Off.IsEmpty()||BladeShot.ItemInstance!=Off))return;
    auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
    if(!Combat||Combat->IsDead())return;
    auto& Current=FalconHookTargets[Hand];
    // Prefer two distinct actual contacts if both blades originally caught one victim.
    if(Current==Target||(Current.IsValid()&&Current!=FalconHookTargets[1-Hand]))return;
    Current=Target;
    const float Rate=Remote?ServerFalconRate:FalconReleaseRate;
    const float Hold=SwiftFalconHeavy::PlaybackSeconds(SwiftFalconHeavy::PullTrail,Rate)
        -SwiftFalconHeavy::PlaybackSeconds(SwiftFalconHeavy::ChopAt,Rate)+SwiftFalconHeavy::FleshStop(false,!Off.IsEmpty());
    const auto* Model=ColdSteelAuthority::ForPawn(P);
    const bool LeftHand=Hand==1||(Model&&!Model->Equipped());
    MulticastFalconMark(Hand,Target,Contact.ImpactPoint,Contact.BoneName,BladeShot.ItemInstance,Hold,LeftHand);
}

void UKukriWeaponComponent::ServerDrawFalconHooks_Implementation(double ChargeStarted)
{
    if(!GetWorld()||!bServerFalconRelease||bFalconHooksDrawn||ChargeStarted!=ServerHeavyLastStartedAt
        ||!IsNetworkHeavyReleaseWindowOpen(ServerHeavyWeapon))return;
    // A request carries no target or damage. Only this paid release's server-accepted contacts can move.
    const double Due=ServerFalconReleasedAt+SwiftFalconHeavy::PlaybackSeconds(SwiftFalconHeavy::PullTrail,ServerFalconRate);
    const double Wait=Due-GetWorld()->GetTimeSeconds();
    // A delayed reliable release and draw may arrive together. Keep the authority's earliest draw time.
    if(Wait>0.)GetWorld()->GetTimerManager().SetTimer(FalconDrawTimer,this,&UKukriWeaponComponent::DrawFalconHooks,float(Wait),false);
    else DrawFalconHooks();
}

void UKukriWeaponComponent::DrawFalconHooks()
{
    auto* P=Pawn();
    if(!P||!P->HasAuthority()||bFalconHooksDrawn)return;
    bFalconHooksDrawn=true;
    const bool Remote=!P->IsLocallyControlled();
    auto* Model=ColdSteelAuthority::ForPawn(P);
    const auto* Item=Model?Model->ActiveKukriWeapon():nullptr;
    const FString& Main=Remote?ServerHeavyWeapon:InstanceId;
    const FString& Off=Remote?ServerHeavyOffhandWeapon:HeavyOffhandWeapon;
    const auto* Other=ColdSteelMelee::PairedOneHandedWeapon(Item,Model);
    auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();
    if((Remote&&(!bServerFalconRelease||!IsNetworkHeavyReleaseWindowOpen(Main)))||
        (!Remote&&(!bHeavyAttack||!bFalconHeavy))||(Health&&Health->IsDead())||!Item||
        Item->InstanceId!=Main||(!Off.IsEmpty()&&(!Other||Other->InstanceId!=Off))||
        !SwiftFalconHeavy::Eligible(Item,Model,!Off.IsEmpty()))
    {ResetFalconHooks();return;}
    const FTransform Aim=P->GetMeleeAimTransform();
    const FVector Forward=Aim.GetUnitAxis(EAxis::X).GetSafeNormal2D();
    const FVector Right=FVector::CrossProduct(FVector::UpVector,Forward);
    const FVector Origin=P->GetActorLocation();
    const bool Shared=FalconHookTargets[0].IsValid() && FalconHookTargets[0]==FalconHookTargets[1];
    uint8 Valid=0,Tugs=0;
    for(int32 Hand=0;Hand<2;++Hand)
    {
        auto* Target=FalconHookTargets[Hand].Get();
        if(!Target||Target->ActorHasTag(TEXT("Friendly")))continue;
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat||Combat->IsDead())continue;
        const FVector Offset=Target->GetActorLocation()-Origin;
        const auto* HeldItem=Hand==1?Other:Item;
        if(!HeldItem)continue;
        const auto Stats=ColdSteelMelee::Evaluate(*HeldItem,Model);
        const double TargetRadius=Target->GetSimpleCollisionRadius();
        const double Range=Stats.BaseReach*Stats.Modifiers.MartialRange+TargetRadius+35.;
        if(Offset.SizeSquared()>FMath::Square(Range)||FVector::DotProduct(Offset.GetSafeNormal2D(),Forward)<.35)continue;
        FFPSAttackQuery Query(SCENE_QUERY_STAT(FalconHookCover),false,P);
        Query.AddIgnoredActor(Target);
        if(GetWorld()->LineTraceTestByChannel(Aim.GetLocation(),Target->GetActorLocation(),ECC_Visibility,Query))continue;
        Valid|=1<<Hand;
        if(Hand==1 && Shared && (Valid&1))continue;
        const float Side=(!Off.IsEmpty()&&!Shared)?(Hand==0?24.f:-24.f):0.f;
        const FVector Destination=Origin+Forward*(P->GetCapsuleComponent()->GetScaledCapsuleRadius()+25.f)+Right*Side;
        const bool Ahead=FVector::DotProduct(Target->GetActorLocation()-Destination,Forward)>0;
        if(Combat->ReceiveFalconDraw(P,Ahead?Destination:Target->GetActorLocation()))Tugs|=1<<Hand;
    }
    if(FalconHookTargets[0].IsValid()||FalconHookTargets[1].IsValid())
        MulticastFalconDraw(Valid,Tugs,Shared&&Valid==3,(SwiftFalconHeavy::PullAt-SwiftFalconHeavy::PullTrail)/(Remote?ServerFalconRate:FalconReleaseRate));
}

void UKukriWeaponComponent::MulticastFalconMark_Implementation(uint8 Hand,AActor* Target,FVector_NetQuantize10 Point,FName Bone,const FString& Weapon,float HoldSeconds,bool bLeftHand)
{
    if(GetNetMode()==NM_DedicatedServer||Hand>1||!IsValid(Target)||!Pawn())return;
    if(auto* Old=FalconHookVisuals[Hand].Get())Old->DestroyComponent();
    auto* Visual=NewObject<USwiftFalconHookVisual>(Pawn());
    Pawn()->AddInstanceComponent(Visual);Visual->RegisterComponent();
    Visual->Bind(Target,Point,Bone,Weapon,HoldSeconds,bLeftHand);
    FalconHookVisuals[Hand]=Visual;
}

void UKukriWeaponComponent::MulticastFalconDraw_Implementation(uint8 ValidHands,uint8 TugHands,bool bShared,float SecondsToSnap)
{
    for(int32 Hand=0;Hand<2;++Hand)
        if(auto* Visual=FalconHookVisuals[Hand].Get())
        {
            if(ValidHands&(1<<Hand))Visual->Draw(SecondsToSnap,bShared,Hand==0||!bShared,(TugHands&(1<<Hand))!=0);
            else Visual->DestroyComponent();
        }
}

void UKukriWeaponComponent::MulticastClearFalconHooks_Implementation()
{
    for(auto& Ref:FalconHookVisuals)if(auto* Visual=Ref.Get())Visual->DestroyComponent();
}
