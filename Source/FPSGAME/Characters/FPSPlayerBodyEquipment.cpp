#include "FPSPlayerBodyComponent.h"
#include "FPSModularOutfitComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "../Weapons/FPSGunplayAnimInstance.h"
#include "../Weapons/WeaponGripProfile.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "../Weapons/Staff/StaffGripPose.h"
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
static bool IsArmMaterial(const FString& Slot)
{
    const FString Name=Slot.ToLower();
    // "Handguard" is a weapon part, not a first-person hand section.
    return Name.Contains(TEXT("manny"))||Name==TEXT("hand")||Name==TEXT("hands")
        ||Name.EndsWith(TEXT("_hand"))||Name.EndsWith(TEXT("_hands"))
        ||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||Name==TEXT("skin");
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
        const FName Slot=Asset->GetMaterials()[I].MaterialSlotName;
        // A parked first-person reload cartridge is not part of the carried gun.
        if(FPSBodyEquipment::IsArmMaterial(Slot.ToString())
            ||(bSuper90&&Slot==Super90WeaponAssets::LooseShellMaterial))Result.HiddenMaterials.Add(I);
    }
    TArray<USceneComponent*> Children;Source->GetChildrenComponents(true,Children);
    for(auto* Child:Children)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->GetStaticMesh()&&Result.Parts.Num()<64)
    {
        FFPSBodyAttachment Entry;Entry.Mesh=Part->GetStaticMesh();
        Entry.bVisible=Part->IsVisible()&&!Part->bHiddenInGame;
        Entry.RelativeTransform=Part->GetRelativeTransform();
        USceneComponent* Branch=Part;
        while(Branch->GetAttachParent()&&Branch->GetAttachParent()!=Source)
        {Branch=Branch->GetAttachParent();Entry.RelativeTransform=Entry.RelativeTransform*Branch->GetRelativeTransform();}
        Entry.Socket=Branch->GetAttachSocketName();
        for(int32 I=0;I<Part->GetNumMaterials();++I)Entry.Materials.Add(FPSBodyEquipment::PersistentMaterial(Part->GetMaterial(I)));
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
    for(auto& W:Weapons)
    {
        FString Schema=W.Mesh.ToSoftObjectPath().ToString()+W.StaticMesh.ToSoftObjectPath().ToString()+W.GripBone.ToString();
        for(int32 B:W.MotionBones)Schema+=FString::Printf(TEXT("|%d"),B);
        for(const auto& P:W.Parts)Schema+=TEXT("|")+P.Mesh.ToSoftObjectPath().ToString()+P.Socket.ToString();
        W.MotionSchema=FCrc::StrCrc32(*Schema);
    }
    FString Key=DisplayState.Weapon.ToString();
    for(const auto& W:Weapons)
    {
        Key+=TEXT("|")+W.Mesh.ToSoftObjectPath().ToString()+TEXT("|")+W.HoldClip.ToSoftObjectPath().ToString();
        Key+=TEXT("|")+W.StaticMesh.ToSoftObjectPath().ToString()+TEXT("|")+W.StaticGrip.ToString();
        Key+=TEXT("|")+W.GripProfile.ToSoftObjectPath().ToString()+FString::Printf(TEXT("|%s:%d:%d"),*W.PoseFamily.ToString(),W.AttachHand,W.StaffVariant);
        for(const auto& Clip:W.MotionClips)Key+=TEXT("|")+Clip.Role.ToString()+Clip.Sequence.ToSoftObjectPath().ToString();
        if(W.PoseFamily==TEXT("Bow"))Key+=TEXT("|")+W.Bow.UpperTip.ToString()+W.Bow.LowerTip.ToString()+W.Bow.Brace.ToString()+W.Bow.ArrowRest.ToString()
            +FString::Printf(TEXT("|%.6f:%.6f:%.6f:%.6f"),W.Bow.StringRadius,W.Bow.ArrowRadius,W.Bow.ArrowLength,W.Bow.FlexDistribution);
        for(const int32 Hidden:W.HiddenMaterials)Key+=FString::Printf(TEXT("#%d"),Hidden);
        for(const auto& Material:W.Materials)Key+=TEXT("|")+Material.ToSoftObjectPath().ToString();
        for(const auto& Part:W.Parts)
        {
            Key+=TEXT("|")+Part.Mesh.ToSoftObjectPath().ToString();
            if(!W.Source.IsValid())Key+=TEXT("|")+Part.RelativeTransform.ToString();
            Key+=TEXT("|")+Part.SkeletalMesh.ToSoftObjectPath().ToString()+Part.Slot.ToString()+TEXT("|")+Part.Socket.ToString();
            for(const auto& Material:Part.Materials)Key+=TEXT("|")+Material.ToSoftObjectPath().ToString();
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
    for(auto Part:WorldParts)if(Part)Part->DestroyComponent();WorldParts.Reset();
    for(auto Weapon:WorldWeapons)if(Weapon)Weapon->DestroyComponent();WorldWeapons.Reset();
    WorldEquipmentHands.Reset();
    MotionBindings.Reset();MotionMaps.Reset();MotionEquipmentIndices.Reset();
    if(WorldStaffLight){WorldStaffLight->DestroyComponent();WorldStaffLight=nullptr;}WorldStaffMaterials.Reset();LastWorldLight=-1.f;
    ClearBow();
    if(BodyAnimation){BodyAnimation->bHasLeftGrip=false;BodyAnimation->EquipmentGripHands=0;BodyAnimation->EquipmentFingers.Reset();BodyAnimation->bBowPose=false;}
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
                    Grip.Transfer(Pose,BodyAnimation->EquipmentFingers);BodyAnimation->EquipmentGripHands|=1<<Side;
                    Part->SetRelativeTransform(FTransform(-StaffGripPose::HoldPoint())*Hold.HandInGrip.Inverse()*Grip.Mount);
                    BodyAnimation->StaffHandRotation=(Grip.Mount.Inverse()*Pose[Grip.SourceHand]*FTransform(FRotator(0,90,0))).GetRotation();
                }
            }
            FPSBodyEquipment::WorldVisibility(Part);
            for(int32 I=0;I<Definition.Materials.Num();++I)if(auto* Material=Definition.Materials[I].LoadSynchronous())Part->SetMaterial(I,Material);
            Part->RegisterComponent();WorldParts.Add(Part);
            Motion.Static=Part;
            MotionEquipmentIndices.Add(Part,Index);
            for(const auto& Attachment:Definition.Parts)if(auto* ChildMesh=Attachment.Mesh.LoadSynchronous())
            {
                auto* Child=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);GetOwner()->AddInstanceComponent(Child);
                Child->SetStaticMesh(ChildMesh);Child->SetupAttachment(Part);Child->SetRelativeTransform(Attachment.RelativeTransform);
                WorldEquipmentHands.Add(Child,static_cast<uint8>(Side));FPSBodyEquipment::WorldVisibility(Child);
                for(int32 I=0;I<Attachment.Materials.Num();++I)if(auto* M=Attachment.Materials[I].LoadSynchronous())Child->SetMaterial(I,M);
                Child->RegisterComponent();WorldParts.Add(Child);
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
                Weapon->ShowMaterialSection(Material,S,!Definition.HiddenMaterials.Contains(Material),L);
            }
        Weapon->SetComponentTickEnabled(false);WorldWeapons.Add(Weapon);
        Motion.Mesh=Weapon;Motion.FrozenPose=Weapon->GetComponentSpaceTransforms();
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
        for(const auto& DefinitionPart:Definition.Parts)if(auto* AssetPart=DefinitionPart.Mesh.LoadSynchronous())
        {
            auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Part);Part->SetStaticMesh(AssetPart);
            Part->SetupAttachment(Weapon);
            Part->SetRelativeTransform(DefinitionPart.Socket.IsNone()?DefinitionPart.RelativeTransform
                :DefinitionPart.RelativeTransform*Weapon->GetSocketTransform(DefinitionPart.Socket,RTS_Component));
            WorldEquipmentHands.Add(Part,static_cast<uint8>(Side));
            FPSBodyEquipment::WorldVisibility(Part);
            for(int32 I=0;I<DefinitionPart.Materials.Num();++I)if(auto* Material=DefinitionPart.Materials[I].LoadSynchronous())Part->SetMaterial(I,Material);
            Part->RegisterComponent();WorldParts.Add(Part);
            Motion.Parts.Add(Part);
            MotionEquipmentIndices.Add(Part,Index);
        }
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
        if(const auto* Index=MotionEquipmentIndices.Find(Mesh);Index&&DisplayState.Contacts.Rigs.IsValidIndex(*Index)&&MotionBindings.IsValidIndex(*Index))
        {
            const auto& Sample=DisplayState.Contacts.Rigs[*Index];const auto& Binding=MotionBindings[*Index];
            if(Sample.Valid&&Sample.Schema==Binding.Definition.MotionSchema&&Sample.Bones.Num()==Binding.Definition.MotionBones.Num()&&Sample.Parts.Num()==Binding.Parts.Num())return;
        }
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
                if(Mesh==Body||WorldWeapons.Contains(Mesh)||OutfitMeshes.Contains(Mesh)||!Mesh->GetSkeletalMeshAsset())continue;
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
