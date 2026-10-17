#include "FlameArmorAttachments.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSBodyWeaponMeshComponent.h"
#include "../Characters/FPSPlayerBodyPoses.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/FPSWeaponFXComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowPartComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"

namespace
{
bool Visible(const USceneComponent* Component)
{
    // Collision capsules are hidden primitives, but their children can render.
    // Equipment controllers already propagate their own stow/visibility gates.
    return IsValid(Component)&&Component->IsRegistered()&&Component->IsVisible()&&!Component->bHiddenInGame;
}

void Add(FFlameArmorAttachments& Out,USceneComponent* Source,FName Section,
    const FVector& Base,const FVector& Tip,float Size,float Opacity=1.f)
{
    if(Out.Num()>=FlameArmorAttachments::MaxLayers||!Visible(Source)||Base.ContainsNaN()||Tip.ContainsNaN()||Base.Equals(Tip,.1f))return;
    auto& Span=Out.AddDefaulted_GetRef();Span.Source=Source;Span.Section=Section;
    Span.Base=Base;Span.Tip=Tip;Span.Size=Size;Span.Opacity=Opacity;
    if(const auto* Mesh=Cast<UStaticMeshComponent>(Source))Span.Geometry=Mesh->GetStaticMesh();
    else if(const auto* Skin=Cast<USkeletalMeshComponent>(Source))Span.Geometry=Skin->GetSkeletalMeshAsset();
}

void StaticSpan(FFlameArmorAttachments& Out,UStaticMeshComponent* Mesh,int32 Axis,
    float From,float To,FName Section,float Size,float Opacity=1.f)
{
    if(!Visible(Mesh)||!Mesh->GetStaticMesh())return;
    const FBox Bounds=Mesh->GetStaticMesh()->GetBoundingBox();
    FVector A=Bounds.GetCenter(),B=A;
    A[Axis]=FMath::Lerp(Bounds.Min[Axis],Bounds.Max[Axis],From);
    B[Axis]=FMath::Lerp(Bounds.Min[Axis],Bounds.Max[Axis],To);
    Add(Out,Mesh,Section,Mesh->GetComponentTransform().TransformPosition(A),Mesh->GetComponentTransform().TransformPosition(B),Size,Opacity);
}

void HammerHeads(FFlameArmorAttachments& Out,UStaticMeshComponent* Mesh)
{
    if(!Visible(Mesh)||!Mesh->GetStaticMesh())return;
    const FBox Bounds=Mesh->GetStaticMesh()->GetBoundingBox();
    const FVector Extent=Bounds.GetExtent();
    const int32 Axis=Extent.X>Extent.Y?0:1;
    const int32 FaceAxis=1-Axis;
    const FTransform Frame=Mesh->GetComponentTransform();
    // The solid heads are 8-14 cm thick; a center-line emitter buries the
    // depth-tested heat and flame roots inside metal. Place both lobes on both
    // broad faces, outside the shader's maximum 2.66 cm radial spawn offset.
    // Sample the installed module bounds so replacement heads use their own
    // dimensions, and transform every endpoint with the current animated head.
    const double Clearance=3.2/FMath::Max(FMath::Abs(Frame.GetScale3D()[FaceAxis]),.01);
    for(int32 Face=0;Face<2;++Face)
    {
        const double Surface=Face?Bounds.Max[FaceAxis]+Clearance:Bounds.Min[FaceAxis]-Clearance;
        const auto FaceSpan=[&](float From,float To,FName Section)
        {
            FVector A=Bounds.GetCenter(),B=A;
            A[Axis]=FMath::Lerp(Bounds.Min[Axis],Bounds.Max[Axis],From);
            B[Axis]=FMath::Lerp(Bounds.Min[Axis],Bounds.Max[Axis],To);
            A[FaceAxis]=B[FaceAxis]=Surface;
            Add(Out,Mesh,Section,Frame.TransformPosition(A),Frame.TransformPosition(B),.62f,.85f);
        };
        FaceSpan(.03f,.38f,Face?TEXT("HammerLeftBack"):TEXT("HammerLeft"));
        FaceSpan(.62f,.97f,Face?TEXT("HammerRightBack"):TEXT("HammerRight"));
    }
}

void Staff(FFlameArmorAttachments& Out,UStaticMeshComponent* Root)
{
    // Staff assembly pieces share the authored shaft coordinates. Keep the
    // grip and lower shaft clear; the existing crystal remains visible.
    StaticSpan(Out,Root,2,.56f,.86f,TEXT("StaffShaft"),.38f,.65f);
    if(!Visible(Root)||!Root->GetStaticMesh())return;
    UStaticMeshComponent* Head=Root;
    double Highest=Root->GetStaticMesh()->GetBoundingBox().Max.Z;
    for(const auto& Child:Root->GetAttachChildren())if(auto* Part=Cast<UStaticMeshComponent>(Child);Visible(Part)&&Part->GetStaticMesh())
    {
        const FBox InStaff=Part->GetStaticMesh()->GetBoundingBox().TransformBy(Part->GetComponentTransform().GetRelativeTransform(Root->GetComponentTransform()));
        if(InStaff.Max.Z>Highest){Head=Part;Highest=InStaff.Max.Z;}
    }
    StaticSpan(Out,Head,2,Head==Root?.87f:.15f,1.f,TEXT("StaffCrown"),.52f,.8f);
}

void Hands(FFlameArmorAttachments& Out,USkeletalMeshComponent* Mesh,uint8 FreeHands)
{
    if(!Visible(Mesh))return;
    for(int32 Side=0;Side<2;++Side)
    {
        if(!(FreeHands&(1<<Side)))continue;
        const FName Hand=Side?TEXT("hand_l"):TEXT("hand_r");
        const FName Finger=Side?TEXT("middle_02_l"):TEXT("middle_02_r");
        if(!Mesh->DoesSocketExist(Hand)||!Mesh->DoesSocketExist(Finger))continue;
        const FVector Wrist=Mesh->GetSocketLocation(Hand),Knuckle=Mesh->GetSocketLocation(Finger);
        Add(Out,Mesh,Hand,FMath::Lerp(Wrist,Knuckle,.2f),Knuckle,.28f,.72f);
    }
}

void Gun(FFlameArmorAttachments& Out,USkeletalMeshComponent* Mesh,const FTransform& Muzzle,bool Pistol,float Aim)
{
    if(!Visible(Mesh))return;
    const FVector Tip=Muzzle.GetLocation(),Forward=Muzzle.GetUnitAxis(EAxis::X);
    const float GripDistance=Mesh->DoesSocketExist(TEXT("hand_r"))?FVector::Distance(Tip,Mesh->GetSocketLocation(TEXT("hand_r"))):45.f;
    const float Length=FMath::Clamp(GripDistance*.72f,Pistol?12.f:26.f,Pistol?27.f:62.f);
    // Burn along the barrel/fore-end, below the sight line, and stop before the
    // actual muzzle (including suppressors). No aim/camera fallback positions.
    const FVector Under=Muzzle.GetUnitAxis(EAxis::Z)*-2.f;
    Add(Out,Mesh,TEXT("GunBarrel"),Tip-Forward*Length+Under,Tip-Forward*3.f+Under,
        Pistol?.32f:.48f,FMath::Lerp(.8f,.28f,FMath::Clamp(Aim,0.f,1.f)));
}

void Bow(FFlameArmorAttachments& Out,UBowPartComponent* Riser,UBowPartComponent* Arrow,FVector Upper,FVector Lower)
{
    if(!Visible(Riser)||!Riser->IsPartVisible())return;
    Riser->FlexTips(Upper,Lower);
    const FTransform Frame=Riser->GetComponentTransform();
    // The tips already contain the current string-load deformation. Leave a
    // clear gap at the grip and arrow rest, rather than burning the bowstring.
    Add(Out,Riser,TEXT("BowUpper"),Frame.TransformPosition(FVector(0,0,12)),Frame.TransformPosition(Upper*.94),.35f,.62f);
    Add(Out,Riser,TEXT("BowLower"),Frame.TransformPosition(FVector(0,0,-12)),Frame.TransformPosition(Lower*.94),.35f,.62f);
    if(Visible(Arrow)&&Arrow->IsPartVisible())
        if(auto* Rod=Arrow->RodVisual(0);Visible(Rod)&&Rod->GetStaticMesh())
        {
            const auto Extent=Rod->GetStaticMesh()->GetBounds().BoxExtent;
            // Sample the actual posed arrow, including taking/nocking it. Fire
            // is restricted to the tip end, away from fingers and fletching.
            StaticSpan(Out,Rod,Extent.X>Extent.Z?0:2,.83f,.98f,TEXT("NockedArrow"),.22f,.55f);
        }
}

bool ReferenceBlade(USkeletalMeshComponent* Mesh,FVector& Base,FVector& Tip)
{
    if(!Visible(Mesh)||!Mesh->GetSkeletalMeshAsset()||!Mesh->DoesSocketExist(TEXT("WPN_root")))return false;
    struct FEndpoints {FVector Base,Tip;bool bValid=false;};
    static TMap<TWeakObjectPtr<USkeletalMesh>,FEndpoints> Cache;
    const TWeakObjectPtr<USkeletalMesh> Key=Mesh->GetSkeletalMeshAsset();
    auto* Endpoints=Cache.Find(Key);
    if(!Endpoints)
    {
        if(Cache.Num()>=32)Cache.Reset();
        auto& Entry=Cache.Add(Key);const auto& Ref=Key->GetRefSkeleton();
        const int32 Root=Ref.FindBoneIndex(TEXT("WPN_root")),A=Ref.FindBoneIndex(TEXT("Blade_Base")),B=Ref.FindBoneIndex(TEXT("Blade_Tip"));
        if(Root>=0&&A>=0&&B>=0)
        {
            const auto Pose=[&](int32 Bone){FTransform T=Ref.GetRefBonePose()[Bone];for(int32 P=Ref.GetParentIndex(Bone);P>=0;P=Ref.GetParentIndex(P))T=T*Ref.GetRefBonePose()[P];return T;};
            const FTransform Mount=Pose(Root);
            Entry.Base=Mount.InverseTransformPosition(Pose(A).GetLocation());Entry.Tip=Mount.InverseTransformPosition(Pose(B).GetLocation());Entry.bValid=true;
        }
        Endpoints=&Entry;
    }
    if(!Endpoints->bValid)return false;
    const FTransform Frame=Mesh->GetSocketTransform(TEXT("WPN_root"));
    Base=Frame.TransformPosition(Endpoints->Base);Tip=Frame.TransformPosition(Endpoints->Tip);return true;
}
}

