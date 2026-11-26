#include "KukriWeaponComponent.h"
#include "KukriDecisiveComponent.h"
#include "KukriAttackTiming.h"
#include "../../Characters/FPSComponentVisibility.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriDrawRhythm.h"
#include "HatchetDrawRhythm.h"
#include "HatchetChopRhythm.h"
#include "HatchetDualChopRhythm.h"
#include "HatchetReadyRhythm.h"
#include "HatchetPairRhythm.h"
#include "KukriDualDashRhythm.h"
#include "KukriDualEquipBlade.h"
#include "KukriOffhandDraw.h"
#include "OffhandBladeDraw.h"
#include "KukriHeavyRhythm.h"
#include "SwiftFalconHeavy.h"
#include "../MeleeWeaponStats.h"
#include "../MeleeSmallTargetQuery.h"
#include "../RuneSwordRhythm.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "../../Building/VoxelBuildComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Movement/FPSCharacterMovementComponent.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

#include "KukriWeaponPrivate.h"
using namespace KukriWeaponPrivate;
void UKukriWeaponComponent::InitializePresentation()
{
    auto* P=Pawn();
    if(!P||!Camera)return;
    // Airborne presentation stays on its own parent, outside the authored clips.
    JumpRoot=NewObject<USceneComponent>(P,TEXT("KukriJumpPresentation"));
    P->AddInstanceComponent(JumpRoot);JumpRoot->SetupAttachment(Camera);JumpRoot->RegisterComponent();
    Viewmodel=NewObject<UKukriArmsMeshComponent>(P,TEXT("KukriViewmodel"));
    P->AddInstanceComponent(Viewmodel);Viewmodel->SetupAttachment(JumpRoot);
    // The shared sword rig faces camera forward along mesh -Y.
    Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Viewmodel->SetCanEverAffectNavigation(false);Viewmodel->SetOnlyOwnerSee(true);
    Viewmodel->SetCastShadow(false);Viewmodel->bReceivesDecals=false;
    Viewmodel->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Viewmodel->RegisterComponent();Viewmodel->SetVisibility(false,true);
    // One clock: this component samples the clip; the mesh never ticks by itself.
    Viewmodel->SetComponentTickEnabled(false);
    Blade=NewObject<UStaticMeshComponent>(P,TEXT("KukriBlade"));
    // The socket attach waits for the arms mesh (RefreshEquipment): before the first draw the viewmodel has no
    // skeletal mesh, and a socket parent would log a GetSocketInfoByName warning on every transform update.
    P->AddInstanceComponent(Blade);Blade->SetupAttachment(Viewmodel);
    Blade->SetMobility(EComponentMobility::Movable);Blade->SetOnlyOwnerSee(true);
    Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision);Blade->SetCanEverAffectNavigation(false);
    Blade->SetCastShadow(false);Blade->bReceivesDecals=false;
    // WPN_root carries the rig's 100x import scale; the mesh is authored in centimetres at the grip.
    Blade->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
    Blade->RegisterComponent();Blade->SetVisibility(false);
    // Dual kukri: the second blade rides hand_l with a constant grip; it follows the viewmodel's visibility tree and
    // is shown or hidden on its own with bHiddenInGame (UpdateOffhandBlade).
    OffhandBlade=NewObject<UStaticMeshComponent>(P,TEXT("KukriOffhandBlade"));
    P->AddInstanceComponent(OffhandBlade);OffhandBlade->SetupAttachment(Viewmodel);
    OffhandBlade->SetMobility(EComponentMobility::Movable);OffhandBlade->SetOnlyOwnerSee(true);
    OffhandBlade->SetCollisionEnabled(ECollisionEnabled::NoCollision);OffhandBlade->SetCanEverAffectNavigation(false);
    OffhandBlade->SetCastShadow(false);OffhandBlade->bReceivesDecals=false;
    OffhandBlade->SetRelativeTransform(OffhandHandToBlade());
    OffhandBlade->SetHiddenInGame(true);
    OffhandBlade->RegisterComponent();OffhandBlade->SetVisibility(false);
}

