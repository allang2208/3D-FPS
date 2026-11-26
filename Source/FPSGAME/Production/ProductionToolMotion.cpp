#include "ProductionToolComponent.h"
#include "../Skills/ChainSlashMotion.h"
#include "ThunderHammerThrown.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../Weapons/RuneSwordWhirlwindFeel.h"
#include "../Weapons/RuneSwordUppercutMotion.h"
#include "ProductionBluntCombo.h"
#include "WarhammerHeavyMotion.h"
#include "WarhammerUppercutMotion.h"
#include "WarhammerQuickCombatMotion.h"
#include "WarhammerConicalThrustMotion.h"
#include "WarhammerGuardMotion.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "ProductionToolMeshComponent.h"
#include "ProductionPickaxeImpactMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/World.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
struct FToolElectricAnchor {FVector Base=FVector::ZeroVector,Tip=FVector::ZeroVector;};
TMap<FString,FToolElectricAnchor> ElectricAnchors;
}

void UProductionToolComponent::LoadEnchantmentAnchors()
{
    static bool bLoaded=false;if(bLoaded)return;bLoaded=true;
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/electrified-tool-anchors.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return;
    for(const auto& Entry:Root->Values)
    {
        const auto Data=Entry.Value->AsObject();if(!Data)continue;
        const TArray<TSharedPtr<FJsonValue>> *Base=nullptr,*Tip=nullptr;
        if(Data->TryGetArrayField(TEXT("base_local"),Base)&&Data->TryGetArrayField(TEXT("tip_local"),Tip)&&Base->Num()==3&&Tip->Num()==3)
        {
            FToolElectricAnchor Anchor;
            Anchor.Base=FVector((*Base)[0]->AsNumber(),(*Base)[1]->AsNumber(),(*Base)[2]->AsNumber());
            Anchor.Tip=FVector((*Tip)[0]->AsNumber(),(*Tip)[1]->AsNumber(),(*Tip)[2]->AsNumber());
            ElectricAnchors.Add(FString(*Entry.Key),Anchor);
        }
    }
}

static TAutoConsoleVariable<float> PickaxeImpactCameraScale(TEXT("fps.Tool.PickaxeCamera"),1.f,
    TEXT("Pickaxe windup and single heavy confirmed-impact camera strength. 0 disables this camera layer."));

bool UProductionToolComponent::HasReadyPresentation() const
{
    if(!bUsesArms)return ToolMesh && ToolMesh->GetStaticMesh();
    if(!Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return false;
    if(Kind==TEXT("warhammer"))
    {
        const auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel);
        if(!Arms||!Arms->GetGripProfile())return false;
        for(const TCHAR* Clip:ProductionBluntCombo::Clips)
            if(!Motions.FindRef(FName(Clip)))return false;
        for(const TCHAR* Clip:{TEXT("SprintCarry"),TEXT("HeavyCharge"),TEXT("HeavyRelease")})
            if(!Motions.FindRef(FName(Clip)))return false;
        if(bFinalTollHead&&!Motions.FindRef(TEXT("FinalTollHeavy")))return false;
        if(bThunderThrowSeat)for(const TCHAR* Clip:{TEXT("ThunderCharge"),TEXT("ThunderThrow"),TEXT("ThunderRecallReady"),TEXT("ThunderCatch")})
            if(!Motions.FindRef(Clip))return false;
        if(bThunderCallSeat)for(const TCHAR* Clip:{TEXT("ThunderCallCharge"),TEXT("ThunderCallRelease")})
            if(!Motions.FindRef(Clip))return false;
    }
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Equip"),TEXT("Swing"),TEXT("HitRecover")})
        if((!UsesTwoHandMotion() || FName(Clip)!=TEXT("Walk")) && !Motions.FindRef(FName(Clip)))return false;
    return true;
}

