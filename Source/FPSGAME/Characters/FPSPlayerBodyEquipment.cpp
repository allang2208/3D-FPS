#include "FPSPlayerBodyComponent.h"
#include "FPSModularOutfitComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "FPSBodyRuneVisual.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Weapons/FPSGunplayAnimInstance.h"
#include "../Weapons/WeaponGripProfile.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "../Weapons/TubeShotgunAssets.h"
#include "../Weapons/WeaponPresentationMaterials.h"
#include "../Weapons/TacticalDeviceComponent.h"
#include "../Weapons/TacticalDeviceVariants.h"
#include "../Weapons/FPSWeaponFXComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "../Weapons/SwordTasselMeshComponent.h"
#include "../Weapons/Staff/StaffGripPose.h"
#include "../Weapons/Unarmed/FPSUnarmedHandPose.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Spellbook/SpellbookAuthoredGrip.h"
#include "FPSBodyStaffGrip.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Crc.h"

namespace FPSBodyEquipment
{
/** Applies owner-visibility flags only where they differ from the current value.
 *
 *  SetOnlyOwnerSee/SetOwnerNoSee/SetCastShadow each mark the primitive's render
 *  state dirty, which on a skeletal body or a viewmodel part costs a render-state
 *  recreate plus shadow-scene re-registration. The body component re-asserts the
 *  same flags on every camera update, so re-applying them unconditionally turned a
 *  one-off setup into continuous render-thread churn.
 */
void ApplyOwnerVisibilityFlags(UPrimitiveComponent* Mesh,bool bOnlyOwnerSee,bool bOwnerNoSee)
{
    if(!Mesh)return;
    // No short-circuit: each flag is independent and each change must be seen.
    const bool bOnlyChanged=Mesh->bOnlyOwnerSee!=bOnlyOwnerSee;
    const bool bOwnerChanged=Mesh->bOwnerNoSee!=bOwnerNoSee;
    if(bOnlyChanged)Mesh->SetOnlyOwnerSee(bOnlyOwnerSee);
    if(bOwnerChanged)Mesh->SetOwnerNoSee(bOwnerNoSee);
    // Count changed fields in this instrumented path, not calls or render-state recreates.
    if(bOnlyChanged||bOwnerChanged)
        UFPSPerformanceMetricsSubsystem::CountVisibilityFlagChange(Mesh,
            static_cast<int32>(bOnlyChanged)+static_cast<int32>(bOwnerChanged));
}
void ApplyShadowFlags(UPrimitiveComponent* Mesh,bool bCastShadow)
{
    if(!Mesh)return;
    const bool bCastChanged=Mesh->CastShadow!=bCastShadow;
    const bool bHiddenChanged=Mesh->bCastHiddenShadow!=bCastShadow;
    if(bCastChanged)Mesh->SetCastShadow(bCastShadow);
    if(bHiddenChanged)Mesh->SetCastHiddenShadow(bCastShadow);
    if(bCastChanged||bHiddenChanged)
        UFPSPerformanceMetricsSubsystem::CountVisibilityFlagChange(Mesh,
            static_cast<int32>(bCastChanged)+static_cast<int32>(bHiddenChanged));
}
static UMaterialInterface* PersistentMaterial(UMaterialInterface* Material)
{
    while(auto* Dynamic=Cast<UMaterialInstanceDynamic>(Material))Material=Dynamic->Parent;
    return Material;
}
static void WorldVisibility(UPrimitiveComponent* Mesh)
{
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetGenerateOverlapEvents(false);
    const auto* Body=Mesh->GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    ApplyOwnerVisibilityFlags(Mesh,/*bOnlyOwnerSee=*/false,/*bOwnerNoSee=*/!Body||!Body->IsThirdPersonViewEnabled());
    // Final shadow/visibility policy is applied after the equipment's hand is registered.
}
static FVector JsonVector(const TSharedPtr<FJsonObject>& Obj,const TCHAR* Key,FVector Default)
{
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    if(!Obj||!Obj->TryGetArrayField(Key,Values)||Values->Num()<3)return Default;
    return FVector((*Values)[0]->AsNumber(),(*Values)[1]->AsNumber(),(*Values)[2]->AsNumber());
}
static TSharedPtr<FJsonObject> OutfitDefinitions()
{
    // Static equipment bindings are content data; reload only once per process.
    static TSharedPtr<FJsonObject> Definitions;
    static bool bLoaded=false;
    if(bLoaded)return Definitions;
    bLoaded=true;
    FString Json;
    if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json"))))return Definitions;
    TSharedPtr<FJsonObject> Root;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root)return Definitions;
    const TSharedPtr<FJsonObject>* Outfits=nullptr;
    if(Root->TryGetObjectField(TEXT("outfits"),Outfits))Definitions=*Outfits;
    return Definitions;
}
FSoftObjectPath StaticOutfitMesh(const FString& Definition)
{
    const auto Definitions=OutfitDefinitions();
    if(!Definitions.IsValid())return FSoftObjectPath();
    const TSharedPtr<FJsonObject>* Settings=nullptr;
    if(!Definitions->TryGetObjectField(Definition,Settings))return FSoftObjectPath();
    FString Path;
    if(!(*Settings)->TryGetStringField(TEXT("world_static_mesh"),Path))return FSoftObjectPath();
    return FSoftObjectPath(Path);
}
}