void UKukriWeaponComponent::RefreshEquipment(UColdSteelStatusModel* Profile)
{
    auto* P=Pawn();
    if(!Profile||!P||!P->IsLocallyControlled())return;
    if(!Viewmodel)InitializePresentation();
    if(!Viewmodel)return;
    // The main hand's kukri / hatchet, or -- main hand empty -- the off-hand one acting alone (left hand).
    const auto* Item=Profile->ActiveKukriWeapon();
    const FString NewId=Item&&!Profile->ActiveProductionTool()&&IsKukri(*Item)?Item->InstanceId:FString();
    const bool Lone=!NewId.IsEmpty()&&!Profile->Equipped();
    // (The lone blade's assembly lives on OffhandBlade -- RefreshOffhand; the hidden right blade carries none.)
    if(NewId==InstanceId&&Lone==bLoneOffhand){if(!NewId.IsEmpty()&&!Lone)MainModules.Refresh(Blade,Item);RefreshOffhand(Profile,true);return;}
    bPendingOffhandDraw=false;
    CancelAction();
    MainModules.Clear(Blade);OffhandModules.Clear(OffhandBlade);
    InstanceId=NewId;bHatchetChop=false;bHatchetReadyRun=false;bDualHatchet=bMainHatchet=bOffhandHatchet=false;ReadyRunPhase=0;
    // Lone off-hand blade: the right-hand clips are sampled and mirrored onto the left arm, the right arm hidden.
    bLoneOffhand=Lone;
    Viewmodel->bMirrorRightToLeft=Viewmodel->bLeftHandOnly=Lone;
    Blade->SetHiddenInGame(Lone,true);
    Viewmodel->SetVisibility(false,true);
    Viewmodel->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
    Viewmodel->ClearEntry();
    if(NewId.IsEmpty()){RefreshOffhand(Profile);return;}
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,KukriRhythm::ArmsMesh);
    auto* BladeMesh=LoadObject<UStaticMesh>(nullptr,KukriRhythm::BladeMesh);
    Animations.Reset();
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Run"),TEXT("Equip"),TEXT("Attack"),TEXT("Attack2"),TEXT("Attack3")})
    {
        const FString Name=FString(TEXT("A_Kukri_"))+Clip;
        Animations.Add(FName(Clip),LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+Name+TEXT(".")+Name)));
    }
    bool Complete=Mesh&&BladeMesh;
    for(const auto& Pair:Animations)Complete&=Pair.Value!=nullptr;
    if(!Complete)
    {
        UE_LOG(LogTemp,Error,TEXT("Kukri: viewmodel, blade or clips missing under %s; the kukri stays hidden."),KukriRhythm::Folder);
        InstanceId.Reset();return;
    }
    // Optional: without the sprint-attack clip the dash readiness never builds (ordinary swings stay available).
    Animations.Add(TEXT("SprintAttack"),LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+TEXT("A_Kukri_SprintAttack.A_Kukri_SprintAttack"))));
    // Optional: a pair's sprint attack chops down with both hands (KukriDualDashRhythm.h; without it the single chop).
    Animations.Add(TEXT("DualSprintAttack"),LoadObject<UAnimSequence>(nullptr,KukriDualDashRhythm::Clip));
    // Optional: without the pommel-strike clip F is refused for the kukri.
    // Optional: the uppercut skill (swordUppercut) reports "动作未就绪" without its clip.
    Animations.Add(TEXT("Uppercut"),LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+TEXT("A_Kukri_Uppercut.A_Kukri_Uppercut"))));
    // Optional: without both heavy clips the left button keeps its plain click (no charge); without both dual heavy clips
    // the dual kukri charges with the single ones.
    for(const FName Clip:{KukriHeavyRhythm::ChargeClip,KukriHeavyRhythm::ReleaseClip,KukriHeavyRhythm::DualChargeClip,KukriHeavyRhythm::DualReleaseClip})
    {
        const FString Name=FString(TEXT("A_Kukri_"))+Clip.ToString();
        Animations.Add(Clip,LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+Name+TEXT(".")+Name)));
    }
    if(Item->Definition==TEXT("ue_tactical_hatchet"))
        for(FName Clip:{SwiftFalconHeavy::Charge,SwiftFalconHeavy::Release,SwiftFalconHeavy::DualCharge,SwiftFalconHeavy::DualRelease})
        {
            const FString Name=TEXT("A_")+Clip.ToString();
            Animations.Add(Clip,LoadObject<UAnimSequence>(nullptr,*(TEXT("/Game/Weapons/TacticalHatchet20261101/SwiftFalconHeavy/Arms/")+Name+TEXT(".")+Name)));
        }
    Animations.Add(TEXT("QuickPommel"),LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+TEXT("A_Kukri_QuickPommel.A_Kukri_QuickPommel"))));
    // Optional: the whirlwind skill reports "动作未就绪" without its clip (checked before any cost).
    Animations.Add(TEXT("Whirlwind"),LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+TEXT("A_Kukri_Whirlwind.A_Kukri_Whirlwind"))));
    // Optional: ShadowStepSlash (瞬步掠影斩) single & dual Stage 1 / Stage 2 clips.
    for(const FName Clip:{KukriShadowStep,KukriShadowStepFollow,KukriDualShadowStep,KukriDualShadowStepFollow})
    {
        const FString Name=FString(TEXT("A_Kukri_"))+Clip.ToString();
        Animations.Add(Clip,LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+Name+TEXT(".")+Name)));
    }
    // Optional: dual kukri hold / walk / run, the two-blade first and second swings and the double thrust (a missing clip
    // falls back to the single one).
    for(const FName Clip:{KukriDualIdle,KukriDualWalk,KukriDualRun,KukriDualAttacks[0],KukriDualAttacks[1],KukriDualThrust,KukriDualEquip})
    {
        const FString Name=FString(TEXT("A_Kukri_"))+Clip.ToString();
        Animations.Add(Clip,LoadObject<UAnimSequence>(nullptr,*(FString(KukriRhythm::Folder)+Name+TEXT(".")+Name)));
    }
    // Optional: the hatchet pairs' draws and mixed stage 3 (either hand may be the hatchet, so for every kukri-family main;
    // a missing clip keeps the kukri pair's DualEquip / double thrust).
    for(const auto& Clip:{TPair<FName,const TCHAR*>(KukriHatchetDualEquip,HatchetPairRhythm::DualEquipClip),
        TPair<FName,const TCHAR*>(KukriPairEquipHK,HatchetPairRhythm::EquipHKClip),
        TPair<FName,const TCHAR*>(KukriPairEquipKH,HatchetPairRhythm::EquipKHClip),
        TPair<FName,const TCHAR*>(KukriPairAttack3HK,HatchetPairRhythm::Attack3HKClip),
        TPair<FName,const TCHAR*>(KukriPairAttack3KH,HatchetPairRhythm::Attack3KHClip)})
        Animations.Add(Clip.Key,LoadObject<UAnimSequence>(nullptr,Clip.Value));
    // Optional: the hatchet's single draw is its own vertical toss (without the clip it keeps the kukri's spinning toss).
    for(bool Axe:{false,true})
        Animations.Add(Axe?OffhandBladeDraw::Hatchet:OffhandBladeDraw::Kukri,LoadObject<UAnimSequence>(nullptr,OffhandBladeDraw::Asset(Axe)));
    if(ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("hatchet"))
    {
        Animations.Add(KukriHatchetEquip,LoadObject<UAnimSequence>(nullptr,HatchetDrawRhythm::Clip));
        // Optional too: without the chop the hatchet's third hit stays the kukri stab.
        Animations.Add(KukriHatchetAttack3,LoadObject<UAnimSequence>(nullptr,HatchetChopRhythm::Clip));
        bHatchetChop=Animations.FindRef(KukriHatchetAttack3)!=nullptr;
        // ...and with a second hatchet the double thrust is both chopping down (without the clip: the double thrust).
        Animations.Add(KukriHatchetDualAttack3,LoadObject<UAnimSequence>(nullptr,HatchetDualChopRhythm::Clip));
        // While sprinting with the sprint attack ready, the dual run becomes the raised-hatchet carry (HatchetReadyRhythm.h):
        // enter from the idle hand gesture, loop, exit.
        Animations.Add(KukriHatchetReadyEnter,LoadObject<UAnimSequence>(nullptr,HatchetReadyRhythm::EnterClip));
        Animations.Add(KukriHatchetReadyRun,LoadObject<UAnimSequence>(nullptr,HatchetReadyRhythm::Clip));
        Animations.Add(KukriHatchetReadyExit,LoadObject<UAnimSequence>(nullptr,HatchetReadyRhythm::ExitClip));
        bHatchetReadyRun=Animations.FindRef(KukriHatchetReadyEnter)&&Animations.FindRef(KukriHatchetReadyRun)&&
            Animations.FindRef(KukriHatchetReadyExit);
        ReadyRunPhase=0;
    }
    SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("swing_sound")));
    HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("hit_sound")));
    PommelHitSound=LoadObject<USoundBase>(nullptr,KukriPommelHitPath);
    WallSound=LoadObject<USoundBase>(nullptr,KukriWallPath);
    TossSound=LoadObject<USoundBase>(nullptr,KukriDrawRhythm::TossSound);
    CatchSound=LoadObject<USoundBase>(nullptr,KukriDrawRhythm::CatchSound);
    StabWhooshSound=LoadObject<USoundBase>(nullptr,KukriRhythm::StabWhoosh);
    StabThudSounds.Reset();
    for(const TCHAR* Path:KukriRhythm::StabThud)if(auto* Thud=LoadObject<USoundBase>(nullptr,Path))StabThudSounds.Add(Thud);
    if(Viewmodel->GetSkeletalMeshAsset()!=Mesh)Viewmodel->SetSkeletalMesh(Mesh);
    if(Blade->GetAttachSocketName()!=KukriWeaponSocket)
        Blade->AttachToComponent(Viewmodel,FAttachmentTransformRules::KeepRelativeTransform,KukriWeaponSocket);
    Blade->SetStaticMesh(BladeMesh);
    if(OffhandBlade->GetAttachSocketName()!=KukriOffhandSocket)
        OffhandBlade->AttachToComponent(Viewmodel,FAttachmentTransformRules::KeepRelativeTransform,KukriOffhandSocket);
    OffhandBlade->SetStaticMesh(BladeMesh);
    if(!bLoneOffhand)MainModules.Refresh(Blade,Item);
    // Equipped sleeves/gloves follow this owner-only rig (modular outfit profile by mesh path).
    Viewmodel->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    CurrentClip=NAME_None;
    OffhandInstanceId.Reset();bDual=false;RefreshOffhand(Profile);
    // A pair draws both: the left hand tosses and catches its weapon like the right, mirrored, a beat later (DualEquip; each
    // hand with its own weapon's toss when a hatchet is in the pair, DualEquipClip).
    bEquipping=true;bTossPlayed=bCatchPlayed=bOffhandTossPlayed=bOffhandCatchPlayed=false;
    const FName DualDraw=bDual?DualEquipClip():NAME_None;
    SetClip(!DualDraw.IsNone()?DualDraw:Animations.FindRef(KukriHatchetEquip)?KukriHatchetEquip:KukriEquip,false,0.f);
    UpdateOffhandDraw();
    Viewmodel->SetVisibility(CanPresent(),true);
}