bool UProductionToolComponent::GetEnchantmentBladeAttachment(USceneComponent*& Parent,FName& Socket,FTransform& LocalFrame,float& Length) const
{
    if(IsThunderHammerAway()||!IsEquipped()||!Viewmodel||!Viewmodel->IsVisible()||Viewmodel->bHiddenInGame||!Viewmodel->DoesSocketExist(TEXT("WPN_root")))return false;
    // Derived from the imported rigid tool vertices; cached before combat begins.
    FVector LocalBase,LocalTip;if(!GetEnchantmentBladeSpan(LocalBase,LocalTip))return false;
    const FTransform Weapon=Viewmodel->GetSocketTransform(TEXT("WPN_root"));
    const FVector Base=Weapon.TransformPosition(LocalBase),Tip=Weapon.TransformPosition(LocalTip);
    Length=FVector::Distance(Base,Tip);if(Length<1.f)return false;
    const FTransform WorldFrame(FRotationMatrix::MakeFromXZ(Tip-Base,Weapon.GetUnitAxis(EAxis::Z)).ToQuat(),Base);
    Parent=Viewmodel;Socket=TEXT("WPN_root");LocalFrame=WorldFrame.GetRelativeTransform(Weapon);
    return true;
}

bool UProductionToolComponent::GetEnchantmentBladeSpan(FVector& Base,FVector& Tip) const
{
    if(bPojunGrip){Base=PojunBladeBase;Tip=PojunBladeTip;return true;}
    const auto* Anchor=ElectricAnchors.Find(Kind);if(!Anchor)return false;
    Base=Anchor->Base;Tip=Anchor->Tip;return true;
}

void UProductionToolComponent::SampleMotion(FName Clip,float Seconds)
{
    UAnimSequence* Motion=Motions.FindRef(Clip);
    if(!Motion || !Viewmodel)return;
    const bool ChainCut=Clip==TEXT("PojunChain");
    // An interrupted cast can restart the same sequence before returning to idle.
    const bool RestartChainCut=ChainCut&&CurrentMotion==Motion&&Seconds+UE_SMALL_NUMBER<Viewmodel->GetPosition();
    if(CurrentMotion!=Motion||RestartChainCut)
    {
        const bool RecallClip=Clip==TEXT("ThunderCatch")||Clip==TEXT("ThunderRecallReady");
        if(RecallClip)if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->ClearWhirlwindEntry();
        const bool GuardClip=Clip==TEXT("GuardEnter")||Clip==TEXT("GuardHold")||Clip==TEXT("GuardHit")||Clip==TEXT("GuardBreak")||Clip==TEXT("GuardExit");
        const bool MatchedNormal=Kind==TEXT("warhammer")&&!bBluntHeavy&&CurrentMotion&&
            (Clip==TEXT("ActiveSwing")||Clip==TEXT("ActiveHitRecover"))&&
            CurrentMotion->GetName().StartsWith(TEXT("A_Warhammer_Slash"));
        if(MatchedNormal&&!bBluntHandoffEntry)
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->ClearWhirlwindEntry();
        bBluntHandoffEntry=false;
        const bool ChixiaoOpening=PojunSlashTime>=0.f&&Clip==ProductionBluntCombo::Swing(PojunChixiao::OpeningStage);
        const bool ContactEntry=Clip==TEXT("ActiveHitRecover")&&CurrentMotion==Motions.FindRef(TEXT("ActiveSwing"));
        // An interrupted inspect can be mid-turn with loose palms: hand off around the shaft.
        const bool LeavingInspect=CurrentMotion&&(CurrentMotion==Motions.FindRef(TEXT("Inspect"))||CurrentMotion==Motions.FindRef(TEXT("InspectWalk")));
        if(!ChainCut&&!bLeapStrike&&Kind==TEXT("warhammer")&&CurrentMotion&&!RecallClip&&!GuardClip&&Clip!=TEXT("QuickCombat")&&Clip!=TEXT("Uppercut")&&Clip!=TEXT("Whirlwind")&&Clip!=TEXT("HitRecover")&&!ContactEntry&&!MatchedNormal&&!ChixiaoOpening&&
            !(bBluntHeavy&&Clip==TEXT("ActiveSwing")))
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(
                // A visual chain hands the turnaround into the next cut's load around the shaft.
                bBluntChain&&Clip==ProductionBluntCombo::Swing(BluntChainStage)?BluntChainBlend:
                Clip==TEXT("Inspect")||Clip==TEXT("InspectWalk")?.14f:Clip==TEXT("ActiveSwing")&&Elapsed<RealContactSeconds()?
                    FMath::Min(.14f/RateScale,FMath::Max(.001f,RealContactSeconds()-Elapsed)):.14f/RateScale,
                (!bBluntHeavy&&!bBluntCharging&&Elapsed>=0.f)||LeavingInspect);
        if(bBluntHeavy&&Clip==TEXT("ActiveSwing"))
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))
            {
                if(bBluntSprintAttack)Arms->CaptureLocomotionEntry(BluntLiftSeconds());
                else Arms->ClearWhirlwindEntry();
            }
        CurrentMotion=Motion;
        if(GuardClip)
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(.06f,true);
        if(Clip==TEXT("QuickCombat"))
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(WarhammerQuickCombat::Entry,true);
        if(ChainCut)
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(.14f,true,true);
        if(ChixiaoOpening)
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(PojunChixiao::Release-PojunChixiao::Start,true);
        if(!bLeapStrike&&(Clip==TEXT("Whirlwind")||Clip==TEXT("Uppercut")))
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->CaptureLocomotionEntry(.10f,true);
        Viewmodel->PlayAnimation(Motion,false);
        Viewmodel->SetPlayRate(0.f);
    }
    if(bBluntHeavy&&bBluntSprintAttack&&Clip==TEXT("ActiveSwing"))
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(Elapsed);
    if(bBluntWhirlwind&&Clip==TEXT("Whirlwind"))
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(BluntWhirlwindTime);
    if(PojunSlashTime>=0.f&&Clip==ProductionBluntCombo::Swing(PojunChixiao::OpeningStage))
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(PojunSlashTime-PojunChixiao::Start);
    if(bBluntUppercut&&Clip==TEXT("Uppercut"))
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(BluntUppercutTime);
    if(ChainCut)
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(Seconds);
    if(IsQuickCombatActive()&&Clip==TEXT("QuickCombat"))
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(Seconds);
    if(IsGuardActive()&&Character->RuneSword)
    {
        FName GuardClip;float GuardSeconds=0.f,GuardAge=0.f;
        if(Character->RuneSword->GetToolGuardPose(GuardClip,GuardSeconds,GuardAge)&&Clip==GuardClip)
            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->SetWhirlwindEntryTime(GuardAge);
    }
    // Quick-combat callers, including the exact-contact probe, pass real age.
    // Keep entry blending on that clock and retime the entire pose only once.
    if(Clip==TEXT("QuickCombat"))Seconds=bConicalSeat?WarhammerConicalThrust::SourceSeconds(Seconds):WarhammerQuickCombat::SourceSeconds(Seconds);
    Viewmodel->SetPosition(FMath::Clamp(Seconds,0.f,Motion->GetPlayLength()),false);
    Viewmodel->TickAnimation(0.f,false);
    Viewmodel->RefreshBoneTransforms();
    if(!ChainCut)FeedWarhammerRift(Clip,Seconds);
}