FFPSBodyWeapon UFPSPlayerBodyComponent::CaptureWeapon(USkeletalMeshComponent* Source,UAnimSequence* Idle,FName Grip) const
{
    FFPSBodyWeapon Result;if(!Source||!Source->GetSkeletalMeshAsset())return Result;
    auto* Asset=Source->GetSkeletalMeshAsset();Result.Mesh=Asset;Result.HoldClip=Idle;Result.GripBone=Grip;
    Result.Source=Source;
    const auto& Ref=Asset->GetRefSkeleton();
    for(int32 B=0;B<Ref.GetNum()&&Result.MotionBones.Num()<512;++B)
    {
        const FString N=Ref.GetBoneName(B).ToString().ToLower();bool Arm=false;
        for(const TCHAR* Prefix:{TEXT("clavicle"),TEXT("upperarm"),TEXT("lowerarm"),TEXT("hand_"),TEXT("thumb"),TEXT("index"),TEXT("middle"),TEXT("ring"),TEXT("pinky"),TEXT("ik_hand")})Arm|=N.StartsWith(Prefix);
        if(!Arm)Result.MotionBones.Add(B);
    }
    if(const auto* Gun=Cast<UFPSGunplayAnimInstance>(Source->GetAnimInstance()))
    {
        Result.PoseFamily=TEXT("Gun");
        Result.HoldClip=Gun->bGripIdle&&Gun->GripIdleFamily?Gun->GripIdleFamily.Get():(Gun->IdleClip?Gun->IdleClip.Get():Idle);
    }
    const bool bSuper90=Asset->GetPathName()==Super90WeaponAssets::MeshPath;
    for(int32 I=0;I<Asset->GetMaterials().Num();++I)
    {
        Result.Materials.Add(FPSBodyEquipment::PersistentMaterial(Source->GetMaterial(I)));
        const auto& NativeMaterial=Asset->GetMaterials()[I];
        const FName Slot=NativeMaterial.MaterialSlotName;
        // Reload cartridge visibility is carried by the motion section mask.
        // Only arms and intentionally replaced factory parts stay hidden.
        // Use the authored material as well as the display slot: slot labels can
        // change during mesh edits, and equipped clothing can override Source's
        // material. The native skin section remains absent from the world copy.
        if(WeaponPresentationMaterials::IsArmSection(NativeMaterial))
            Result.HiddenMaterials.Add(I);
        if((Slot==TEXT("M870_FactoryFurniture")||Slot==TEXT("M870_FactoryTubeCap"))
            &&!Source->IsMaterialSectionShown(I,0))Result.HiddenMaterials.AddUnique(I);
        if(bSuper90&&(Slot==TEXT("S90_FactoryRearGrip")||Slot.ToString().StartsWith(TEXT("S90_FactoryStock_"))
            ||Slot.ToString().StartsWith(TEXT("S90_FactoryTubeCap_")))&&!Source->IsMaterialSectionShown(I,0))
            Result.HiddenMaterials.AddUnique(I);
        if(Slot==TEXT("M_SteelWarhammerSurface")&&!Source->IsMaterialSectionShown(I,0))
            Result.HiddenMaterials.AddUnique(I);
    }
    TArray<USceneComponent*> Children;Source->GetChildrenComponents(true,Children);
    for(auto* Child:Children)if(auto* Prop=Cast<USkeletalMeshComponent>(Child);
        Prop&&Prop->ComponentHasTag(TEXT("WeaponReloadProp")))
    {
        Result.ReloadPropMesh=Prop->GetSkeletalMeshAsset();Result.ReloadPropSource=Prop;
        for(int32 M=0;M<Prop->GetNumMaterials();++M)
            Result.ReloadPropMaterials.Add(FPSBodyEquipment::PersistentMaterial(Prop->GetMaterial(M)));
        break;
    }
    TInlineComponentArray<UTacticalDeviceComponent*> TacticalDevices(Source->GetOwner());
    const auto* RuneProfile=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* RuneTool=RuneProfile?RuneProfile->ActiveProductionTool():nullptr;
    const auto* RuneItem=RuneTool?RuneTool:RuneProfile?RuneProfile->Equipped():nullptr;
    for(auto* Child:Children)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->GetStaticMesh()&&Result.Parts.Num()<64)
    {
        FFPSBodyAttachment Entry;Entry.Mesh=Part->GetStaticMesh();
        // A hidden first-person carrier still owns installed warhammer modules.
        // World fallback poses must not capture that temporary hidden state.
        Entry.bVisible=Part->ComponentHasTag(TEXT("WarhammerModule"))||(Part->IsVisible()&&!Part->bHiddenInGame);
        Entry.RelativeTransform=Part->GetRelativeTransform();
        USceneComponent* Branch=Part;
        while(Branch->GetAttachParent()&&Branch->GetAttachParent()!=Source)
        {Branch=Branch->GetAttachParent();Entry.RelativeTransform=Entry.RelativeTransform*Branch->GetRelativeTransform();}
        Entry.Socket=Branch->GetAttachSocketName();
        for(int32 I=0;I<Part->GetNumMaterials();++I)Entry.Materials.Add(FPSBodyEquipment::PersistentMaterial(Part->GetMaterial(I)));
        FPSBodyRuneVisual::Capture(Part,RuneItem,Entry);
        if(Character.IsValid()&&Source==Character->AKMViewmodel&&Part==Character->MuzzleAttachment
            &&!Character->MuzzleVariant.IsEmpty())
        {
            Result.MuzzlePart=Result.Parts.Num();Result.MuzzleTip=Character->MuzzleLocalTip;
            Result.MuzzleAxis=Character->MuzzleLocalAxis;
        }
        TWeakObjectPtr<UTacticalDeviceComponent> TacticalSource;
        for(auto* Device:TacticalDevices)
            if(Device->DescribePart(Part,Entry.TacticalKind,Entry.bAuthoredEmitterAxis))
            {TacticalSource=Device;break;}
        Result.SourceTacticalDevices.Add(TacticalSource);
        Result.Parts.Add(MoveTemp(Entry));
        Result.SourceParts.Add(Part);
    }
    return Result;
}
void UFPSPlayerBodyComponent::CaptureEquipment()
{
    UFPSPerformanceMetricsSubsystem::CountEquipmentCapture(this);
    FFPSPerformanceScope PerformanceScope(this,TEXT("PlayerBody.EquipmentCapture"));
    const auto* Pawn=Character.Get();TArray<FFPSBodyWeapon> Weapons;
    if(Pawn->IsDualWieldingPistols())
    {
        for(int32 I=0;I<2;++I)
        {
            const auto& Hand=Pawn->DualPistols->Hand(I);
            // Both imported pistol rigs use the right-hand grip; the world instance attaches to the chosen body hand.
            Weapons.Add(CaptureWeapon(Hand.Mesh,Hand.Clips.FindRef(TEXT("idle")),TEXT("hand_r")));
            Weapons.Last().AttachHand=I;
            Weapons.Last().GripProfile=Hand.PoseProfiles.FindRef(TEXT("base"));
        }
    }
    else if(Pawn->HasInventoryWeapon())
    {
        Weapons.Add(CaptureWeapon(Pawn->AKMViewmodel,Pawn->IdleAnimation,TEXT("hand_r")));
        Weapons.Last().GripProfile=Pawn->WeaponGripProfileFor(Pawn->ResolveRifleGripProfile());
    }
    else if(const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsEquipped())
    {
        Weapons.Add(CaptureWeapon(Sword->Viewmodel,Sword->Animations.FindRef(TEXT("Idle")),TEXT("hand_r")));
        Weapons.Last().PoseFamily=TEXT("Sword");
        if(const auto* Arms=Cast<URuneSwordMeshComponent>(Sword->Viewmodel))Weapons.Last().GripProfile=Arms->GetGripProfile();
    }
    else if(const auto* Bow=Pawn->FindComponentByClass<UBowWeaponComponent>();Bow&&Bow->IsEquipped())
    {
        FFPSBodyWeapon Entry;CaptureBow(*Bow,Entry);Weapons.Add(MoveTemp(Entry));
    }
    else if(const auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>();Staff&&Staff->IsEquipped()&&Staff->AssemblyRoot()&&Staff->AssemblyRoot()->GetStaticMesh())
    {
        FFPSBodyWeapon Entry;const auto* Root=Staff->AssemblyRoot();Entry.StaticMesh=Root->GetStaticMesh();
        FQuat HandBasis=FQuat::Identity;
        if(const auto* Body=GetBodyMesh();Body&&Body->GetSkeletalMeshAsset())
        {const auto& Ref=Body->GetSkeletalMeshAsset()->GetRefSkeleton();FTransform Hand=FTransform::Identity;
            for(int32 B=Ref.FindBoneIndex(TEXT("hand_r"));B!=INDEX_NONE;B=Ref.GetParentIndex(B))Hand=Hand*Ref.GetRefBonePose()[B];HandBasis=Hand.GetRotation();}
        const FQuat StaffRotation=HandBasis.Inverse()*FRotator(0,90,0).Quaternion();
        Entry.StaticGrip=FTransform(StaffRotation,-StaffRotation.RotateVector(StaffGripPose::HoldPoint()));
        Entry.PoseFamily=TEXT("Staff");Entry.StaffVariant=Staff->GripVariant();
        Entry.StaticSource=Staff->AssemblyRoot();Entry.Source=Staff->ArmsMesh();
        if(Staff->CrystalLight)Entry.StaffLightLocation=Staff->CrystalLight->GetRelativeLocation();
        if(const auto* Arms=Staff->ArmsMesh())Entry.Mesh=Arms->GetSkeletalMeshAsset();
        for(auto* C:ColdSteelStaffAssembly::Components(Staff->AssemblyRoot()))
        {
            if(C==Root){for(auto* M:C->GetMaterials())Entry.Materials.Add(FPSBodyEquipment::PersistentMaterial(M));continue;}
            FFPSBodyAttachment Part;Part.Mesh=C->GetStaticMesh();Part.RelativeTransform=C->GetRelativeTransform();
            Part.bVisible=C->IsVisible()&&!C->bHiddenInGame;
            for(auto* M:C->GetMaterials())Part.Materials.Add(FPSBodyEquipment::PersistentMaterial(M));Entry.Parts.Add(MoveTemp(Part));
            Entry.SourceParts.Add(C);
        }
        Weapons.Add(MoveTemp(Entry));
        if(Pawn->HasOffhandPistol())
        {
            const auto& Hand=Pawn->DualPistols->Hand(1);
            Weapons.Add(CaptureWeapon(Hand.Mesh,Hand.Clips.FindRef(TEXT("idle")),TEXT("hand_r")));
            Weapons.Last().AttachHand=1;Weapons.Last().GripProfile=Hand.PoseProfiles.FindRef(TEXT("base"));
        }
    }
    else if(const auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool&&Tool->IsEquipped())
    {
        if(Tool->bUsesArms)
        {Weapons.Add(CaptureWeapon(Tool->Viewmodel,Tool->Motions.FindRef(TEXT("Idle")),TEXT("hand_r")));Weapons.Last().PoseFamily=TEXT("Tool");}
        else if(Tool->ToolMesh&&Tool->ToolMesh->GetStaticMesh())
        {
            FFPSBodyWeapon Entry;Entry.StaticMesh=Tool->ToolMesh->GetStaticMesh();
            // Preserve the tool's authored mount and scale. Convert its camera
            // basis into Manny's +Y facing basis, relative to the hand bind frame.
            FQuat HandBasis=FQuat::Identity;
            if(const auto* Body=GetBodyMesh();Body&&Body->GetSkeletalMeshAsset())
            {
                const auto& Ref=Body->GetSkeletalMeshAsset()->GetRefSkeleton();
                FTransform Hand=FTransform::Identity;
                for(int32 Bone=Ref.FindBoneIndex(TEXT("hand_r"));Bone!=INDEX_NONE;Bone=Ref.GetParentIndex(Bone))
                    Hand=Hand*Ref.GetRefBonePose()[Bone];
                HandBasis=Hand.GetRotation();
            }
            Entry.StaticGrip=FTransform(HandBasis.Inverse()*FRotator(0,90,0).Quaternion()*Tool->ToolMesh->GetRelativeRotation().Quaternion(),
                FVector::ZeroVector,Tool->ToolMesh->GetRelativeScale3D());
            Entry.PoseFamily=TEXT("Shovel");
            // Reuse the accepted two-handed harvesting grip, then fit it to
            // this mesh's measured shaft instead of gripping the mesh origin.
            Entry.Mesh=FSoftObjectPath(TEXT("/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe.SK_Harvest_Axe"));
            Entry.HoldClip=FSoftObjectPath(TEXT("/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle.A_Harvest_Axe_Idle"));
            for(int32 I=0;I<Tool->ToolMesh->GetNumMaterials();++I)
                Entry.Materials.Add(FPSBodyEquipment::PersistentMaterial(Tool->ToolMesh->GetMaterial(I)));
            Weapons.Add(MoveTemp(Entry));
        }
    }
    const auto* Spellbook=Pawn->FindComponentByClass<USpellbookComponent>();
    const auto* RemoteProfile=Pawn->GetNetShadowProfile();
    if(RemoteProfile&&RemoteProfile->ActiveSpellbook()&&!RemoteProfile->ActiveProductionTool())
    {
        // A remote/dedicated pawn does not load or equip the owner-only hand rig.
        // Publish the same asset identity/schema from authoritative equipment.
        FFPSBodyWeapon Entry;
        Entry.StaticMesh=TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Weapons/SpellbookEvildeer20261009/Meshes/SM_Spellbook_Alchemy_Closed.SM_Spellbook_Alchemy_Closed")));
        Entry.Mesh=TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7")));
        Entry.GripBone=TEXT("hand_l");Entry.AttachHand=1;Entry.PoseFamily=TEXT("Spellbook");Entry.StaticGrip=SpellbookAuthoredGrip::BookInHand;
        Weapons.Add(MoveTemp(Entry));
    }
    else if(Spellbook&&Spellbook->IsEquipped())
    {
        const auto* Book=Spellbook->BookMesh();auto* Arms=Spellbook->ArmsMesh();
        if(Book&&Book->GetStaticMesh()&&Arms&&Arms->GetSkeletalMeshAsset())
        {
            FFPSBodyWeapon Entry;Entry.StaticMesh=Book->GetStaticMesh();Entry.Mesh=Arms->GetSkeletalMeshAsset();
            Entry.StaticSource=Spellbook->BookMesh();Entry.Source=Arms;Entry.GripBone=TEXT("hand_l");
            Entry.AttachHand=1;Entry.PoseFamily=TEXT("Spellbook");Entry.StaticGrip=SpellbookAuthoredGrip::BookInHand;
            for(int32 M=0;M<Book->GetNumMaterials();++M)Entry.Materials.Add(FPSBodyEquipment::PersistentMaterial(Book->GetMaterial(M)));
            Weapons.Add(MoveTemp(Entry));
        }
    }
    for(auto& W:Weapons)
    {
        DescribeGun(W);
        FString Schema=W.Mesh.ToSoftObjectPath().ToString()+W.StaticMesh.ToSoftObjectPath().ToString()+W.GripBone.ToString();
        for(int32 B:W.MotionBones)Schema+=FString::Printf(TEXT("|%d"),B);
        for(const auto& P:W.Parts)Schema+=TEXT("|")+P.Mesh.ToSoftObjectPath().ToString()+P.Socket.ToString()+P.TacticalKind.ToString();
        if(!W.ReloadPropMesh.IsNull())Schema+=TEXT("|")+W.ReloadPropMesh.ToSoftObjectPath().ToString();
        W.MotionSchema=FCrc::StrCrc32(*Schema);
    }
    FString Key=DisplayState.Weapon.ToString();
    for(const auto& W:Weapons)
    {
        Key+=TEXT("|")+W.Mesh.ToSoftObjectPath().ToString()+TEXT("|")+W.HoldClip.ToSoftObjectPath().ToString();
        Key+=TEXT("|")+W.StaticMesh.ToSoftObjectPath().ToString()+TEXT("|")+W.StaticGrip.ToString();
        Key+=TEXT("|")+W.GripProfile.ToSoftObjectPath().ToString()+FString::Printf(TEXT("|%s:%d:%d"),*W.PoseFamily.ToString(),W.AttachHand,W.StaffVariant);
        Key+=TEXT("|")+W.ReloadPropMesh.ToSoftObjectPath().ToString();
        Key+=TEXT("|")+W.GunInstance+W.GunDefinition.ToString();
        Key+=W.GunFireSound.ToSoftObjectPath().ToString()+W.GunSuppressedSound.ToSoftObjectPath().ToString();
        Key+=W.bGunSuppressed?TEXT("|suppressed"):TEXT("|open");
        for(const auto& Sound:W.GunSounds)Key+=TEXT("|")+Sound.ToSoftObjectPath().ToString();
        for(const auto& Material:W.ReloadPropMaterials)Key+=TEXT("|")+Material.ToSoftObjectPath().ToString();
        if(W.MuzzlePart!=INDEX_NONE)Key+=FString::Printf(TEXT("|exit:%d|%s|%s"),W.MuzzlePart,*W.MuzzleTip.ToString(),*W.MuzzleAxis.ToString());
        // Discard cached fitted mounts/palm poses when this source-sharing
        // implementation replaces the old third-person-only grip table.
        if(W.PoseFamily==TEXT("Staff"))Key+=TEXT("|StaffFromFirstPerson20261009|UnarmedFreeHand20261009|StaffSurfaceFit20261009");
        for(const auto& Clip:W.MotionClips)Key+=TEXT("|")+Clip.Role.ToString()+Clip.Sequence.ToSoftObjectPath().ToString();
        if(W.PoseFamily==TEXT("Bow"))Key+=TEXT("|")+W.Bow.UpperTip.ToString()+W.Bow.LowerTip.ToString()+W.Bow.Brace.ToString()+W.Bow.ArrowRest.ToString()
            +FString::Printf(TEXT("|%.6f:%.6f:%.6f:%.6f"),W.Bow.StringRadius,W.Bow.ArrowRadius,W.Bow.ArrowLength,W.Bow.FlexDistribution);
        for(const int32 Hidden:W.HiddenMaterials)Key+=FString::Printf(TEXT("#%d"),Hidden);
        for(const auto& Material:W.Materials)Key+=TEXT("|")+Material.ToSoftObjectPath().ToString();
        for(const auto& Part:W.Parts)
        {
            Key+=TEXT("|")+Part.Mesh.ToSoftObjectPath().ToString();
            Key+=TEXT("|")+Part.TacticalKind.ToString()+(Part.bAuthoredEmitterAxis?TEXT("|axis-authored"):TEXT("|axis-sight"));
            if(Part.Mesh.ToSoftObjectPath().GetAssetName().Contains(TEXT("Stock")))Key+=Part.bVisible?TEXT("|stock-on"):TEXT("|stock-off");
            if(!W.Source.IsValid())Key+=TEXT("|")+Part.RelativeTransform.ToString();
            Key+=TEXT("|")+Part.SkeletalMesh.ToSoftObjectPath().ToString()+Part.Slot.ToString()+TEXT("|")+Part.Socket.ToString();
            for(const auto& Material:Part.Materials)Key+=TEXT("|")+Material.ToSoftObjectPath().ToString();
            Key+=FPSBodyRuneVisual::Key(Part);
        }
    }
    if(EquipmentKey!=Key)
    {
        EquipmentKey=Key;LocalWeapons=Weapons;
        if(GetOwner()->HasAuthority())ReplicatedWeapons=Weapons;
        if(GetNetMode()!=NM_DedicatedServer)RebuildWeapons(Weapons);
        bOutfitDirty=true;
    }
    else LocalWeapons=Weapons; // refresh weak source instances without rebuilding render assets
    // 联机：远端 pawn 的装备来源是影子档案（GetNetShadowProfile），不是主机单例。
    UColdSteelStatusModel* OutfitProfile=Pawn->GetNetShadowProfile();
    if(!OutfitProfile&&Pawn->IsLocallyControlled()&&Pawn->GetGameInstance())OutfitProfile=Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(OutfitProfile)RefreshAppearance(OutfitProfile);
    if(OutfitProfile)
    {
        TArray<FFPSBodyOutfitSlot> Next;
        for(const auto& Item:OutfitProfile->Items())if(Item.Place==1&&Item.Cell!=6&&Item.Cell!=8&&Item.Cell!=9&&Item.Cell!=11)
        {FFPSBodyOutfitSlot Entry;Entry.Slot=Item.Cell;Entry.Definition=FName(*Item.Definition);Next.Add(Entry);}
        Next.Sort([](const auto& A,const auto& B){return A.Slot<B.Slot;});
        bool Changed=Next.Num()!=LocalOutfit.Num();
        if(!Changed)for(int32 I=0;I<Next.Num();++I)
            if(Next[I].Slot!=LocalOutfit[I].Slot||Next[I].Definition!=LocalOutfit[I].Definition){Changed=true;break;}
        if(Changed||bOutfitDirty)
        {
            LocalOutfit=MoveTemp(Next);
            if(GetOwner()->HasAuthority()){ReplicatedOutfit=LocalOutfit;GetOwner()->ForceNetUpdate();}
            if(GetNetMode()!=NM_DedicatedServer)ApplyOutfit(LocalOutfit);
        }
        bOutfitDirty=false;
    }
}
void UFPSPlayerBodyComponent::RebuildWeapons(const TArray<FFPSBodyWeapon>& Weapons)
{
    auto* Body=GetBodyMesh();if(!Body)return;
    if(FPSPlayerBodyWorldBodySuppressed())return;
    UFPSPerformanceMetricsSubsystem::CountEquipmentRebuild(this);
    for(auto Device:WorldTacticalDevices)if(Device)Device->DestroyComponent();WorldTacticalDevices.Reset();
    ClearGunPresentation();
    for(auto Part:WorldParts)if(Part)Part->DestroyComponent();WorldParts.Reset();
    for(auto Prop:WorldReloadProps)if(Prop)Prop->DestroyComponent();WorldReloadProps.Reset();
    for(auto Weapon:WorldWeapons)if(Weapon)Weapon->DestroyComponent();WorldWeapons.Reset();
    WorldEquipmentHands.Reset();
    MotionBindings.Reset();MotionMaps.Reset();MotionEquipmentIndices.Reset();
    // New equipment must not interpolate from the preceding gun's support hand.
    SmoothedContacts=FFPSBodyMotionSample();bMotionSampleValid=false;
    if(WorldStaffLight){WorldStaffLight->DestroyComponent();WorldStaffLight=nullptr;}WorldStaffMaterials.Reset();LastWorldLight=-1.f;
    ClearBow();
    if(BodyAnimation){BodyAnimation->bHasLeftGrip=false;BodyAnimation->RifleHold=FFPSBodyRifleHold();BodyAnimation->EquipmentGripHands=0;BodyAnimation->SpellbookEquipmentIndex=INDEX_NONE;BodyAnimation->EquipmentFingers.Reset();BodyAnimation->bBowPose=false;}
    for(int32 Index=0;Index<Weapons.Num();++Index)
    {
        const auto& Definition=Weapons[Index];
        auto& Motion=MotionBindings.AddDefaulted_GetRef();Motion.Definition=Definition;
        const int32 Side=FMath::Min<int32>(Definition.AttachHand,1);
        const FName BodyHand=Side==1?TEXT("hand_l"):TEXT("hand_r");
        if(auto* Static=Definition.StaticMesh.LoadSynchronous())
        {
            auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Part);Part->SetStaticMesh(Static);
            Part->SetupAttachment(Body,BodyHand);Part->SetRelativeTransform(Definition.StaticGrip);
            if(Definition.PoseFamily==TEXT("Shovel"))BuildShovelGrip(Definition,*Part);
            if(Definition.PoseFamily==TEXT("Spellbook"))if(auto* Native=Definition.Mesh.LoadSynchronous();Native&&BodyAnimation)
            {
                const auto& Ref=Native->GetRefSkeleton();auto Pose=Ref.GetRefBonePose();
                for(const auto& Finger:SpellbookAuthoredGrip::Fingers)
                    if(const int32 I=Ref.FindBoneIndex(Finger.Name);I>=0)Pose[I].SetRotation(Finger.Rotation.GetNormalized());
                for(int32 I=0;I<Pose.Num();++I)if(Ref.GetParentIndex(I)>=0)Pose[I]=Pose[I]*Pose[Ref.GetParentIndex(I)];
                FFPSBodyGripRig Grip;Grip.Initialize(Ref,Body->GetSkeletalMeshAsset()->GetRefSkeleton(),TEXT("hand_l"),BodyHand);
                if(Grip.IsValid())
                {
                    Grip.Transfer(Pose,BodyAnimation->EquipmentFingers);BodyAnimation->EquipmentGripHands|=1<<Side;
                    Part->SetRelativeTransform(SpellbookAuthoredGrip::BookInHand*Grip.Mount);
                    BodyAnimation->SpellbookEquipmentIndex=Index;
                }
            }
            WorldEquipmentHands.Add(Part,static_cast<uint8>(Side));
            if(Definition.PoseFamily==TEXT("Staff"))if(auto* Native=Definition.Mesh.LoadSynchronous();Native&&BodyAnimation)
            {
                const auto& Ref=Native->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
                for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)>=0)Bind[I]=Bind[I]*Bind[Ref.GetParentIndex(I)];
                const auto& Hold=StaffGripPose::Get(Native,Bind,Definition.StaffVariant);
                auto Pose=Hold.Local[0];
                for(int32 I=0;I<Pose.Num();++I)if(Ref.GetParentIndex(I)>=0)Pose[I]=Pose[I]*Pose[Ref.GetParentIndex(I)];
                FFPSBodyGripRig Grip;Grip.Initialize(Ref,Body->GetSkeletalMeshAsset()->GetRefSkeleton(),TEXT("hand_r"),BodyHand);
                if(Grip.IsValid())
                {
                    FPSBodyStaffGrip::AdaptMount(Grip,Definition.StaffVariant);
                    if(!FPSBodyStaffGrip::Transfer(Grip,Ref,Pose,BodyAnimation->EquipmentFingers,Definition.StaffVariant))
                        Grip.Transfer(Pose,BodyAnimation->EquipmentFingers);
                    BodyAnimation->EquipmentGripHands|=1<<Side;
                    Part->SetRelativeTransform(FTransform(-StaffGripPose::HoldPoint())*Hold.HandInGrip.Inverse()*Grip.Mount);
                    BodyAnimation->StaffHandRotation=(Grip.Mount.Inverse()*Pose[Grip.SourceHand]*FTransform(FRotator(0,90,0))).GetRotation();
                }
                const bool HasOffhand=Weapons.ContainsByPredicate([](const FFPSBodyWeapon& Weapon){return Weapon.AttachHand==1;});
                if(!HasOffhand&&FPSUnarmedHandPose::Build(Ref,TEXT("hand_l"),Pose))
                {
                    FFPSBodyGripRig FreeHand;
                    FreeHand.Initialize(Ref,Body->GetSkeletalMeshAsset()->GetRefSkeleton(),TEXT("hand_l"),TEXT("hand_l"));
                    // Reuse the complete FPS fist, including its thumb and palm
                    // fan. Only finger descendants are applied: the native
                    // unarmed walk/run still owns shoulder, elbow and wrist.
                    if(FPSBodyStaffGrip::Transfer(FreeHand,Ref,Pose,BodyAnimation->EquipmentFingers))
                        BodyAnimation->EquipmentGripHands|=2;
                }
            }
            FPSBodyEquipment::WorldVisibility(Part);
            for(int32 I=0;I<Definition.Materials.Num();++I)if(auto* Material=Definition.Materials[I].LoadSynchronous())Part->SetMaterial(I,Material);
            Part->RegisterComponent();WorldParts.Add(Part);
            Motion.Static=Part;
            MotionEquipmentIndices.Add(Part,Index);
            for(const auto& Attachment:Definition.Parts)if(auto* ChildMesh=Attachment.Mesh.LoadSynchronous())
            {
                const auto TailSpec=Definition.PoseFamily==TEXT("Staff")?ColdSteelStaffAssembly::TailDynamics(ChildMesh):nullptr;
                UStaticMeshComponent* Child=TailSpec?NewObject<USwordTasselMeshComponent>(GetOwner(),NAME_None,RF_Transient):NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
                GetOwner()->AddInstanceComponent(Child);
                Child->SetStaticMesh(ChildMesh);Child->SetupAttachment(Part);Child->SetRelativeTransform(Attachment.RelativeTransform);
                WorldEquipmentHands.Add(Child,static_cast<uint8>(Side));FPSBodyEquipment::WorldVisibility(Child);
                for(int32 I=0;I<Attachment.Materials.Num();++I)if(auto* M=Attachment.Materials[I].LoadSynchronous())Child->SetMaterial(I,M);
                Child->RegisterComponent();WorldParts.Add(Child);
                if(auto* Tail=Cast<USwordTasselMeshComponent>(Child))
                {
                    Tail->Configure(TailSpec);
                    Tail->AddTickPrerequisiteComponent(this);
                    Tail->AddTickPrerequisiteComponent(Body);
                }
                Motion.Parts.Add(Child);
                MotionEquipmentIndices.Add(Child,Index);
            }
            if(Definition.PoseFamily==TEXT("Staff"))
            {
                TArray<UStaticMeshComponent*> Pieces={Part};for(const auto& Weak:Motion.Parts)if(Weak.IsValid())Pieces.Add(Weak.Get());
                for(auto* Piece:Pieces)for(int32 M=0;M<Piece->GetNumMaterials();++M)
                {
                    auto* Material=Piece->GetMaterial(M);float Value=0.f;
                    if(Material&&Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("StaffLightAmount")),Value))
                        if(auto* Dynamic=Piece->CreateDynamicMaterialInstance(M))WorldStaffMaterials.Add(Dynamic);
                }
                if(!WorldStaffMaterials.IsEmpty())
                {
                    WorldStaffLight=NewObject<UPointLightComponent>(GetOwner(),NAME_None,RF_Transient);GetOwner()->AddInstanceComponent(WorldStaffLight);
                    WorldStaffLight->SetupAttachment(Part);WorldStaffLight->SetRelativeLocation(Definition.StaffLightLocation);
                    WorldStaffLight->SetIntensityUnits(ELightUnits::Lumens);WorldStaffLight->SetInverseExposureBlend(1.f);
                    WorldStaffLight->SetAttenuationRadius(800.f);WorldStaffLight->SetSourceRadius(3.f);WorldStaffLight->SetSoftSourceRadius(5.f);
                    WorldStaffLight->SetLightColor(FLinearColor(1.f,.94f,.82f));WorldStaffLight->SetCastShadows(true);
                    WorldStaffLight->SetIntensity(0.f);WorldStaffLight->SetVisibility(false);WorldStaffLight->RegisterComponent();
                }
            }
            continue;
        }
        auto* Asset=Definition.Mesh.LoadSynchronous();if(!Asset)continue;
        auto* Weapon=NewObject<UFPSBodyWeaponMeshComponent>(GetOwner(),NAME_None,RF_Transient);
        Weapon->GripProfile=Definition.GripProfile.LoadSynchronous();
        GetOwner()->AddInstanceComponent(Weapon);Weapon->SetSkeletalMeshAsset(Asset);
        Weapon->SetupAttachment(Body,BodyHand);
        WorldEquipmentHands.Add(Weapon,static_cast<uint8>(Side));
        FPSBodyEquipment::WorldVisibility(Weapon);Weapon->RegisterComponent();
        Weapon->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        if(auto* Hold=Definition.HoldClip.LoadSynchronous())
        {Weapon->PlayAnimation(Hold,false);Weapon->SetPosition(0.f,false);Weapon->SetPlayRate(0.f);Weapon->TickAnimation(0.f,false);}
        Weapon->RefreshBoneTransforms();
        FTransform Grip=Weapon->GetSocketTransform(Definition.GripBone,RTS_Component);
        // Imported viewmodel hand bones can carry scale 100. Their component-space
        // locations are already centimetres; invert only the rigid grip transform.
        Grip.SetScale3D(FVector::OneVector);
        Weapon->SetRelativeTransform(Grip.Inverse()*HandRigOffsets[Index==1?1:0]);
        FFPSBodyGripRig FingerRigs[2];
        if(BodyAnimation&&(Definition.PoseFamily==TEXT("Gun")||Definition.PoseFamily==TEXT("Tool")||Definition.PoseFamily==TEXT("Sword")))
        {
            FingerRigs[Side].Initialize(Asset->GetRefSkeleton(),Body->GetSkeletalMeshAsset()->GetRefSkeleton(),Definition.GripBone,BodyHand);
            FingerRigs[Side].Transfer(Weapon->GetComponentSpaceTransforms(),BodyAnimation->EquipmentFingers);
            if(FingerRigs[Side].IsValid())
            {BodyAnimation->EquipmentGripHands|=1<<Side;Weapon->SetRelativeTransform(Grip.Inverse()*FingerRigs[Side].Mount);}
        }
        for(int32 I=0;I<Definition.Materials.Num();++I)if(auto* Material=Definition.Materials[I].LoadSynchronous())Weapon->SetMaterial(I,Material);
        if(const auto* Render=Asset->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 Material=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                const bool ParkedShell=TubeShotgunAssets::MatchesMesh(Asset->GetPathName())
                    &&Asset->GetMaterials()[Material].MaterialSlotName==Super90WeaponAssets::LooseShellMaterial;
                Weapon->ShowMaterialSection(Material,S,!Definition.HiddenMaterials.Contains(Material)&&!ParkedShell,L);
            }
        Weapon->SetComponentTickEnabled(false);WorldWeapons.Add(Weapon);
        Motion.Mesh=Weapon;Motion.FrozenPose=Weapon->GetComponentSpaceTransforms();
        if(auto* PropAsset=Definition.ReloadPropMesh.LoadSynchronous())
        {
            auto* Prop=NewObject<USkeletalMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Prop);Prop->SetSkeletalMeshAsset(PropAsset);
            Prop->SetupAttachment(Weapon);FPSBodyEquipment::WorldVisibility(Prop);
            for(int32 M=0;M<Definition.ReloadPropMaterials.Num();++M)
                if(auto* Material=Definition.ReloadPropMaterials[M].LoadSynchronous())Prop->SetMaterial(M,Material);
            Prop->bUseAttachParentBound=true;Prop->SetLeaderPoseComponent(Weapon);
            Prop->RegisterComponent();Prop->SetVisibility(false);
            WorldReloadProps.Add(Prop);WorldEquipmentHands.Add(Prop,static_cast<uint8>(Side));Motion.ReloadProp=Prop;
        }
        Motion.NativeWeaponRoot=Asset->GetRefSkeleton().FindBoneIndex(TEXT("WPN_root"));
        if(Definition.PoseFamily!=TEXT("Bow"))MotionEquipmentIndices.Add(Weapon,Index);
        if(Definition.PoseFamily==TEXT("Bow")){BuildBow(Definition,Weapon);continue;}
        if(Index==0&&Weapons.Num()==1&&BodyAnimation&&Weapon->DoesSocketExist(TEXT("hand_l")))
        {
            FTransform LeftGrip=Weapon->GetSocketTransform(TEXT("hand_l"),RTS_Component);
            LeftGrip.SetScale3D(FVector::OneVector);
            BodyAnimation->LeftGripFromRight=HandRigOffsets[1].Inverse()*LeftGrip.GetRelativeTransform(Grip)*HandRigOffsets[0];
            BodyAnimation->bHasLeftGrip=true;
            if(Definition.PoseFamily==TEXT("Gun")||Definition.PoseFamily==TEXT("Tool")||Definition.PoseFamily==TEXT("Sword"))
            {
                FingerRigs[1].Initialize(Asset->GetRefSkeleton(),Body->GetSkeletalMeshAsset()->GetRefSkeleton(),TEXT("hand_l"),TEXT("hand_l"));
                FingerRigs[1].Transfer(Weapon->GetComponentSpaceTransforms(),BodyAnimation->EquipmentFingers);
                if(FingerRigs[1].IsValid())
                {
                    BodyAnimation->EquipmentGripHands|=2;
                    BodyAnimation->LeftGripFromRight=FingerRigs[1].Mount.Inverse()*LeftGrip.GetRelativeTransform(Grip)*FingerRigs[0].Mount;
                }
            }
        }
        for(int32 PartIndex=0;PartIndex<Definition.Parts.Num();++PartIndex)
        {
            const auto& DefinitionPart=Definition.Parts[PartIndex];
            auto* AssetPart=DefinitionPart.Mesh.LoadSynchronous();if(!AssetPart)continue;
            auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Part);Part->SetStaticMesh(AssetPart);
            Part->SetupAttachment(Weapon);
            Part->SetRelativeTransform(DefinitionPart.Socket.IsNone()?DefinitionPart.RelativeTransform
                :DefinitionPart.RelativeTransform*Weapon->GetSocketTransform(DefinitionPart.Socket,RTS_Component));
            WorldEquipmentHands.Add(Part,static_cast<uint8>(Side));
            FPSBodyEquipment::WorldVisibility(Part);
            for(int32 I=0;I<DefinitionPart.Materials.Num();++I)if(auto* Material=DefinitionPart.Materials[I].LoadSynchronous())Part->SetMaterial(I,Material);
            FPSBodyRuneVisual::Apply(Part,DefinitionPart);
            Part->RegisterComponent();WorldParts.Add(Part);
            Motion.Parts.Add(Part);
            MotionEquipmentIndices.Add(Part,Index);
            if(!Character->IsLocallyControlled()&&(TacticalDeviceVariants::IsLaser(DefinitionPart.TacticalKind.ToString())
                ||(Definition.GunDefinition==TEXT("ue_super90")&&DefinitionPart.TacticalKind==TEXT("flashlight"))))
            {
                auto* Device=NewObject<UTacticalDeviceComponent>(GetOwner(),NAME_None,RF_Transient);
                GetOwner()->AddInstanceComponent(Device);Device->RegisterComponent();
                Device->ConfigureWorld(DefinitionPart.TacticalKind.ToString(),Weapon,Part,
                    DefinitionPart.bAuthoredEmitterAxis,Index,PartIndex,Definition.MotionSchema);
                WorldTacticalDevices.Add(Device);
            }
        }
        BuildGunPresentation(Definition,Weapon);
        if(Index==0&&Weapons.Num()==1&&BodyAnimation)BodyAnimation->RifleHold=BuildFPSBodyRifleHold(*Weapon,Definition);
    }
    for(auto& Binding:MotionBindings)
    {
        if(Binding.Mesh.IsValid())Binding.Mount=Binding.Mesh->GetRelativeTransform();
        else if(Binding.Static.IsValid())Binding.Mount=Binding.Static->GetRelativeTransform();
        for(const auto& Part:Binding.Parts)Binding.FrozenParts.Add(Part.IsValid()?Part->GetRelativeTransform():FTransform::Identity);
    }
    if(BodyAnimation)BaseSupportGrip=BodyAnimation->LeftGripFromRight;
    UpdateWorldWeaponPresentation();
}