void UBowWeaponComponent::GetFlameArmorAttachments(FFlameArmorAttachmentBuffer& Out) const
{
    if(IsEquipped())Bow(Out,Part(SlotRiser),Part(SlotArrow),UpperTipCM,LowerTipCM);
}

void UProductionToolComponent::GetFlameArmorAttachments(FFlameArmorAttachmentBuffer& Out) const
{
    if(!IsEquipped())return;
    if(Kind==TEXT("warhammer"))
    {
        for(auto* Part:ColdSteelModularSword::Components(ToolMesh))
            if(Part->ComponentHasTag(TEXT("SwordSlot=hammer_heads"))){HammerHeads(Out,Part);return;}
        return;
    }
    USceneComponent* Parent=nullptr;FName Socket;FTransform Local;float Length=0;
    if(GetEnchantmentBladeAttachment(Parent,Socket,Local,Length)&&Parent)
    {
        const FTransform World=Local*Parent->GetSocketTransform(Socket);
        Add(Out,Parent,TEXT("ToolEdge"),World.GetLocation(),World.GetLocation()+World.GetUnitAxis(EAxis::X)*Length,.45f);
    }
}

void UFPSPlayerBodyComponent::GetFlameArmorAttachments(FFlameArmorAttachmentBuffer& Out) const
{
    if(IsDeathViewActive()||!Visible(GetBodyMesh()))return;
    uint8 Occupied=0;
    for(const auto& Motion:MotionBindings)
    {
        const auto& Definition=Motion.Definition;Occupied|=1<<FMath::Min<int32>(Definition.AttachHand,1);
        if(Definition.PoseFamily==TEXT("Bow"))
        {
            UBowPartComponent* Riser=nullptr;UBowPartComponent* Arrow=nullptr;
            for(const auto& Part:WorldBowParts)if(Part){if(Part->SlotName==TEXT("riser"))Riser=Part;if(Part->SlotName==TEXT("arrow"))Arrow=Part;}
            Bow(Out,Riser,Arrow,BowSettings.UpperTip,BowSettings.LowerTip);continue;
        }
        auto* Mesh=Motion.Mesh.Get();
        if(Definition.PoseFamily==TEXT("Gun"))
        {
            if(!Mesh||IsWorldWeaponStowed(Mesh))continue;
            // Owner F6 bodies intentionally have no remote gun-FX component.
            // Both views use the already-replicated native muzzle frame.
            FTransform Muzzle=Definition.GunMuzzleInRoot*Mesh->GetSocketTransform(TEXT("WPN_root"));
            if(Motion.Parts.IsValidIndex(Definition.MuzzlePart))if(auto* Part=Motion.Parts[Definition.MuzzlePart].Get())
            {
                const FVector Axis=Part->GetComponentTransform().TransformVectorNoScale(Definition.MuzzleAxis).GetSafeNormal();
                Muzzle.SetLocation(Part->GetComponentTransform().TransformPosition(Definition.MuzzleTip));
                Muzzle.SetRotation(FRotationMatrix::MakeFromXZ(Axis,Muzzle.GetUnitAxis(EAxis::Z)).ToQuat());
            }
            Gun(Out,Mesh,Muzzle,Definition.bGunPistol,DisplayState.bAiming?1.f:0.f);
        }
        else if(Definition.PoseFamily==TEXT("Staff"))
        {if(auto* Root=Motion.Static.Get();Root&&!IsWorldWeaponStowed(Root))Staff(Out,Root);}
        else if(Definition.PoseFamily==TEXT("Sword")||Definition.PoseFamily==TEXT("Tool"))
        {
            if(!Mesh||IsWorldWeaponStowed(Mesh))continue;
            const int32 Before=Out.Num();
            for(const auto& Weak:Motion.Parts)if(auto* Part=Weak.Get())
            {
                if(Part->ComponentHasTag(TEXT("SwordSlot=hammer_heads")))HammerHeads(Out,Part);
                else if(Part->ComponentHasTag(TEXT("SwordSlot=blade_1")))StaticSpan(Out,Part,2,.06f,.97f,TEXT("SwordEdge"),.7f);
            }
            if(Out.Num()==Before&&Definition.PoseFamily==TEXT("Sword"))
            {FVector Base,Tip;if(ReferenceBlade(Mesh,Base,Tip))Add(Out,Mesh,TEXT("SwordEdge"),Base,Tip,.7f);}
            else if(Out.Num()==Before&&Definition.PoseFamily==TEXT("Tool")&&Mesh->DoesSocketExist(TEXT("WPN_root"))
                &&FVector::DistSquared(Definition.ToolEdgeBase,Definition.ToolEdgeTip)>UE_SMALL_NUMBER)
            {
                const auto Frame=Mesh->GetSocketTransform(TEXT("WPN_root"));
                Add(Out,Mesh,TEXT("ToolEdge"),Frame.TransformPosition(Definition.ToolEdgeBase),Frame.TransformPosition(Definition.ToolEdgeTip),.45f);
            }
        }
    }
    if(DisplayState.Family==TEXT("Unarmed"))Hands(Out,GetBodyMesh(),3&~Occupied);
    for(auto& Span:Out)Span.EquipmentIdentity=GetTypeHash(DisplayState.WeaponInstance)^GetTypeHash(DisplayState.OffhandInstance);
}