bool UProductionToolComponent::IsPojunChainOccupied() const
{
    return Character.IsValid()&&Character->RuneSword&&Character->RuneSword->IsPojunChainOccupied();
}

void UProductionToolComponent::SamplePojunChain(float Source,float Length,TConstArrayView<float> Contacts)
{
    const auto Phase=ChainSlashMotion::Phase(Source,Length,Contacts);
    Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
    if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
    SampleMotion(TEXT("PojunChain"),Source);
    FeedWarhammerRift(TEXT("PojunChain"),Source,Phase.Cut,Phase.Contact);
}

void UProductionToolComponent::UpdateHandPresentation(float Delta)
{
    VisualTime+=Delta;
    // Also retire a draw already started before the replicated away state
    // arrived; the away/catch branches below do not advance its clock.
    if(IsThunderHammerAway())EquipElapsed=-1.f;
    if(PresentThunderCatch(Delta))return;
    if(IsThunderHammerAway()&&Elapsed<0.f)return;
    if(bLeapStrike){PresentLeapStrike();return;}
    if(IsPojunChainOccupied())return;
    // Every action, sprint, jump or dodge takes over from the cosmetic inspect.
    if(InspectElapsed>=0.f&&ShouldBreakInspect())CancelInspect();
    if(PresentGuardPose())return;
    TickWalkInspect(Delta);
    if(IsQuickCombatActive())
    {
        if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
        Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
        SampleMotion(TEXT("QuickCombat"),Character->QuickCombatPistol->GetActionAge());return;
    }
    if(bBluntUppercut||bBluntWhirlwind)
        if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
    if(bBluntUppercut)
    {
        Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
        if(PojunSlashTime>=0.f)SampleMotion(ProductionBluntCombo::Swing(PojunChixiao::OpeningStage),PojunSlashTime);
        else SampleMotion(TEXT("Uppercut"),BluntUppercutPoseTime());
        return;
    }
    if(bBluntWhirlwind)
    {
        Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
        SampleMotion(TEXT("Whirlwind"),BluntWhirlwindPoseTime());UpdateBluntWhirlwindFocus();return;
    }
    const float Speed=Character->GetVelocity().Size2D();
    const bool bTwoHand=UsesTwoHandMotion();
    if(Kind==TEXT("warhammer"))
    {
        const float Target=DashReadyFraction()>=1.f-UE_SMALL_NUMBER?1.f:0.f;
        // Match the sword: earn readiness first, then enter/exit the supported
        // carry over half a second. Reversal continues from the visible pose.
        SprintBlend=FMath::FInterpConstantTo(SprintBlend,Target,Delta,1.f/WarhammerSprint::CarryTransitionSeconds);
        if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->AdvanceLocomotionEntry(Delta);
    }
    if(!bTwoHand)
    {
        const float SprintTarget=Elapsed<0 && Speed>650.f?1.f:0.f;
        SprintBlend=FMath::Lerp(SprintBlend,SprintTarget,1.f-FMath::Exp(-14.f*Delta));
        Viewmodel->SetRelativeLocation(FVector(-3,0,-6)*SprintBlend);
    }
    if(bBluntHeavy&&!UsesFinalTollHeavy()&&!UsesThunderThrowHeavy()&&Elapsed>=0.f)
    {
        // The strike remains in its stable forward frame as the camera follows
        // the head down. Camera feedback must not rotate the grounded hammer.
        const float Anchor=WarhammerHeavy::AnchorWeight(AuthoredElapsed());
        const FQuat Rotation=FQuat::Slerp(Camera->GetComponentQuat(),BluntSlamRotation,Anchor).GetNormalized();
        Viewmodel->SetWorldLocationAndRotation(FMath::Lerp(Camera->GetComponentLocation(),BluntSlamEye,Anchor),
            Rotation*FRotator(0,90,0).Quaternion());
    }
    if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))
        Arms->SetFloorContact(BluntFloorPoint,bBluntHeavy&&!UsesFinalTollHeavy()&&!UsesThunderThrowHeavy()&&bBluntFloorTarget?WarhammerHeavy::FloorWeight(AuthoredElapsed()):0.f);
    if(bBluntReturningCharge||(bBluntCharging&&(!bThunderCallSeat||IsThunderCalling())))
    {
        if(bThunderCallSeat)SampleMotion(TEXT("ThunderCallCharge"),BluntChargePoseSeconds());
        else if(bThunderThrowSeat)SampleMotion(TEXT("ThunderCharge"),BluntChargePoseSeconds());
        else if(bFinalTollHead)
            SampleMotion(TEXT("Slash1"),FinalTollHeavy::ChargeSource(BluntChargePoseSeconds()/WarhammerHeavy::ChargeSeconds));
        else SampleMotion(TEXT("HeavyCharge"),BluntChargePoseSeconds());
    }
    else if(ThunderCallReleaseAge>=0.f)SampleMotion(TEXT("ThunderCallRelease"),ThunderCallReleaseAge);
    else if(Elapsed>=0)
    {
        // Pose, whoosh and the one authoritative contact share the same clock.
        // Only a confirmed resource/enemy hit chooses braced recovery; misses follow through.
        // 挥砍速度改造只压缩真实时钟：动画仍按作者时间采样，RateScale=1 时逐帧等价。
        const float Authored=AuthoredElapsed();
        // Buffered next cut: its load is already visible during this cut's tail.
        if(bBluntChain)SampleMotion(ProductionBluntCombo::Swing(BluntChainStage),BluntChainClipTime());
        else if(bBluntHeavy)SampleMotion(TEXT("ActiveSwing"),Authored);
        else if(bHitConfirmed)
        {
            // Confirmed dig: shovel HitRecover (0.5 s authored) maps 1:1 from the
            // contact age; the .44 s legacy remap is for the older short clips.
            const bool bShovel=Kind==TEXT("shovel");
            const float RecoverSource=bShovel?(Authored-ContactSeconds):
                .44f*(Authored-ContactSeconds)/(Kind==TEXT("axe")?AxeMotion.HitRecoverSeconds:SwingSeconds-ContactSeconds);
            SampleMotion(Motions.FindRef(TEXT("ActiveHitRecover"))?TEXT("ActiveHitRecover"):TEXT("HitRecover"),Kind==TEXT("warhammer")?
                ProductionBluntCombo::HitSourceTime(Authored-ContactSeconds):UsesPickaxeMotion()?
                ProductionPickaxeImpact::SourceHitTime(Authored-ContactSeconds):RecoverSource);
        }
        else
        {
            // The shovel's authored Swing is 0.82 s from contact-time mapping; other
            // single-hand skeletal tools keep the legacy .24/.44 author-time remap.
            const bool bShovel=Kind==TEXT("shovel");
            const float SourceTime=bBluntSprintAttack?Authored:Kind==TEXT("warhammer")?BluntClipTime():
                bShovel?Authored:
                (Authored<ContactSeconds?.24f*Authored/ContactSeconds:.24f+.44f*(Authored-ContactSeconds)/(SwingSeconds-ContactSeconds));
            SampleMotion(Motions.FindRef(TEXT("ActiveSwing"))?TEXT("ActiveSwing"):TEXT("Swing"),SourceTime);
        }
    }
    else if(EquipElapsed>=0)
    {
        EquipElapsed+=Delta*LightningHaste::ActionSpeed(GetOwner());
        SampleMotion(TEXT("Equip"),EquipElapsed);
        if(EquipElapsed>=Motions.FindRef(TEXT("Equip"))->GetPlayLength())
        {
            EquipElapsed=-1.f;
            if(bTwoHand)VisualTime=0.f;
        }
    }
    else if(InspectElapsed>=0.f)
    {
        // Own real-time clock: no attack rate, stamina or hit window.
        const UAnimSequence* Inspect=Motions.FindRef(InspectClip);
        const float CueFrom=InspectElapsed;
        const float Rate=LightningHaste::ActionSpeed(GetOwner());
        InspectElapsed+=Delta*Rate;
        PlayInspectCues(CueFrom,InspectElapsed,Rate);
        if(Inspect&&InspectElapsed<Inspect->GetPlayLength())SampleMotion(InspectClip,InspectElapsed);
        else
        {
            // The authored last frame is the idle start; resume idle from there.
            CancelInspect();VisualTime=0.f;SampleMotion(TEXT("Idle"),0.f);
        }
    }
    else if(Kind==TEXT("warhammer")&&SprintBlend>.001f)
        SampleMotion(TEXT("SprintCarry"),SprintBlend*Motions.FindRef(TEXT("SprintCarry"))->GetPlayLength());
    else
    {
        // Two-hand tools keep the fitted idle grasp at every movement speed.
        const FName Clip=!bTwoHand && Speed>20.f?TEXT("Walk"):TEXT("Idle");
        const float Duration=Motions.FindRef(Clip)->GetPlayLength();
        SampleMotion(Clip,FMath::Fmod(VisualTime,Duration));
    }
    if(bTwoHand)UpdateTwoHandLocomotion(Delta);
}

