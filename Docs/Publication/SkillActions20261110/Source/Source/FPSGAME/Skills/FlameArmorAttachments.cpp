#include "FlameArmorAttachments.h"
#include "FlameArmorSurfaceProfiles.h"
#include "HammerFireSurfaces.h"
#include "FPSElementalArrowComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSBodyWeaponMeshComponent.h"
#include "../Characters/FPSPlayerBodyPoses.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowPartComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffOffhandMeleeComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/OffhandKukriComponent.h"
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

FFlameArmorAttachment* Add(FFlameArmorAttachments& Out,USceneComponent* Source,FName Section,
    const FVector& Base,const FVector& Tip,float Size,float Opacity=1.f)
{
    if(Out.Num()>=FlameArmorAttachments::MaxLayers||!Visible(Source)||Base.ContainsNaN()||Tip.ContainsNaN()||Base.Equals(Tip,.1f))return nullptr;
    auto& Span=Out.AddDefaulted_GetRef();Span.Source=Source;Span.Section=Section;
    Span.Base=Base;Span.Tip=Tip;Span.Size=Size;Span.Opacity=Opacity;
    const FVector Axis=(Tip-Base).GetSafeNormal();
    Span.Side=FVector::VectorPlaneProject(Source->GetComponentTransform().GetUnitAxis(EAxis::X),Axis).GetSafeNormal();
    if(Span.Side.IsNearlyZero())Span.Side=FVector::VectorPlaneProject(Source->GetComponentTransform().GetUnitAxis(EAxis::Y),Axis).GetSafeNormal();
    Span.Normal=FVector::CrossProduct(Axis,Span.Side).GetSafeNormal();
    for(auto& Surface:Span.Surface)Surface=FVector4(0,0,FMath::Max(.35f,Size*2.2f),FMath::Max(.3f,Size*1.1f));
    if(const auto* Mesh=Cast<UStaticMeshComponent>(Source))Span.Geometry=Mesh->GetStaticMesh();
    else if(const auto* Skin=Cast<USkeletalMeshComponent>(Source))
    {
        Span.Geometry=Skin->GetSkeletalMeshAsset();
        Span.Socket=Skin->DoesSocketExist(Section)?Section:Skin->DoesSocketExist(TEXT("WPN_root"))?FName(TEXT("WPN_root")):NAME_None;
    }
    return &Span;
}

void StaticSpan(FFlameArmorAttachments& Out,UStaticMeshComponent* Mesh,int32 Axis,
    float From,float To,FName Section,float Size,float Opacity=1.f)
{
    if(!Visible(Mesh)||!Mesh->GetStaticMesh())return;
    const FBox Bounds=Mesh->GetStaticMesh()->GetBoundingBox();
    FVector A=Bounds.GetCenter(),B=A;
    A[Axis]=FMath::Lerp(Bounds.Min[Axis],Bounds.Max[Axis],From);
    B[Axis]=FMath::Lerp(Bounds.Min[Axis],Bounds.Max[Axis],To);
    const FTransform Frame=Mesh->GetComponentTransform();
    if(auto* Span=Add(Out,Mesh,Section,Frame.TransformPosition(A),Frame.TransformPosition(B),Size,Opacity))
    {
        const int32 Side=(Axis+1)%3,Normal=(Axis+2)%3;
        FVector S=FVector::ZeroVector,N=S;S[Side]=1;N[Normal]=1;
        Span->Side=Frame.TransformVector(S).GetSafeNormal();Span->Normal=Frame.TransformVector(N).GetSafeNormal();
        const FVector Extent=Bounds.GetExtent()*Frame.GetScale3D().GetAbs();
        for(auto& Surface:Span->Surface)Surface=FVector4(0,0,Extent[Side]+.25,Extent[Normal]+.25);
    }
}