void FlameArmorAttachments::Gather(AFPSGAMECharacter* Player,FFlameArmorAttachments& Out)
{
    if(!Player)return;
    const auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Player->IsLocallyControlled()||(Body&&Body->IsThirdPersonViewEnabled()))
    {if(Body)Body->GetFlameArmorAttachments(Out);return;}
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsEquipped())
    {
        USceneComponent* Parent=nullptr;FName Socket;FTransform Local;float Length=0;
        if(Sword->GetEnchantmentBladeAttachment(Parent,Socket,Local,Length)&&Parent)
        {
            const FTransform Frame=Local*Parent->GetSocketTransform(Socket);
            Add(Out,Parent,TEXT("SwordEdge"),Frame.GetLocation(),Frame.GetLocation()+Frame.GetUnitAxis(EAxis::X)*Length,FMath::Clamp(Length/110.f,.45f,.8f));
        }
    }
    else if(auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();Tool&&Tool->IsEquipped())Tool->GetFlameArmorAttachments(Out);
    else if(auto* BowComponent=Player->FindComponentByClass<UBowWeaponComponent>();BowComponent&&BowComponent->IsEquipped())BowComponent->GetFlameArmorAttachments(Out);
    else if(auto* StaffComponent=Player->FindComponentByClass<UStaffWeaponComponent>();StaffComponent&&StaffComponent->IsEquipped())Staff(Out,StaffComponent->AssemblyRoot());
    else if(auto* Empty=Player->FindComponentByClass<UFPSUnarmedIdleComponent>();Empty&&Empty->IsEquipped())
    {
        const auto* Book=Player->FindComponentByClass<USpellbookComponent>();
        Hands(Out,Empty->ArmsMesh(),Book&&Book->IsEquipped()?1:3);
    }
    if(auto* Dual=Player->FindComponentByClass<UPistolDualWieldComponent>();Dual&&Dual->IsActive())
    {
        for(int32 Side=Dual->IsOffhandOnly()?1:0;Side<2;++Side)
        {const auto& Hand=Dual->Hand(Side);if(Hand.FX)Gun(Out,Hand.Mesh,Hand.FX->ShotTransform(),true,0.f);}
    }
    else if(Player->HasInventoryWeapon())Gun(Out,Player->AKMViewmodel,Player->GetEffectiveMuzzleTransform(),Player->IsPistolWeapon(),Player->IsAiming()?1.f:0.f);
    uint32 Identity=GetTypeHash(Player->ActiveInventoryWeapon);
    if(const auto* Dual=Player->FindComponentByClass<UPistolDualWieldComponent>();Dual&&Dual->IsActive())Identity^=GetTypeHash(Dual->Hand(1).Item.InstanceId);
    for(auto& Span:Out)Span.EquipmentIdentity=Identity;
    // An optical scope can suppress a still-ticking viewmodel using owner flags.
    Out.RemoveAll([](const FFlameArmorAttachment& S){const auto* P=Cast<UPrimitiveComponent>(S.Source.Get());return P&&P->bOwnerNoSee;});
}