void UProductionToolComponent::GetCameraMotion(FVector& Location,FRotator& Rotation) const
{
    Location=FVector::ZeroVector; Rotation=FRotator::ZeroRotator;
    if(bLeapStrike){LeapStrikeCamera(Location,Rotation);return;}
    const bool ThunderDocking=IsThunderHammerAway()&&ThrownHammer&&ThrownHammer->IsCatching();
    if(bThunderThrowSeat&&IsEquipped()&&CanPresent()&&(ThunderDocking||ThunderCatchAge>=0.f))
    {
        // Same .025 s palm-load event as RecallWeightV4. Read the committed
        // catch clock across the projectile/held-mesh handoff; never retrigger.
        const float Age=ThunderDocking?ThrownHammer->CatchAge():float(RuneboundClock()-ThunderCatchStartedAt);
        const float T=Age-.025f;
        if(T>0.f&&T<.50f)
        {
            const auto* Shake=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Camera.Shake"));
            const float Scale=Shake?FMath::Max(0.f,Shake->GetFloat()):1.f;
            // One readable body jolt, a short loaded dip, then recovery.
            // The high-frequency shock rides on this weight transfer; it
            // must not be the entire catch, as it decays before it reads.
            static const ProductionPickaxeImpact::FCameraKey CatchLoadV4[]={
                {0.f,{0,0,0},{0,0,0}},
                {.035f,{-4.f,.45f,-1.15f},{-3.f,.30f,-1.8f}},
                {.090f,{-3.1f,.25f,-.65f},{-2.2f,.20f,-1.3f}},
                {.150f,{-1.7f,0,-.3f},{-1.2f,0,-.7f}},
                {.230f,{.65f,-.15f,.20f},{.3f,-.05f,.2f}},
                {.350f,{0,0,0},{0,0,0}},
                {.500f,{0,0,0},{0,0,0}}};
            const auto Load=ProductionPickaxeImpact::CameraCurve(CatchLoadV4,T);
            const float Envelope=FMath::Exp(-16.f*T)*FMath::SmoothStep(0.f,.006f,T)*
                (1.f-FMath::SmoothStep(.24f,.40f,T));
            const float Shock=FMath::Sin(69.f*T)*Envelope;
            Location=(Load.Position+FVector(-.9f*Shock,.28f*FMath::Sin(87.f*T)*Envelope,-.55f*Shock))*Scale;
            Rotation=(FRotator(Load.Angles.X,Load.Angles.Y,Load.Angles.Z)+
                FRotator(-1.8f*Shock,.32f*FMath::Sin(79.f*T)*Envelope,.7f*FMath::Sin(83.f*T)*Envelope))*Scale;
        }
        return;
    }
    if(bBluntUppercut)
    {
        if(PojunSlashTime>=0.f)
        {
            ProductionBluntCombo::SampleCamera(PojunSlashTime,PojunChixiao::OpeningStage,false,Location,Rotation);
            const float Blend=FMath::SmoothStep(PojunChixiao::Start,PojunChixiao::Release,PojunSlashTime);
            Location=FMath::Lerp(FVector(-13.f,6.f,3.f),Location,Blend);
            Rotation=FMath::Lerp(FRotator(7.8f,6.f,5.f),Rotation,Blend);
            return;
        }
        WarhammerUppercutMotion::Camera(BluntUppercutTime,!bBluntUppercutLungeBlocked,Location,Rotation);
        Location*=1.1f;Rotation*=1.1f;
        if(PojunAttack==PojunGrip::EAttack::Chixiao&&BluntUppercutTime<.10f)
        {
            FVector FromLocation;FRotator FromRotation;
            ProductionBluntCombo::SampleCamera(PojunChixiao::Handoff,PojunChixiao::OpeningStage,false,FromLocation,FromRotation);
            const float Blend=FMath::SmoothStep(0.f,.10f,BluntUppercutTime);
            Location=FMath::Lerp(FromLocation,Location,Blend);
            Rotation=FMath::Lerp(FromRotation,Rotation,Blend);
        }
        if(BluntUppercutImpactAge<.16f)
            Rotation.Pitch+=FMath::Sin(BluntUppercutImpactAge*90.f)*FMath::Exp(-23.f*BluntUppercutImpactAge)*1.5f;
        return;
    }
    if(bBluntWhirlwind)
    {
        WhirlwindFeel::Camera(BluntWhirlwindTime,BluntWhirlwindTuning,BluntWhirlwindImpactAge,BluntWhirlwindImpactStrength,Location,Rotation);
        return;
    }
    if(bBluntCharging||bBluntReturningCharge)
    {
        const float W=FMath::SmoothStep(0.f,WarhammerHeavy::ChargeSeconds,BluntChargePoseSeconds());
        if(bThunderCallSeat){Location=FVector(-1.f,0,.5f)*W;return;}
        if(bThunderThrowSeat){Location=FVector(-3.f,0,1.5f)*W;Rotation=FRotator(3.f,0,0)*W;return;}
        Location=FVector(-13.f,6.f,3.f)*W;Rotation=FRotator(7.8f,6.f,5.f)*W;return;
    }
    if(Elapsed<0.f||!IsEquipped()||!CanUse(true))return;
    if(UsesThunderThrowHeavy())
    {
        const float T=AuthoredElapsed(),W=FMath::Exp(-8.f*FMath::Max(0.f,T-ThunderHammerThrow::Release))*FMath::SmoothStep(0.f,ThunderHammerThrow::Release,T);
        Location=FVector(2.5f,0,-2.f)*W;Rotation=FRotator(-3.5f,0,0)*W;return;
    }
    if(UsesFinalTollHeavy())
    {
        const float T=Elapsed;
        const float Down=FMath::Exp(-10.f*FMath::Max(0.f,T-FinalTollHeavy::FirstContact))*FMath::SmoothStep(0.f,FinalTollHeavy::FirstContact,T);
        const float Up=FMath::Exp(-9.f*FMath::Max(0.f,T-FinalTollHeavy::SecondContact))*FMath::SmoothStep(FinalTollHeavy::SecondStart,FinalTollHeavy::SecondContact,T);
        Location=FVector(2.f*Down+1.5f*Up,1.4f*Up,-3.2f*Down+1.4f*Up);
        Rotation=FRotator(-4.5f*Down+2.4f*Up,1.5f*Up,-2.2f*Down+2.f*Up);
        return;
    }
    if(bBluntHeavy)
    {
        if(bBluntSprintAttack&&AuthoredElapsed()<0.f)
        {
            const float W=WarhammerHeavy::PostureEase(0.f,BluntLiftSeconds(),Elapsed);
            Location=FVector(-13.f,6.f,3.f)*W;Rotation=FRotator(7.8f,6.f,5.f)*W;return;
        }
        static const ProductionPickaxeImpact::FCameraKey Keys[]={
            {0.f,{7.8f,6.f,5.f},{-13.f,6.f,3.f}},
            {.075f,{-3.f,0,0},{5.f,0,-2.f}},
            {.115f,{-4.5f,0,.7f},{-3.f,0,-3.f}},
            {.26f,{0,0,0},{0,0,0}},
            {WarhammerHeavy::HoldEnd,{0,0,0},{0,0,0}},
            {WarhammerHeavy::Duration,{0,0,0},{0,0,0}}};
        const auto Key=ProductionPickaxeImpact::CameraCurve(Keys,AuthoredElapsed());
        Location=Key.Position;Rotation=FRotator(Key.Angles.X,Key.Angles.Y,Key.Angles.Z);
        const float T=AuthoredElapsed();
        if(T<WarhammerHeavy::Contact)
        {
            const float U=T/WarhammerHeavy::Contact,Burst=FMath::Square(FMath::Sin(PI*U));
            Location.X+=15.f*Burst;
            Rotation.Pitch+=2.55f*Burst*FMath::Sin(U*PI*6.f);
            Rotation.Roll+=3.3f*Burst*FMath::Sin(U*PI*4.f);
        }
        else if(bBluntFloorTarget&&T<WarhammerHeavy::Contact+.20f)
        {
            const float Age=T-WarhammerHeavy::Contact;
            const float Kick=FMath::Exp(-17.f*Age)*FMath::Sin(55.f*Age)*(1.f-FMath::SmoothStep(0.f,.20f,Age));
            Rotation.Pitch-=5.f*Kick;Location.Z-=3.5f*Kick;
        }
        return;
    }
    // 镜头关键帧是作者秒；改造后的真实时间先换算回作者时间再采样。
    if(Kind==TEXT("warhammer"))
    {
        ProductionBluntCombo::SampleCamera(bHitConfirmed?BluntHitClipTime():BluntClipTime(),BluntStage,bHitConfirmed,Location,Rotation);
        if(bBluntChain)
        {
            // Hand the camera to the chained cut's load by the time it begins.
            FVector NextLocation;FRotator NextRotation;
            ProductionBluntCombo::SampleCamera(BluntChainClipTime(),BluntChainStage,false,NextLocation,NextRotation);
            const float W=ProductionBluntCombo::Ease(BluntChainAge/FMath::Max(.001f,FMath::Min(BluntChainBlend,BluntChainSpan)));
            Location=FMath::Lerp(Location,NextLocation,W);Rotation=FMath::Lerp(Rotation,NextRotation,W);
        }
        return;
    }
    const float Authored=AuthoredElapsed();
    if(Kind==TEXT("axe"))AxeMotion.Sample(Authored,bHitConfirmed,Location,Rotation);
    else if(UsesPickaxeMotion())ProductionPickaxeImpact::SampleCamera(Authored,ContactSeconds,SwingSeconds,
        bHitConfirmed,PickaxeImpactCameraScale.GetValueOnGameThread(),Location,Rotation);
    else if(Kind==TEXT("shovel")&&bHitConfirmed)
    {
        // Shovel dig impact: one heavy camera dip at contact, then a smooth return
        // (user's two-hand tool camera rule; no oscillation). Slightly softer than
        // the pickaxe because a dig lodges soil, not stone.
        const float Age=Authored-ContactSeconds;
        const float K=FMath::Exp(-14.f*Age)*(1.f-FMath::SmoothStep(0.f,.30f,Age));
        Location=FVector(-2.5f,0.f,-2.0f)*K;
        Rotation=FRotator(-4.2f,0.f,1.1f)*K;
    }
}