void UKukriWeaponComponent::RefreshOffhand(UColdSteelStatusModel* Profile,bool DrawNewOffhand)
{
    // Dual kukri: the active set's off-hand slot (6 -> 8, 9 -> 11) also holds a kukri.  Without the dual hold clip the
    // second kukri stays an inventory item only, like an off-hand kukri beside a non-pistol weapon.
    if(bLoneOffhand)
    {
        // Lone off-hand blade: the left hand's assembly is the acting weapon itself, never a pair.
        if(const auto* Item=Profile?Profile->ActiveKukriWeapon():nullptr;Item&&Item->InstanceId==InstanceId)
            OffhandModules.Refresh(OffhandBlade,Item);
        bMainHatchet=bOffhandHatchet=bDualHatchet=false;
        OffhandInstanceId.Reset();bDual=false;
        UpdateOffhandBlade();
        return;
    }
    FString Id;const FColdSteelItem* OffhandItem=nullptr;
    if(Profile&&IsEquipped()&&Animations.FindRef(KukriDualIdle))
    {
        const int32 Main=Profile->Snapshot().ActiveWeaponSlot;
        const auto* Item=Profile->Equipped(Main==6?8:11);
        if(Item&&IsKukri(*Item)&&Item->InstanceId!=InstanceId){Id=Item->InstanceId;OffhandItem=Item;}
    }
    if(OffhandItem)OffhandModules.Refresh(OffhandBlade,OffhandItem);
    else if(!OffhandModules.ItemId.IsEmpty())OffhandModules.Clear(OffhandBlade);
    // Which hand holds a hatchet: each hand plays its own weapon's variants (the ready run follows the right hand, the
    // whirlwind's lowered left arm the off-hand hatchet, the draw and stage 3 both).
    if(const auto* Main=Profile?Profile->ActiveKukriWeapon():nullptr)
    {
        bMainHatchet=ColdSteelInventory::Text(*Main,TEXT("weaponType"))==TEXT("hatchet");
        bOffhandHatchet=OffhandItem!=nullptr&&ColdSteelInventory::Text(*OffhandItem,TEXT("weaponType"))==TEXT("hatchet");
        bDualHatchet=bMainHatchet&&bOffhandHatchet;
    }
    if(Id==OffhandInstanceId)return;
    OffhandInstanceId=Id;bDual=!Id.IsEmpty();
    if(bEquipping&&OffhandBladeDraw::IsClip(CurrentClip))
    {
        bEquipping=false;SetClip(LocomotionClip(),true,KukriRhythm::EntryBlendSeconds);UpdateOffhandDraw();
    }
    bPendingOffhandDraw=DrawNewOffhand&&bDual&&Animations.FindRef(bOffhandHatchet?OffhandBladeDraw::Hatchet:OffhandBladeDraw::Kukri);
    // Idle/walk/run switch family on the next tick (LocomotionClip); the left arm blends on its own (SetClip).
    UpdateOffhandBlade();
}