bool UFPSPlayerBodyComponent::IsWorldWeaponStowed(UPrimitiveComponent* Mesh) const
{
    const float Now=ServerClock();
    if(IsDeathViewActive())return true;
    if(FPSBodyPoses::Traversing(DisplayState.Motion)||Now<WorldWeaponsHiddenUntil)return true;
    const auto* Hand=WorldEquipmentHands.Find(Mesh);
    const bool BusyLeft=DisplayState.Action==EFPSBodyAction::Consume||DisplayState.Action==EFPSBodyAction::DoorPush
        ||(DisplayState.Action==EFPSBodyAction::Cast&&DisplayState.Contacts.Channel!=TEXT("StaffCast"));
    return Hand&&*Hand==1&&(((DisplayState.bDual||DisplayState.bOffhandPistol)&&BusyLeft)||Now<OffhandWeaponHiddenUntil);
}

void UFPSPlayerBodyComponent::UpdateWorldWeaponPresentation()
{
    const bool BodyVisible=!FPSPlayerBodyWorldBodyHidden();
    const bool BodyShadow=ShouldWorldBodyCastShadow();
    const auto Apply=[&](UPrimitiveComponent* Mesh)
    {
        if(!Mesh)return;
        if(const auto* Index=MotionEquipmentIndices.Find(Mesh);Index&&HasMatchingMotionRig(*Index))return;
        const bool Stowed=IsWorldWeaponStowed(Mesh);
        const bool Visible=BodyVisible&&!Stowed;
        if(Mesh->IsVisible()!=Visible)Mesh->SetVisibility(Visible);
        if(Mesh->bHiddenInGame==Visible)Mesh->SetHiddenInGame(!Visible);
        // A stowed weapon must not leave a floating weapon-shaped shadow.
        FPSBodyEquipment::ApplyShadowFlags(Mesh,BodyShadow&&!Stowed);
    };
    for(const auto& Weapon:WorldWeapons)Apply(Weapon.Get());
    for(const auto& Part:WorldParts)Apply(Part.Get());
}