void MeasuredSurface(FFlameArmorAttachments& Out,USceneComponent* Source,UObject* Geometry,
    const FTransform& Frame,FName Section)
{
    if(!Visible(Source)||!Geometry)return;
    // A bounded cache resolves immutable author data once per equipped geometry.
    // No runtime CPU vertex readback, asset load or per-frame path allocation.
    static TMap<TWeakObjectPtr<UObject>,const FlameArmorSurfaces::FProfile*> Profiles;
    const TWeakObjectPtr<UObject> Key=Geometry;
    const auto** Found=Profiles.Find(Key);
    if(!Found)
    {
        if(Profiles.Num()>=64)Profiles.Reset();
        const FString Path=Key->GetPathName();const FlameArmorSurfaces::FProfile* Profile=nullptr;
        for(const auto& Candidate:FlameArmorSurfaces::Profiles)if(Path==Candidate.Mesh){Profile=&Candidate;break;}
        Found=&Profiles.Add(Key,Profile);
    }
    const auto* Profile=*Found;
    if(!Profile){if(auto* Mesh=Cast<UStaticMeshComponent>(Source))StaticSpan(Out,Mesh,2,.055f,.97f,Section,.55f);return;}
    const FVector Scale=Frame.GetScale3D().GetAbs();
    const int32 Axis=Profile->Axis;
    float Width=0,Depth=0;
    for(const auto& P:Profile->Sections){Width+=P.Z*Scale[(Axis+1)%3];Depth+=P.W*Scale[(Axis+2)%3];}
    const bool Swap=Depth>Width;
    const int32 Side=(Axis+(Swap?2:1))%3,Normal=(Axis+(Swap?1:2))%3;
    FVector A=FVector::ZeroVector,B=A,S=A,N=A;A[Axis]=Profile->Start;B[Axis]=Profile->End;S[Side]=1;N[Normal]=1;
    const float Length=FVector::Distance(Frame.TransformPosition(A),Frame.TransformPosition(B));
    auto* Span=Add(Out,Source,Section,Frame.TransformPosition(A),Frame.TransformPosition(B),FMath::Clamp(Length/105.f,.36f,.78f));
    if(!Span)return;
    Span->Side=Frame.TransformVector(S).GetSafeNormal();Span->Normal=Frame.TransformVector(N).GetSafeNormal();
    for(int32 I=0;I<8;++I)
    {
        const auto& P=Profile->Sections[I];
        Span->Surface[I]=FVector4((Swap?P.Y:P.X)*Scale[Side],(Swap?P.X:P.Y)*Scale[Normal],
            (Swap?P.W:P.Z)*Scale[Side]+.25,(Swap?P.Z:P.W)*Scale[Normal]+.25);
    }
}

void BladeSurface(FFlameArmorAttachments& Out,UStaticMeshComponent* Mesh,FName Section=TEXT("BladeSurface"))
{
    if(Visible(Mesh))MeasuredSurface(Out,Mesh,Mesh->GetStaticMesh(),Mesh->GetComponentTransform(),Section);
}

bool BladeAssembly(FFlameArmorAttachments& Out,UStaticMeshComponent* Root)
{
    const int32 Before=Out.Num();
    if(Visible(Root))for(auto* Part:ColdSteelModularSword::Components(Root))
        if(Part->ComponentHasTag(TEXT("SwordSlot=blade_1")))BladeSurface(Out,Part);
    for(int32 Index=Before;Index<Out.Num();++Index)Out[Index].bSword=true;
    return Out.Num()>Before;
}

void HammerHeads(FFlameArmorAttachments& Out,UStaticMeshComponent* Mesh)
{
    if(!Visible(Mesh)||!Mesh->GetStaticMesh())return;
    const auto* Profile=HammerFireSurfaces::Find(Mesh->GetStaticMesh());
    if(!Profile)return;
    const FTransform Frame=Mesh->GetComponentTransform();
    const FVector Center(Profile->Center);
    FVector Tip=Center;Tip[Profile->Axis]+=Profile->Extent[Profile->Axis]*.7f;
    // One mesh-local system samples baked triangles on the actual installed
    // head. Curved faces and bevels no longer inherit an outer bounding plane.
    if(auto* Span=Add(Out,Mesh,TEXT("HammerSurface"),Frame.TransformPosition(Center),Frame.TransformPosition(Tip),.62f,.92f))
    {
        Span->HammerSurface=Profile;
        Span->Side=Frame.GetUnitAxis(EAxis::Z);
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
        if(!Mesh->DoesSocketExist(Hand)||!Mesh->DoesSocketExist(Finger)||Mesh->IsBoneHiddenByName(Hand))continue;
        const FVector Wrist=Mesh->GetSocketLocation(Hand),Knuckle=Mesh->GetSocketLocation(Finger);
        if(auto* Span=Add(Out,Mesh,Hand,FMath::Lerp(Wrist,Knuckle,.2f),Knuckle,.36f,.72f))
        {
            // A barrel-sized default radius buried the copied flame inside
            // the palm. Fit its ring to the current finger-root width instead.
            const FName IndexRoot=Side?TEXT("index_01_l"):TEXT("index_01_r");
            const FName PinkyRoot=Side?TEXT("pinky_01_l"):TEXT("pinky_01_r");
            float HalfWidth=2.6f;
            if(Mesh->DoesSocketExist(IndexRoot)&&Mesh->DoesSocketExist(PinkyRoot))
            {
                const FVector Across=FVector::VectorPlaneProject(Mesh->GetSocketLocation(IndexRoot)-Mesh->GetSocketLocation(PinkyRoot),(Knuckle-Wrist).GetSafeNormal());
                if(!Across.IsNearlyZero())
                {
                    Span->Side=Across.GetSafeNormal();
                    Span->Normal=FVector::CrossProduct((Knuckle-Wrist).GetSafeNormal(),Span->Side).GetSafeNormal();
                    HalfWidth=FMath::Clamp(float(Across.Size())*.5f+.7f,2.2f,4.f);
                }
            }
            for(auto& Surface:Span->Surface)Surface=FVector4(0,0,HalfWidth,FMath::Max(1.7f,HalfWidth*.65f));
        }
    }
}

