#include "WarhammerModificationAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "WarhammerCombat.h"
#include "ThunderHammerPommel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Characters/FPSBodyRuneVisual.h"
#include "../Characters/FPSPlayerBodyTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/Texture.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshOperations.h"
#include "StaticMeshCompiler.h"
#endif
#include "Serialization/JsonSerializer.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"

namespace
{
void SetParts(FColdSteelItem& Item,const FGunsmithParts& Parts)
{
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    auto Mods=MakeShared<FJsonObject>();for(const auto& Pair:Parts)Mods->SetStringField(Pair.Key,Pair.Value);
    Data->SetObjectField(TEXT("gunsmith_parts"),Mods);Item.Data.Reset();
    FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
}
bool Near(double A,double B){return FMath::IsNearlyEqual(A,B,.001);}
}

bool UWarhammerModificationAuditCommandlet::RepairSeatTangentBasis(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh||(!Mesh->GetPathName().StartsWith(TEXT("/Game/Weapons/ThunderGodHammer20261028/GuanLeiClosedCrownV12/"))&&
        !Mesh->GetPathName().StartsWith(TEXT("/Game/Weapons/ThunderGodHammer20261028/JiLeiInlaidLightningV14/"))))return false;
    FStaticMeshCompilingManager::Get().FinishCompilation({Mesh});
    const auto* Source=Mesh->GetMeshDescription(0);if(!Source)return false;
    FMeshDescription Description=*Source;
    FStaticMeshOperations::ComputeTriangleTangentsAndNormals(Description);
    FStaticMeshOperations::ComputeTangentsAndNormals(Description,EComputeNTBsFlags::Tangents|EComputeNTBsFlags::UseMikkTSpace|EComputeNTBsFlags::IgnoreDegenerateTriangles);
    FStaticMeshAttributes Attributes(Description);
    auto Normals=Attributes.GetVertexInstanceNormals();auto Tangents=Attributes.GetVertexInstanceTangents();auto Signs=Attributes.GetVertexInstanceBinormalSigns();
    int32 Repaired=0;
    for(const FVertexInstanceID V:Description.VertexInstances().GetElementIDs())
    {
        const FVector3f N=Normals[V].GetSafeNormal();if(N.ContainsNaN()||N.IsNearlyZero())return false;
        FVector3f X=Tangents[V];const bool Invalid=X.ContainsNaN()||X.SizeSquared()<.9f||FMath::Abs(FVector3f::DotProduct(X,N))>.001f;
        X=(X-N*FVector3f::DotProduct(X,N)).GetSafeNormal();
        if(X.ContainsNaN()||X.IsNearlyZero())
        {const auto Axis=FMath::Abs(N.Z)<.9f?FVector3f::UpVector:FVector3f::RightVector;X=FVector3f::CrossProduct(Axis,N).GetSafeNormal();}
        Tangents[V]=X;Signs[V]=Signs[V]<0.f?-1.f:1.f;Repaired+=Invalid;
    }
    // Commit only the tangent basis. Keep source vertices, custom normals, UVs,
    // material groups and the approved interfaces; never bake from a reduced LOD.
    Mesh->Modify();*Mesh->CreateMeshDescription(0)=MoveTemp(Description);Mesh->CommitMeshDescription(0);
    auto& Build=Mesh->GetSourceModel(0).BuildSettings;Build.bRecomputeNormals=false;Build.bRecomputeTangents=false;
    Build.bUseHighPrecisionTangentBasis=true;Build.bUseFullPrecisionUVs=true;
    Mesh->PostEditChange();FStaticMeshCompilingManager::Get().FinishCompilation({Mesh});Mesh->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("THOR_SEAT_BASIS mesh=%s corrected_corners=%d"),*Mesh->GetPathName(),Repaired);return true;
#else
    return false;
#endif
}