void UFPSPlayerBodyComponent::ApplyOutfit(const TArray<FFPSBodyOutfitSlot>& Outfit)
{
    if(auto* Modular=GetOwner()->FindComponentByClass<UFPSModularOutfitComponent>())Modular->SetWorldOutfit(Outfit);
    if(FPSPlayerBodyWorldBodySuppressed())return;
    auto* Body=GetBodyMesh();if(!Body||!Configuration.IsValid())return;
    UFPSPerformanceMetricsSubsystem::CountOutfitRebuild(this);
    for(auto Part:OutfitMeshes)if(Part)Part->DestroyComponent();OutfitMeshes.Reset();
    for(auto Part:OutfitStaticMeshes)if(Part)Part->DestroyComponent();OutfitStaticMeshes.Reset();
    for(auto It=OriginalMaterials.CreateIterator();It;++It)
    {
        auto* Mesh=It.Key().Get();if(!IsValid(Mesh)){It.RemoveCurrent();continue;}
        if(auto* Skeletal=Cast<USkeletalMeshComponent>(Mesh);Skeletal&&Skeletal->GetSkeletalMeshAsset()!=It.Value().MeshAsset)
        {It.RemoveCurrent();continue;}
        for(int32 I=0;I<It.Value().Materials.Num();++I)Mesh->SetMaterial(I,It.Value().Materials[I]);
    }
    // Body sections are controlled by the outfit; restore them before applying a new combination.
    const auto* Render=Body->GetSkeletalMeshAsset()?Body->GetSkeletalMeshAsset()->GetResourceForRendering():nullptr;
    if(Render)for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        Body->ShowMaterialSection(Render->LODRenderData[L].RenderSections[S].MaterialIndex,S,true,L);
    const TSharedPtr<FJsonObject>* Definitions=nullptr;
    if(!Configuration->TryGetObjectField(TEXT("outfits"),Definitions))return;
    const auto Remember=[&](UMeshComponent* Mesh)
    {
        if(OriginalMaterials.Contains(Mesh))return;
        FFPSBodyOriginalMaterials Backup;
        if(auto* Skeletal=Cast<USkeletalMeshComponent>(Mesh))Backup.MeshAsset=Skeletal->GetSkeletalMeshAsset();
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)Backup.Materials.Add(Mesh->GetMaterial(I));
        OriginalMaterials.Add(Mesh,MoveTemp(Backup));
    };
    for(const auto& Entry:Outfit)
    {
        const TSharedPtr<FJsonObject>* Settings=nullptr;
        if(!(*Definitions)->TryGetObjectField(Entry.Definition.ToString(),Settings))continue;
        FString Path;
        bool bHasSkeletalOutfit=false;
        if((*Settings)->TryGetStringField(TEXT("world_mesh"),Path))if(auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Path))
        {
            auto* Part=NewObject<USkeletalMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Part);Part->SetSkeletalMeshAsset(Asset);Part->SetupAttachment(Body);
            FPSBodyEquipment::WorldVisibility(Part);Part->RegisterComponent();Part->SetLeaderPoseComponent(Body);
            OutfitMeshes.Add(Part);
            bHasSkeletalOutfit=true;
        }
        FString StaticPath;
        // 刚性装备件（背包等）：静态网格直接挂骨骼，变换由 JSON 给出骨骼相对偏移。
        // A fitted skeletal backpack owns the world presentation. Keep the
        // static source for its inventory icon, without drawing a second pack.
        if(!bHasSkeletalOutfit&&(*Settings)->TryGetStringField(TEXT("world_static_mesh"),StaticPath))if(auto* Asset=LoadObject<UStaticMesh>(nullptr,*StaticPath))
        {
            auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Part);Part->SetStaticMesh(Asset);
            FString Bone=TEXT("spine_03");(*Settings)->TryGetStringField(TEXT("attach_bone"),Bone);
            Part->SetupAttachment(Body,FName(*Bone));
            const FVector L=FPSBodyEquipment::JsonVector(*Settings,TEXT("attach_location"),FVector::ZeroVector);
            const FVector R=FPSBodyEquipment::JsonVector(*Settings,TEXT("attach_rotation"),FVector::ZeroVector);
            const FVector S=FPSBodyEquipment::JsonVector(*Settings,TEXT("attach_scale"),FVector::OneVector);
            Part->SetRelativeTransform(FTransform(FRotator(R.X,R.Y,R.Z).Quaternion(),L,S));
            FPSBodyEquipment::WorldVisibility(Part);Part->RegisterComponent();
            OutfitStaticMeshes.Add(Part);
        }
        const TArray<TSharedPtr<FJsonValue>>* Hidden=nullptr;
        if(Render&&(*Settings)->TryGetArrayField(TEXT("hide_body_materials"),Hidden))
            for(const auto& Value:*Hidden)for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
                if(Render->LODRenderData[L].RenderSections[S].MaterialIndex==static_cast<int32>(Value->AsNumber()))Body->ShowMaterialSection(static_cast<int32>(Value->AsNumber()),S,false,L);
        const TSharedPtr<FJsonObject>* Overrides=nullptr;
        if((*Settings)->TryGetObjectField(TEXT("body_materials"),Overrides))
        {
            Remember(Body);
            for(const auto& Pair:(*Overrides)->Values)if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Pair.Value->AsString()))Body->SetMaterial(FCString::Atoi(*Pair.Key),Material);
        }
        if((*Settings)->TryGetObjectField(TEXT("first_person_materials"),Overrides)&&Character.IsValid()&&Character->IsLocallyControlled())
        {
            TArray<USkeletalMeshComponent*> Meshes;GetOwner()->GetComponents(Meshes);
            for(auto* Mesh:Meshes)
            {
                if(Mesh==Body||WorldWeapons.Contains(Mesh)||WorldReloadProps.Contains(Mesh)||OutfitMeshes.Contains(Mesh)||!Mesh->GetSkeletalMeshAsset())continue;
                for(const auto& Pair:(*Overrides)->Values)
                {
                    const int32 Slot=Mesh->GetMaterialIndex(FName(*Pair.Key));
                    if(Slot!=INDEX_NONE)if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Pair.Value->AsString())){Remember(Mesh);Mesh->SetMaterial(Slot,Material);}
                }
            }
        }
    }
    ApplyWorldBodyVisibility();
}