void BowArrow(FFlameArmorAttachments& Out,UBowPartComponent* Arrow)
{
    // Bow fire belongs to the actual arrow, including taking and nocking it.
    // The released projectile keeps its existing independent local-space FX.
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
    // The prepared fire arrow already carries the same warm flame structure.
    if(const auto* Element=GetOwner()->FindComponentByClass<UFPSElementalArrowComponent>();Element&&Element->ShotElement()==EArrowElement::Fire)return;
    if(IsEquipped())BowArrow(Out,Part(SlotArrow));
}

void URuneSwordComponent::GetFlameArmorAttachments(FFlameArmorAttachmentBuffer& Out) const
{
    if(!IsEquipped()||BladeAssembly(Out,ModularSword))return;
    USceneComponent* Parent=nullptr;FName Socket;FTransform Local;float Length=0;
    if(GetEnchantmentBladeAttachment(Parent,Socket,Local,Length)&&Parent)
    {
        const FTransform Frame=Local*Parent->GetSocketTransform(Socket);
        if(auto* Span=Add(Out,Parent,TEXT("SwordEdge"),Frame.GetLocation(),Frame.GetLocation()+Frame.GetUnitAxis(EAxis::X)*Length,FMath::Clamp(Length/110.f,.45f,.8f)))
        {Span->bSword=true;Span->Socket=Socket;}
    }
}

void UProductionToolComponent::GetFlameArmorAttachments(FFlameArmorAttachmentBuffer& Out) const
{
    if(!IsEquipped())return;
    if(Kind==TEXT("shovel"))
    {
        if(bUsesArms&&Visible(Viewmodel)&&Viewmodel->DoesSocketExist(TEXT("WPN_root")))
            MeasuredSurface(Out,Viewmodel,Viewmodel->GetSkeletalMeshAsset(),Viewmodel->GetSocketTransform(TEXT("WPN_root")),TEXT("ToolEdge"));
        else BladeSurface(Out,ToolMesh,TEXT("ToolEdge"));
        return;
    }
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
        if(auto* Span=Add(Out,Parent,TEXT("ToolEdge"),World.GetLocation(),World.GetLocation()+World.GetUnitAxis(EAxis::X)*Length,.45f))Span->Socket=Socket;
    }
}

