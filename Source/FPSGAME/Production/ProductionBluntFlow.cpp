#include "ProductionToolComponent.h"
#include "ProductionBluntCombo.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

void UProductionToolComponent::HandOffBluntPose()
{
    // The visible cut is not at its shared idle endpoint (chain mismatch or a
    // late server confirmation): blend from it around the shaft instead of
    // letting the matched-cut rule snap.
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(.14f,true);
    bBluntHandoffEntry=true;
}

float UProductionToolComponent::BluntClipTime() const
{
    // ContactSeconds is the rate-1 contact; the map keeps contact/end exact.
    return ProductionBluntCombo::ClipTime(Elapsed,RealContactSeconds(),RealSwingSeconds(),ContactSeconds,RateScale,BluntStage,BluntStartClip);
}

float UProductionToolComponent::BluntHitClipTime() const
{
    return ProductionBluntCombo::HitSourceTime(AuthoredElapsed()-ContactSeconds);
}

float UProductionToolComponent::BluntChainClipTime() const
{
    return BluntChainStartClip*FMath::Clamp(BluntChainAge/FMath::Max(.001f,BluntChainSpan),0.f,1.f);
}

void UProductionToolComponent::StartBluntChain(float Remaining)
{
    // Gameplay is untouched: the buffered cut still starts when this one ends
    // (same contact, cadence and server timer). Only its visible load begins
    // here, at exactly the load speed it keeps afterwards, so the hammer flows
    // from this cut's turnaround into the next cut without parking at idle.
    BluntChainStage=(BluntStage+1)%3;
    const float RealContact=ContactSeconds/RateScale;
    const float Load=FMath::Max(.001f,RealContact-ProductionBluntCombo::ReleaseReal(RealContact,ContactSeconds,RateScale,BluntChainStage));
    BluntChainSpan=Remaining;BluntChainAge=0.f;
    BluntChainStartClip=ProductionBluntCombo::Apex(BluntChainStage)*Remaining/(Remaining+Load);
    BluntChainBlend=FMath::Clamp(Remaining*.7f,.16f,.45f);
    bBluntChain=true;
}

float UProductionToolComponent::BluntClipRate() const
{
    // Clip seconds per real second right now (third-person progress rate).
    constexpr float Step=.01f;
    const float From=BluntClipTime();
    const float To=ProductionBluntCombo::ClipTime(Elapsed+Step,RealContactSeconds(),RealSwingSeconds(),ContactSeconds,RateScale,BluntStage,BluntStartClip);
    return FMath::Max(.05f,(To-From)/Step);
}

void UProductionToolComponent::AdvanceBluntChain(float Delta,float End)
{
    if(Kind!=TEXT("warhammer")||bBluntHeavy||bBluntSprintAttack||Elapsed<0.f)return;
    if(bBluntChain)
    {
        // The buffered cut was withdrawn (guard queued, input blocked): stop
        // showing its load and hand the visible pose back to this cut's tail.
        if(!bQueuedBluntAttack){bBluntChain=false;HandOffBluntPose();return;}
        BluntChainAge+=Delta;return;
    }
    if(!bQueuedBluntAttack||!bContacted)return;
    // Do not start a load the next cut cannot pay for.
    if(const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        !Profile||!Profile->CanSpendStamina(float(ToolStats.StaminaCost)))return;
    // Miss: after the follow-through turnaround (stage 2 also after its hand
    // swap back). Hit: once the hit stop has released.
    const int32 Stage=ProductionBluntCombo::SafeStage(BluntStage);
    const float Clip=bHitConfirmed?BluntHitClipTime():BluntClipTime();
    const float At=bHitConfirmed?ProductionBluntComboTiming::HitChainClip[Stage]:ProductionBluntComboTiming::ChainClip[Stage];
    if(Clip>=At&&End-Elapsed>.06f)StartBluntChain(End-Elapsed);
}