void UKukriWeaponComponent::UpdateOffhandBlade()
{
    if(!OffhandBlade)return;
    bool Show=(IsDual()||IsLoneOffhand())&&!bPendingOffhandDraw&&OffhandBlade->GetStaticMesh();
    // A consumable taken with the left hand stows the off-hand weapon for its use phase.
    if(Show)if(const auto* Potion=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>())Show=!Potion->IsOffhandWeaponHidden();
    if(OffhandBlade->bHiddenInGame==Show)OffhandBlade->SetHiddenInGame(!Show,true);
}

void UKukriWeaponComponent::UpdateDualFlip(float Delta)
{
    // The reference sprint holds the right sword in a reverse grip (SourceAssets/DualKukriIdle20261025/fit_run_r4.py):
    // DualRun is authored that way.  The right kukri turns into it with the arm's blend into the run and back out of it;
    // while a dual clip plays (or the turn is under way) the grip lock holds the turned relation.
    const bool bRun=IsDual()&&CurrentClip==KukriDualRun;
    if(bRun!=bDualTwirlIn)
    {
        // Each change of direction starts from the present orientation (a run cut short turns back from where it is).
        bDualTwirlIn=bRun;
        DualTwirlFrom=DualTwirlAngle;
        DualTwirlProgress=0.f;
    }
    DualTwirlProgress=FMath::Min(1.f,DualTwirlProgress+Delta/KukriDualRunBlendSeconds);
    const float X=DualTwirlProgress;
    DualTwirlAngle=FMath::Lerp(DualTwirlFrom,bRun?KukriDualFlipAngle:0.f,X*X*X*(X*(X*6.f-15.f)+10.f));
    // The dual draw takes the right knife out of the fist like the single draw: the lock follows the authored deviation.
    if(Viewmodel)Viewmodel->SetGripFlip(DualTwirlAngle,KukriRunFlipAxis,
        IsDual()&&((IsDualClip(CurrentClip)&&!IsDualEquipClip(CurrentClip))||DualTwirlAngle>1e-4f));
}