void UFPSPlayerBodyComponent::GetFlameArmorAttachments(FFlameArmorAttachmentBuffer& Out) const
{
    if(IsDeathViewActive()||!Visible(GetBodyMesh()))return;
    uint8 Occupied=0,GunHands=0;
    for(const auto& Motion:MotionBindings)
    {
        const auto& Definition=Motion.Definition;Occupied|=1<<FMath::Min<int32>(Definition.AttachHand,1);
        if(Definition.PoseFamily==TEXT("Bow"))
        {
            if(DisplayState.BowMagic==uint8(EArrowElement::Fire))continue;
            UBowPartComponent* Arrow=nullptr;
            for(const auto& Part:WorldBowParts)if(Part&&Part->SlotName==TEXT("arrow")){Arrow=Part;break;}
            BowArrow(Out,Arrow);continue;
        }
        auto* Mesh=Motion.Mesh.Get();
        if(Definition.PoseFamily==TEXT("Gun"))
        {
            if(!Mesh||IsWorldWeaponStowed(Mesh))continue;
            // World gun meshes do not render the hands. Use the posed body,
            // with one hand per paired gun and both hands for a single grip.
            GunHands|=(!Definition.bGunPistol||MotionBindings.Num()==1)?3:uint8(1<<FMath::Min<int32>(Definition.AttachHand,1));
        }
        else if(Definition.PoseFamily==TEXT("Staff"))
        {if(auto* Root=Motion.Static.Get();Root&&!IsWorldWeaponStowed(Root))Staff(Out,Root);}
        else if(Definition.PoseFamily==TEXT("Kukri")||Definition.PoseFamily==TEXT("KukriDual")||
            Definition.PoseFamily==TEXT("OffhandKukri")||Definition.PoseFamily==TEXT("Shovel"))
        {
            if(auto* Root=Motion.Static.Get();Root&&!IsWorldWeaponStowed(Root))BladeSurface(Out,Root);
        }
        else if(Definition.PoseFamily==TEXT("Sword")||Definition.PoseFamily==TEXT("Tool"))
        {
            if(!Mesh||IsWorldWeaponStowed(Mesh))continue;
            const int32 Before=Out.Num();
            for(const auto& Weak:Motion.Parts)if(auto* Part=Weak.Get())
            {
                if(Part->ComponentHasTag(TEXT("SwordSlot=hammer_heads")))HammerHeads(Out,Part);
                else if(Part->ComponentHasTag(TEXT("SwordSlot=blade_1")))BladeSurface(Out,Part);
            }
            if(Out.Num()==Before&&Definition.PoseFamily==TEXT("Sword"))
            {FVector Base,Tip;if(ReferenceBlade(Mesh,Base,Tip))Add(Out,Mesh,TEXT("SwordEdge"),Base,Tip,.7f);}
            else if(Out.Num()==Before&&Definition.PoseFamily==TEXT("Tool")&&DisplayState.Weapon==TEXT("shovel")&&Mesh->DoesSocketExist(TEXT("WPN_root")))
                MeasuredSurface(Out,Mesh,Mesh->GetSkeletalMeshAsset(),Mesh->GetSocketTransform(TEXT("WPN_root")),TEXT("ToolEdge"));
            else if(Out.Num()==Before&&Definition.PoseFamily==TEXT("Tool")&&Mesh->DoesSocketExist(TEXT("WPN_root"))
                &&FVector::DistSquared(Definition.ToolEdgeBase,Definition.ToolEdgeTip)>UE_SMALL_NUMBER)
            {
                const auto Frame=Mesh->GetSocketTransform(TEXT("WPN_root"));
                Add(Out,Mesh,TEXT("ToolEdge"),Frame.TransformPosition(Definition.ToolEdgeBase),Frame.TransformPosition(Definition.ToolEdgeTip),.45f);
            }
            if(Definition.PoseFamily==TEXT("Sword"))for(int32 Index=Before;Index<Out.Num();++Index)Out[Index].bSword=true;
        }
    }
    if(DisplayState.Family==TEXT("Unarmed"))GunHands|=3&~Occupied;
    if(GunHands)Hands(Out,GetBodyMesh(),GunHands);
    for(auto& Span:Out)Span.EquipmentIdentity=GetTypeHash(DisplayState.WeaponInstance)^GetTypeHash(DisplayState.OffhandInstance);
}

void FlameArmorAttachments::Gather(AFPSGAMECharacter* Player,FFlameArmorAttachments& Out)
{
    if(!Player)return;
    const auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Player->IsLocallyControlled()||(Body&&Body->IsThirdPersonViewEnabled()))
    {if(Body)Body->GetFlameArmorAttachments(Out);return;}
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsEquipped())
        Sword->GetFlameArmorAttachments(Out);
    else if(auto* Knife=Player->FindComponentByClass<UKukriWeaponComponent>();Knife&&Knife->IsEquipped())
    {
        if(!Knife->IsLoneOffhand())BladeSurface(Out,Knife->WeaponMesh());
        if(Knife->IsDual()||Knife->IsLoneOffhand())BladeSurface(Out,Knife->WeaponMesh(true));
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
        {
            const auto& Hand=Dual->Hand(Side);
            Hands(Out,Hand.Mesh,Dual->IsTwoHandedLone()?3:uint8(1<<Side));
        }
    }
    else if(Player->HasInventoryWeapon())
    {
        const auto* Offhand=Player->FindComponentByClass<UOffhandKukriComponent>();
        const auto* Book=Player->FindComponentByClass<USpellbookComponent>();
        const bool OtherLeft=(Offhand&&Offhand->OwnsLeftHand())||(Book&&Book->OwnsLeftHand());
        Hands(Out,Player->AKMViewmodel,OtherLeft?1:3);
    }
    if(auto* Knife=Player->FindComponentByClass<UOffhandKukriComponent>();Knife&&Knife->OwnsLeftHand())
        BladeSurface(Out,Knife->WeaponMesh());
    if(auto* Pair=Player->FindComponentByClass<UStaffOffhandMeleeComponent>();Pair&&Pair->OwnsLeftHand())
        BladeSurface(Out,Pair->WeaponMesh());
    uint32 Identity=GetTypeHash(Player->ActiveInventoryWeapon);
    if(const auto* Dual=Player->FindComponentByClass<UPistolDualWieldComponent>();Dual&&Dual->IsActive())Identity^=GetTypeHash(Dual->Hand(1).Item.InstanceId);
    for(auto& Span:Out)Span.EquipmentIdentity=Identity;
    // An optical scope can suppress a still-ticking viewmodel using owner flags.
    Out.RemoveAll([](const FFlameArmorAttachment& S){const auto* P=Cast<UPrimitiveComponent>(S.Source.Get());return P&&P->bOwnerNoSee;});
}