int32 UWarhammerModificationAuditCommandlet::Main(const FString& Params)
{
    if(FParse::Param(*Params,TEXT("ZhenTing")))return AuditZhenTing(Params);
    if(FParse::Param(*Params,TEXT("HeavyFormula")))return AuditHeavyFormula(Params);
    FString Definition=TEXT("ue_steel_warhammer");
    const bool Targeted=FParse::Value(*Params,TEXT("Definition="),Definition);
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("HammerModsAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WarhammerModificationAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("HammerModsAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();auto* G=GI->GetSubsystem<UGunsmithSystem>();
    if(!World||!Host||!G||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool Passed,const FString& Label,double Actual=0.,double Expected=0.)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("check"),Label);Row->SetBoolField(TEXT("pass"),Passed);
        Row->SetNumberField(TEXT("actual"),Actual);Row->SetNumberField(TEXT("expected"),Expected);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Passed;
        UE_LOG(LogTemp,Display,TEXT("HAMMER_MODS %s %s actual=%.5f expected=%.5f"),Passed?TEXT("PASS"):TEXT("FAIL"),*Label,Actual,Expected);
    };
    if(FParse::Param(*Params,TEXT("StormDriveLifecycle")))
    {
        // Reproduce mesh removal between the 250 ms discovery passes, without
        // starting gameplay or loading/modifying weapon assets and player saves.
        auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();
        auto* Tool=Pawn?Pawn->FindComponentByClass<UProductionToolComponent>():nullptr;
        Check(Tool!=nullptr,TEXT("storm lifecycle fixture"));
        if(Tool)
        {
            auto* OtherMesh=NewObject<UStaticMesh>(GetTransientPackage(),TEXT("StormLifecycleOtherWeapon"));
            for(const TCHAR* Name:{TEXT("Warhammer_StormDrive_Lifecycle"),
                TEXT("SM_ThunderGodHammer_head_mount_ji_lei_seat"),
                TEXT("SM_ThunderGodHammer_head_mount_ji_lei_seat_V14")})
            {
                auto* Asset=NewObject<UStaticMesh>(GetTransientPackage(),Name);
                auto* Seat=NewObject<UStaticMeshComponent>(Pawn);Pawn->AddInstanceComponent(Seat);
                Seat->SetCollisionEnabled(ECollisionEnabled::NoCollision);Seat->RegisterComponent();
                const auto Select=[&]()
                {
                    Seat->SetVisibility(true);Seat->SetHiddenInGame(false);Seat->SetOnlyOwnerSee(false);
                    Seat->SetStaticMesh(Asset);Tool->StormDriveSeatRefresh=0.f;Tool->UpdateStormDriveLightning(0.f);
                    Check(Tool->StormDriveSeat.Get()==Seat&&Tool->StormDriveSeatRefresh>.01f,FString(TEXT("select seat "))+Name);
                };
                Select();Seat->SetStaticMesh(nullptr);Tool->UpdateStormDriveLightning(.01f);
                Check(!Tool->StormDriveSeat.IsValid(),FString(TEXT("cached mesh cleared safely "))+Name);
                Seat->SetStaticMesh(Asset);Tool->UpdateStormDriveLightning(.01f);
                Check(Tool->StormDriveSeat.Get()==Seat,FString(TEXT("replacement seat reacquired next tick "))+Name);
                Seat->SetStaticMesh(OtherMesh);Tool->UpdateStormDriveLightning(.01f);
                Check(!Tool->StormDriveSeat.IsValid(),FString(TEXT("cached mesh replaced by unrelated weapon "))+Name);
                Select();Seat->SetVisibility(false);Tool->UpdateStormDriveLightning(.01f);
                Check(!Tool->StormDriveSeat.IsValid(),FString(TEXT("cached seat hidden "))+Name);
                Select();Seat->SetHiddenInGame(true);Tool->UpdateStormDriveLightning(.01f);
                Check(!Tool->StormDriveSeat.IsValid(),FString(TEXT("cached seat hidden in game "))+Name);
                Select();Seat->SetOnlyOwnerSee(true);Tool->UpdateStormDriveLightning(.01f);
                Check(!Tool->StormDriveSeat.IsValid(),FString(TEXT("observer rejects owner-only cached seat "))+Name);
                Select();Seat->UnregisterComponent();Tool->UpdateStormDriveLightning(.01f);
                Check(!Tool->StormDriveSeat.IsValid(),FString(TEXT("cached seat unregistered "))+Name);
                Seat->RegisterComponent();Select();Seat->DestroyComponent();Tool->UpdateStormDriveLightning(.01f);
                Check(!Tool->StormDriveSeat.IsValid(),FString(TEXT("cached seat destroyed "))+Name);
                Tool->ClearStormDriveLightning();
            }
        }
        if(Pawn)Pawn->Destroy();
        auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);
        Report->SetNumberField(TEXT("failures"),Failures);Report->SetNumberField(TEXT("count"),Rows.Num());
        Report->SetStringField(TEXT("isolated_profile"),Slot);Report->SetBoolField(TEXT("user_profile_modified"),false);
        Report->SetBoolField(TEXT("gameplay_started"),false);Report->SetBoolField(TEXT("real_network_transport_tested"),false);
        FString Out=FPaths::ProjectSavedDir()/TEXT("StormDriveLifecycle.json");FParse::Value(*Params,TEXT("Out="),Out);
        FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
        const bool Saved=FFileHelper::SaveStringToFile(Json,*Out);
        GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
        UE_LOG(LogTemp,Display,TEXT("STORM_LIFECYCLE_DONE checks=%d failures=%d"),Rows.Num(),Failures);
        return Failures||!Saved?1:0;
    }
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Stamina=100;Seed.bSprintExhausted=false;Seed.SwordUppercutCooldown=Seed.WhirlwindCooldown=0.f;
    Seed.Skills.FindOrAdd(TEXT("swordUppercut")).Level=1;Seed.Skills.FindOrAdd(TEXT("whirlwind")).Level=1;
    auto Hammer=Host->CreateItem(Definition);Hammer.Place=1;Hammer.Cell=6;
    if(!ColdSteelInventory::IsTwoHandedBlunt(Hammer)||!G->ModifiableWeapon(Definition))return 2;
    if(Targeted)
    {
        // Exercise the real grant without opening a personal save or filling the
        // fixture with every other starting weapon. All other receipts are seeded.
        auto Armory=Seed;Armory.ArmoryReceived.Reset();
        FString ItemText;TSharedPtr<FJsonObject> Definitions;
        if(!FFileHelper::LoadFileToString(ItemText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(ItemText),Definitions)||!Definitions)return 2;
        for(const auto& Entry:Definitions->Values)
        {
            const FString EntryId(*Entry.Key);if(EntryId!=Definition)Armory.ArmoryReceived.Add(EntryId);
        }
        Host->AdoptNetMirror(Armory);
        Check(Host->GrantStartingArmory(),TEXT("target armory grant succeeds"));
        const auto CountTarget=[&](){int32 Count=0;for(const auto& Item:Host->Snapshot().Items)Count+=Item.Definition==Definition;return Count;};
        Check(CountTarget()==1&&Host->Snapshot().ArmoryReceived.Contains(Definition),TEXT("target granted once with receipt"));
        Check(Host->GrantStartingArmory()&&CountTarget()==1,TEXT("repeated armory grant is idempotent"));
    }
    const auto Equip=[&](UColdSteelStatusModel* Model,const FColdSteelItem& Item)
    {auto State=Seed;State.Items.Add(Item);Model->AdoptNetMirror(State);};
    Equip(Host,Hammer);
    const auto Factory=ColdSteelTool::Evaluate(Hammer,Host);
    const float Fireball=Host->FireballStats().Cooldown,Uppercut=Host->SwordUppercutCooldownSeconds();
    SetParts(Hammer,{{TEXT("rune"),TEXT("resonance_rune")},{TEXT("pommel"),TEXT("twin_disc_balance")}});Equip(Host,Hammer);
    Check(Near(Host->FireballStats().Cooldown/Fireball,.85),TEXT("hammer resonance applies to magic cooldown"),Host->FireballStats().Cooldown/Fireball,.85);
    Check(Near(Host->SwordUppercutCooldownSeconds()/Uppercut,.68),TEXT("resonance and balancing pommel multiply for martial cooldown"),Host->SwordUppercutCooldownSeconds()/Uppercut,.68);
    const auto HammerMods=ColdSteelMelee::EquippedModifiers(Host);
    Check(Near(HammerMods.SkillCooldown,.85)&&Near(HammerMods.MartialCooldown,.8),TEXT("tool executor preserves hammer equipped passives"));
    auto Axe=Host->CreateItem(TEXT("tool_axe"));Axe.Place=1;Axe.Cell=6;Equip(Host,Axe);
    Check(Near(ColdSteelMelee::EquippedModifiers(Host).SkillCooldown,1.),TEXT("harvesting axe does not inherit stored hammer passives"));

    // Every registered hammer option executes the real normalization and evaluator.
    const auto* Catalog=G->ModifiableWeapon(Hammer.Definition);
    for(const auto& Column:Catalog->Options)for(const auto& Part:Column.Value)if(Part.Id!=TEXT("false"))
    {
        FGunsmithParts Parts{{Column.Key,Part.Id}};
        const auto Normal=G->Normalize(Hammer.Definition,Parts);const auto M=G->Calculate(Hammer.Definition,Normal).Melee;
        Check(Normal.FindRef(Column.Key)==Part.Id,TEXT("option survives normalization ")+Column.Key+TEXT("/")+Part.Id);
        Check(Near(M.PhysicalDamage,Part.Melee.PhysicalDamage)&&Near(M.AttackSpeed,Part.Melee.AttackSpeed)&&
            Near(M.Stamina,Part.Melee.Stamina)&&Near(M.ToughnessDamage,Part.Melee.ToughnessDamage)&&
            Near(M.HeavyChargeSpeedBonus,Part.Melee.HeavyChargeSpeedBonus)&&Near(M.HeavyReleaseStamina,Part.Melee.HeavyReleaseStamina)&&
            Near(M.PhysicalArmorPenetration,Part.Melee.PhysicalArmorPenetration),TEXT("native modifier evaluation ")+Part.Id);
        if(Targeted)
        {
            auto Item=Host->CreateItem(Definition);SetParts(Item,Parts);
            const auto Geometry=ColdSteelModularSword::DescribeGeometry(Item);
            Check(Geometry.Num()==6,TEXT("six-module remote recipe ")+Part.Id,Geometry.Num(),6);
            bool Loaded=true;for(const auto& Module:Geometry)Loaded&=LoadObject<UStaticMesh>(nullptr,*Module.Mesh)!=nullptr;
            Check(Loaded,TEXT("every selected module loads ")+Part.Id);
            if(Part.Id==TEXT("guan_lei_seat")||Part.Id==TEXT("ji_lei_seat"))
            {
                for(const auto& Module:Geometry)if(Module.Mesh.Contains(TEXT("head_mount_")+Part.Id))
                {
                    const auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Module.Mesh);
                    const auto* Render=Mesh?Mesh->GetRenderData():nullptr;
                    const bool HasBuffers=Render&&Render->LODResources.Num()>0&&Render->LODResources[0].VertexBuffers.StaticMeshVertexBuffer.GetNumVertices()>0;
                    Check(HasBuffers,TEXT("saved seat mesh has render tangent buffers ")+Part.Id);
                    if(HasBuffers)
                    {
                        const auto& Buffer=Render->LODResources[0].VertexBuffers.StaticMeshVertexBuffer;int32 Invalid=0;int32 Axes[3]={};
                        for(uint32 V=0;V<Buffer.GetNumVertices();++V)
                        {
                            int32 Index=0;
                            for(const FVector3f Axis:{FVector3f(Buffer.VertexTangentX(V)),Buffer.VertexTangentY(V),FVector3f(Buffer.VertexTangentZ(V))})
                            {const bool Bad=Axis.ContainsNaN()||Axis.SizeSquared()<.9f;Axes[Index++]+=Bad;Invalid+=Bad;}
                        }
                        UE_LOG(LogTemp,Display,TEXT("GUANLEI_TANGENTS mesh=%s vertices=%u invalid_x=%d invalid_y=%d invalid_z=%d nanite=%d explicit=%d target=%d percent=%f error=%f"),
                            *Mesh->GetPathName(),Buffer.GetNumVertices(),Axes[0],Axes[1],Axes[2],Mesh->NaniteSettings.bEnabled,Mesh->NaniteSettings.bExplicitTangents,
                            int32(Mesh->NaniteSettings.FallbackTarget),Mesh->NaniteSettings.FallbackPercentTriangles,Mesh->NaniteSettings.FallbackRelativeError);
                        Check(Invalid==0,TEXT("built seat render tangents are finite and normalized ")+Part.Id,Invalid,0);
                    }
                }
            }
            auto* Actor=World->SpawnActor<AActor>();auto* Root=NewObject<UStaticMeshComponent>(Actor);
            Actor->SetRootComponent(Root);Actor->AddInstanceComponent(Root);Root->RegisterComponent();
            Check(ColdSteelModularSword::Apply(Root,Item),TEXT("native selected assembly ")+Part.Id);
            Check(ColdSteelModularSword::Components(Root).Num()==6,TEXT("six visible assembled modules ")+Part.Id);
            if(Column.Key==TEXT("rune"))
            {
                int32 RuneCarriers=0;
                for(auto* Module:ColdSteelModularSword::Components(Root))
                {
                    FFPSBodyAttachment Description;FPSBodyRuneVisual::Capture(Module,&Item,Description);
                    if(Description.RuneDefinition.IsEmpty())continue;
                    ++RuneCarriers;
                    Check(Description.RuneId==Part.Id&&Description.RuneSlot==TEXT("SwordSlot=shaft"),TEXT("selected rune captured on shaft ")+Part.Id);
                    auto* Previous=Module->GetOverlayMaterial(true,0);
                    ColdSteelMeleeRune::Apply(Module,Part.Id,Definition);
                    Check(Previous&&Module->GetOverlayMaterial(true,0)==Previous,TEXT("same rune reuses existing material ")+Part.Id);
                }
                Check(RuneCarriers==1,TEXT("one active rune carrier ")+Part.Id,RuneCarriers,1);
            }
            const FBox Bounds=ColdSteelModularSword::LocalBounds(Root);
            Check(Bounds.IsValid&&Bounds.GetSize().Z>90.&&Bounds.GetSize().Z<140.,TEXT("assembled length stays within hammer range ")+Part.Id,Bounds.GetSize().Z,115.);
            const FString SelectedKey=ColdSteelModularSword::Key(Item);
            SetParts(Item,{});Check(ColdSteelModularSword::Key(Item)!=SelectedKey,TEXT("factory reset invalidates assembly ")+Part.Id);
            Check(ColdSteelModularSword::Apply(Root,Item),TEXT("factory visual restores ")+Part.Id);
            if(Column.Key==TEXT("rune"))
            {
                bool Cleared=true;for(auto* Module:ColdSteelModularSword::Components(Root))
                {FFPSBodyAttachment Description;FPSBodyRuneVisual::Capture(Module,&Item,Description);Cleared&=Description.RuneDefinition.IsEmpty();}
                Check(Cleared,TEXT("factory removes added rune ")+Part.Id);
            }
            ColdSteelModularSword::Clear(Root);Actor->Destroy();
        }
    }
    const TArray<FString> Weapons=Targeted?TArray<FString>{Definition}:TArray<FString>{TEXT("ue_rune_sword"),TEXT("ue_frost_crystal_sword"),TEXT("ue_highland_claymore"),TEXT("ue_tang_dao"),TEXT("ue_xuanchi_zhenyue"),TEXT("ue_steel_warhammer")};
    for(const auto& Id:Weapons)
    {
        auto Item=Host->CreateItem(Id);Item.Place=1;Item.Cell=6;Equip(Host,Item);
        const bool Blunt=ColdSteelInventory::IsTwoHandedBlunt(Item);
        const auto Before=Blunt?ColdSteelTool::Evaluate(Item,Host).Damage:ColdSteelMelee::Evaluate(Item,Host).DamageParts;
        const FString RuneSlot=Blunt?TEXT("rune"):TEXT("blade_2");
        SetParts(Item,{{RuneSlot,TEXT("strength_rune")}});Equip(Host,Item);
        const auto After=Blunt?ColdSteelTool::Evaluate(Item,Host).Damage:ColdSteelMelee::Evaluate(Item,Host).DamageParts;
        Check(Near(After.BasePhysical,Before.BasePhysical*1.1)&&Near(After.AddedMagic,Before.AddedMagic),TEXT("strength physical-only native damage ")+Id,After.BasePhysical,Before.BasePhysical*1.1);
        Check(G->Installed(Item).FindRef(RuneSlot)==TEXT("strength_rune"),TEXT("installed payload roundtrip ")+Id);
        auto* Actor=World->SpawnActor<AActor>();auto* Root=NewObject<UStaticMeshComponent>(Actor);
        Actor->SetRootComponent(Root);Actor->AddInstanceComponent(Root);Root->RegisterComponent();
        Check(ColdSteelModularSword::Apply(Root,Item),TEXT("installed modular assembly ")+Id);
        int32 Carriers=0;
        for(auto* Source:ColdSteelModularSword::Components(Root))
        {
            FFPSBodyAttachment Description;FPSBodyRuneVisual::Capture(Source,&Item,Description);
            if(Description.RuneDefinition.IsEmpty())continue;
            ++Carriers;TArray<uint8> Bytes;
            {FMemoryWriter Writer(Bytes);FObjectAndNameAsStringProxyArchive Ar(Writer,false);FFPSBodyAttachment::StaticStruct()->SerializeItem(Ar,&Description,nullptr);}
            FFPSBodyAttachment Read;
            {FMemoryReader Reader(Bytes);FObjectAndNameAsStringProxyArchive Ar(Reader,true);FFPSBodyAttachment::StaticStruct()->SerializeItem(Ar,&Read,nullptr);}
            Check(FPSBodyRuneVisual::Key(Read)==FPSBodyRuneVisual::Key(Description)&&Read.RuneId==TEXT("strength_rune"),TEXT("replicated attachment data roundtrip ")+Id);
            auto* Remote=NewObject<UStaticMeshComponent>(Actor);Actor->AddInstanceComponent(Remote);Remote->SetStaticMesh(Source->GetStaticMesh());
            for(int32 Index=0;Index<Source->GetNumMaterials();++Index)
            {
                UMaterialInterface* Material=Source->GetMaterial(Index);while(auto* MID=Cast<UMaterialInstanceDynamic>(Material))Material=MID->Parent;
                Remote->SetMaterial(Index,Material);
            }
            FPSBodyRuneVisual::Apply(Remote,Read);bool Red=false,Mask=false;
            for(int32 Index=0;Index<Remote->GetNumMaterials();++Index)
            {
                auto* MID=Cast<UMaterialInstanceDynamic>(Remote->GetOverlayMaterial(true,Index));
                if(!MID)MID=Cast<UMaterialInstanceDynamic>(Remote->GetMaterial(Index));if(!MID)continue;
                const auto Color=MID->K2_GetVectorParameterValue(TEXT("ConductionCoreColor"));
                Red|=Color.R>.8&&Color.G<.02&&Color.B<.025;
                auto* Texture=MID->K2_GetTextureParameterValue(TEXT("RuneTexture"));Mask|=Texture&&Texture->GetName()==TEXT("T_Mask_strength_rune");
            }
            Check(Red&&Mask,TEXT("observer reconstructs red strength ink ")+Id);
            FFPSBodyAttachment Empty;Check(FPSBodyRuneVisual::Key(Read)!=FPSBodyRuneVisual::Key(Empty),TEXT("rune-only selection invalidates equipment key ")+Id);
        }
        Check(Carriers>0,TEXT("rune carrier captured ")+Id,Carriers,1);
        ColdSteelModularSword::Clear(Root);Actor->Destroy();
    }

    // Remote player authority must spend only that player's shadow stamina.
    SetParts(Hammer,{{TEXT("hammer_heads"),TEXT("pointed_hammer")},{TEXT("pommel"),TEXT("no_pommel")},{TEXT("rune"),TEXT("strength_rune")}});
    auto GuestSeed=Seed;GuestSeed.Items.Add(Hammer);
    auto* Guest=Host->CreateShadowModel(GuestSeed);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<AWarhammerAuditRemoteController>();
    auto* PS=World->SpawnActor<AColdSteelPlayerState>();PC->PlayerState=PS;PC->Possess(Pawn);PS->ShadowModel=Guest;Guest->AttachPawn(Pawn);
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;Tool->Kind=TEXT("warhammer");
    if(Targeted)
    {
        if(Definition==TEXT("ue_thunder_god_hammer"))
        {
            auto CoreItem=Host->CreateItem(Definition);SetParts(CoreItem,{{TEXT("pommel"),TEXT("lei_xi_pommel")}});
            auto* Root=NewObject<UStaticMeshComponent>(Pawn);Pawn->AddInstanceComponent(Root);Root->RegisterComponent();
            Check(ColdSteelModularSword::Apply(Root,CoreItem),TEXT("LeiXi remote assembly loads current pommel"));
            auto* Buff=UCombatStatusFormula::GetOrAdd(Pawn);Buff->GrantMagicInspiration();int32 Cores=0;
            for(auto* Part:ColdSteelModularSword::Components(Root))
            {
                ThunderHammerPommel::RefreshWorldCore(Pawn,Part);
                for(int32 SlotIndex=0;SlotIndex<Part->GetNumMaterials();++SlotIndex)
                    if(auto* MID=Cast<UMaterialInstanceDynamic>(Part->GetMaterial(SlotIndex));MID&&MID->GetBaseMaterial()->GetFName()==TEXT("M_LeiXi_StormCore"))
                    {++Cores;Check(MID->K2_GetScalarParameterValue(TEXT("LeiXiActive"))==1.f,TEXT("remote LeiXi core follows active inspiration"));}
            }
            Check(Cores==1,TEXT("one remote LeiXi core material"));Buff->TickComponent(10.1f,LEVELTICK_All,nullptr);
            for(auto* Part:ColdSteelModularSword::Components(Root))
            {
                ThunderHammerPommel::RefreshWorldCore(Pawn,Part);
                for(int32 SlotIndex=0;SlotIndex<Part->GetNumMaterials();++SlotIndex)
                    if(auto* MID=Cast<UMaterialInstanceDynamic>(Part->GetMaterial(SlotIndex));MID&&MID->GetBaseMaterial()->GetFName()==TEXT("M_LeiXi_StormCore"))
                        Check(MID->K2_GetScalarParameterValue(TEXT("LeiXiActive"))==0.f,TEXT("remote LeiXi core resets on inspiration expiry"));
            }
            ColdSteelModularSword::Clear(Root);Root->DestroyComponent();
        }
        for(const TCHAR* HostId:{TEXT("ue_steel_warhammer"),TEXT("ue_runebound_warhammer"),TEXT("ue_thunder_god_hammer")})
        {
            auto SeatItem=Host->CreateItem(HostId);SetParts(SeatItem,{{TEXT("head_mount"),TEXT("storm_drive_seat")}});
            auto* SeatRoot=NewObject<UStaticMeshComponent>(Pawn);Pawn->AddInstanceComponent(SeatRoot);SeatRoot->RegisterComponent();
            Check(ColdSteelModularSword::Apply(SeatRoot,SeatItem),FString(TEXT("storm seat assembly "))+HostId);
            Tool->StormDriveSeatRefresh=0.f;Tool->UpdateStormDriveLightning(0.f);
            const bool RetiredThor=FString(HostId)==TEXT("ue_thunder_god_hammer");
            Check(RetiredThor?!Tool->StormDriveSeat.IsValid():Tool->StormDriveSeat.Get()==SeatRoot,
                FString(RetiredThor?TEXT("retired Thor storm seat remains absent "):TEXT("storm lightning selects installed seat "))+HostId);
            SeatRoot->SetVisibility(false);Tool->StormDriveSeatRefresh=0.f;Tool->UpdateStormDriveLightning(0.f);
            Check(!Tool->StormDriveSeat.IsValid(),FString(TEXT("hidden storm seat stops selection "))+HostId);
            ColdSteelModularSword::Clear(SeatRoot);SeatRoot->DestroyComponent();
        }
        Tool->ClearStormDriveLightning();
    }
    Check(ColdSteelAuthority::ForPawn(Pawn)==Guest,TEXT("authority resolves guest shadow rather than host model"));
    const float HostStamina=Host->Stamina();
    const auto Stats=ColdSteelTool::Evaluate(Hammer,Guest);
    Check(Near(Stats.StaminaCost/Factory.StaminaCost,1.15*.95),TEXT("pointed head and no pommel normal cost"),Stats.StaminaCost/Factory.StaminaCost,1.15*.95);
    Check(Near(Stats.HeavyReleaseStaminaCost/Stats.StaminaCost,1.1),TEXT("no pommel heavy release surcharge"));
    const auto Attack=[&](uint32 Id,bool Heavy,bool Sprint)
    {
        Tool->CancelUse();Tool->BluntServerReadyAt=0.;Guest->AdoptNetMirror(GuestSeed);
        if(Heavy){Tool->ServerBeginBluntCharge_Implementation(Id);Tool->BluntServerChargeStartedAt=World->GetTimeSeconds()-Stats.HeavyChargeSeconds-.05;}
        if(Sprint){Tool->BluntSprintInstance=Hammer.InstanceId;Tool->BluntSprintReadyAt=World->GetTimeSeconds();}
        const float Before=Guest->Stamina();Tool->ServerBeginBluntAttack_Implementation(Id,Heavy,Sprint);
        const double Expected=Heavy?Stats.HeavyReleaseStaminaCost:Stats.StaminaCost;
        Check(Near(Before-Guest->Stamina(),Expected),Sprint?TEXT("guest sprint charged once without heavy surcharge"):Heavy?TEXT("guest charged heavy cost"):TEXT("guest normal cost"),Before-Guest->Stamina(),Expected);
        Check(Near(Tool->AxeStrike.ArmorPenetration,.15),TEXT("authority strike includes pointed-head penetration"),Tool->AxeStrike.ArmorPenetration,.15);
        Check(Near(Host->Stamina(),HostStamina),TEXT("guest attack leaves host stamina unchanged"));
    };
    Attack(1,false,false);Attack(2,true,false);Attack(3,false,true);Tool->CancelUse();
    Guest->AdoptNetMirror(GuestSeed);const float ReceiptBefore=Guest->Stamina();
    Check(Tool->ApplyBluntStaminaReceipt(Guest,10,12.f)&&Near(Guest->Stamina(),ReceiptBefore-12.f),TEXT("late accepted cost applies after cancellation"));
    Check(!Tool->ApplyBluntStaminaReceipt(Guest,10,12.f)&&Near(Guest->Stamina(),ReceiptBefore-12.f),TEXT("duplicate cost receipt does not spend twice"));
    Check(!Tool->ApplyBluntStaminaReceipt(Guest,9,12.f),TEXT("older cost receipt ignored"));
    Check(Tool->ApplyBluntStaminaReceipt(Guest,11,1000.f)&&Near(Guest->Stamina(),0.),TEXT("accepted cost clamps depleted client stamina"));
    if(Definition==TEXT("ue_steel_warhammer"))
    {
        SetParts(Hammer,{{TEXT("hammer_heads"),TEXT("meteor_core")}});GuestSeed.Items[0]=Hammer;Guest->AdoptNetMirror(GuestSeed);
        Tool->ApplyToolStats(Guest->ActiveProductionTool(),Guest);
        Check(Near(Tool->BluntWaveRadius,450.),TEXT("guest meteor core authoritative shockwave radius"),Tool->BluntWaveRadius,450.);
    }
    else if(Definition==TEXT("ue_thunder_god_hammer"))
    {
        const auto Rejected=G->Normalize(Definition,{{TEXT("hammer_heads"),TEXT("meteor_core")},{TEXT("rune"),TEXT("swift_mana_rune")}});
        Check(Rejected.FindRef(TEXT("hammer_heads"))!=TEXT("meteor_core")&&Rejected.FindRef(TEXT("rune"))!=TEXT("swift_mana_rune"),TEXT("other hammer exclusive options rejected"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetNumberField(TEXT("count"),Rows.Num());Report->SetStringField(TEXT("isolated_profile"),Slot);
    Report->SetBoolField(TEXT("native_authority_executed"),true);Report->SetBoolField(TEXT("real_network_transport_tested"),false);
    Report->SetBoolField(TEXT("user_profile_modified"),false);
    Report->SetStringField(TEXT("definition"),Definition);
    FString Out=FPaths::ProjectSavedDir()/TEXT("WarhammerModificationAudit.json");FParse::Value(*Params,TEXT("Out="),Out);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Out);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    UE_LOG(LogTemp,Display,TEXT("HAMMER_MODS_DONE checks=%d failures=%d"),Rows.Num(),Failures);return Failures?1:0;
}