FName UKukriWeaponComponent::DualEquipClip() const
{
    const FName Pair=bMainHatchet?(bOffhandHatchet?KukriHatchetDualEquip:KukriPairEquipHK):
        bOffhandHatchet?KukriPairEquipKH:KukriDualEquip;
    return Animations.FindRef(Pair)?Pair:Animations.FindRef(KukriDualEquip)?KukriDualEquip:NAME_None;
}

void UKukriWeaponComponent::UpdateOffhandDraw()
{
    // While the dual draw plays the off-hand weapon flies its mirrored toss on hand_l (a hatchet its own vertical toss);
    // everywhere else it keeps the grip.
    const bool bDraw=bEquipping&&IsDualEquipClip(CurrentClip)&&CurrentAnimation;
    if(!OffhandBlade||(!bDraw&&!bOffhandDrawPose))return;
    bOffhandDrawPose=bDraw;
    OffhandBlade->SetRelativeTransform(!bDraw?OffhandHandToBlade():IsLeftHatchetDraw(CurrentClip)?
        HatchetPairRhythm::SampleLeftHatchet(Elapsed):OffhandDrawBlade(Elapsed));
}

bool UKukriWeaponComponent::CanPresent() const
{
    const auto* P=Pawn();
    const auto* PC=P?Cast<APlayerController>(P->GetController()):nullptr;
    const auto* Health=P?P->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return PC&&!P->IsTraversing()&&(!Health||!Health->IsDead())&&(!Build||!Build->IsBuilding()||Build->IsPanelOpen());
}

bool UKukriWeaponComponent::CanUse(bool bContinuing) const
{
    const auto* P=Pawn();
    const auto* PC=P?Cast<APlayerController>(P->GetController()):nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return CanPresent()&&!(bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC))&&(!Build||!Build->IsBuilding());
}

