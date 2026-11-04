#include "ModularSwordVisual.h"
#include "FrostSwordRunes.h"
#include "GunsmithModificationTier.h"
#include "../Characters/FPSBodyRuneVisual.h"
#include "../Characters/FPSPlayerBodyTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"

// Explicitly invoked development check; uses an isolated profile and no game save.
int32 RunSharedTwoHandFinishAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("SwordBladeFinishAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SwordBladeFinishAudit -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("SharedFinishAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();auto* G=GI->GetSubsystem<UGunsmithSystem>();
    if(!World||!Host||!G||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    int32 Checks=0,Failures=0,Cases=0;TArray<TSharedPtr<FJsonValue>> Errors,Weapons;
    const auto Check=[&](bool Pass,const FString& Label)
    {
        ++Checks;if(Pass)return;++Failures;Errors.Add(MakeShared<FJsonValueString>(Label));
        UE_LOG(LogTemp,Error,TEXT("SHARED_FINISH_FAIL %s"),*Label);
    };
    const TArray<FString> Definitions={TEXT("ue_rune_sword"),TEXT("ue_frost_crystal_sword"),TEXT("ue_highland_claymore"),
        TEXT("ue_tang_dao"),TEXT("ue_xuanchi_zhenyue"),TEXT("ue_zhanmadao"),TEXT("ue_steel_warhammer"),TEXT("ue_runebound_warhammer"),TEXT("ue_thunder_god_hammer")};
    const TArray<FString> Common={TEXT("false"),TEXT("folded_steel"),TEXT("dark_iron"),TEXT("mithril"),TEXT("damascus_steel"),TEXT("meteoric_iron")};
    const auto Scalar=[](UMaterialInterface* M,const TCHAR* Name,float& V){return M&&M->GetScalarParameterValue(FMaterialParameterInfo(Name),V);};
    const auto CheckRune=[&](UStaticMeshComponent* Mesh,const FString& Label,const FString& ExpectedMask)
    {
        int32 Active=0;
        for(int32 Index=0;Index<Mesh->GetNumMaterials();++Index)
        {
            for(auto* M:{Mesh->GetMaterial(Index),Mesh->GetOverlayMaterial(true,Index)})
            {
                if(!M||!M->GetBaseMaterial())continue;
                const FString Name=M->GetBaseMaterial()->GetName();float Mode=-1.f;UTexture* Texture=nullptr;
                if(Name==TEXT("M_AzureRunesword_NativeGold"))
                {
                    ++Active;Check(Scalar(M,TEXT("GoldAmount"),Mode)&&Mode>0.f,Label+TEXT(" native rune enabled"));
                    Check(M->GetTextureParameterValue(FMaterialParameterInfo(TEXT("NativeRuneMask")),Texture)&&Texture,Label+TEXT(" native rune mask"));
                    Check(Texture&&Texture->GetName()==(Mesh->ComponentHasTag(TEXT("SwordSlot=guard"))?TEXT("T_RuneSword_GuardNativeMask"):TEXT("T_RuneSword_NativeMask")),Label+TEXT(" native rune coverage"));
                }
                else if((Name.StartsWith(TEXT("M_SilverRuneSurface"))||Name.StartsWith(TEXT("M_TangDaoBladeRuneSurface"))||Name.StartsWith(TEXT("M_XuanChiBladeRuneSurface")))&&Scalar(M,TEXT("RuneMode"),Mode)&&Mode>=0.f)
                {
                    ++Active;Check(M->GetTextureParameterValue(FMaterialParameterInfo(TEXT("RuneTexture")),Texture)&&Texture,Label+TEXT(" selected rune texture"));
                    Check(Texture&&Texture->GetName()==ExpectedMask,Label+TEXT(" selected rune identity"));
                    float Glow=0.f;Check(Scalar(M,TEXT("GlowStrength"),Glow)&&Glow>0.f,Label+TEXT(" rune glow enabled"));
                    FLinearColor Dimensions;Check(M->GetVectorParameterValue(FMaterialParameterInfo(TEXT("Dimensions")),Dimensions)&&Dimensions.R>0.f&&Dimensions.G>0.f&&Dimensions.B>0.f,Label+TEXT(" rune projection dimensions"));
                }
            }
        }
        return Active;
    };
    for(const auto& Definition:Definitions)
    {
        auto Item=Host->CreateItem(Definition);const bool Hammer=ColdSteelInventory::IsTwoHandedBlunt(Item),RuneSword=Definition==TEXT("ue_rune_sword");
        const FString PartSlot=Hammer?TEXT("hammer_heads"):TEXT("blade_1"),RuneSlot=ColdSteelFrostRunes::Slot(Definition);
        const auto* Catalog=G->ModifiableWeapon(Definition);Check(Catalog!=nullptr,Definition+TEXT(" workbench catalog"));if(!Catalog)continue;
        const auto* Parts=Catalog->Options.Find(PartSlot);const auto* Runes=Catalog->Options.Find(RuneSlot);
        const auto* Materials=Catalog->Options.Find(TEXT("blade_material"));
        Check(Parts&&Runes&&Materials,Definition+TEXT(" material and rune categories"));if(!Parts||!Runes||!Materials)continue;
        Check(Catalog->Allowed.Contains(RuneSlot)&&Catalog->Allowed.Contains(TEXT("blade_material")),Definition+TEXT(" visible workbench categories"));
        const bool Crystal=Definition==TEXT("ue_frost_crystal_sword"),Highland=Definition==TEXT("ue_highland_claymore");
        TArray<FString> Finishes=Crystal?TArray<FString>{TEXT("false"),TEXT("red_magic_crystal"),TEXT("high_energy_magic_crystal")}:Common;
        if(RuneSword)Finishes.Append({TEXT("frost_crystal"),TEXT("time_sand_gold")});
        if(Highland)Finishes.Append({TEXT("blackthorn_steel"),TEXT("whitehart_mithril")});
        Check(Materials->Num()==Finishes.Num(),Definition+TEXT(" complete visible material list"));
        for(const auto& Finish:Finishes)Check(G->Option(Definition,TEXT("blade_material"),Finish)!=nullptr,Definition+TEXT(" selectable finish ")+Finish);
        const FString IconDirectory=FPaths::ProjectContentDir()/TEXT("ColdSteelData/AttachmentIcons20260913");
        for(const FString& Slot:{RuneSlot,FString(TEXT("blade_material"))})for(const auto& O:Catalog->Options.FindChecked(Slot))
        {
            if(O.Id==TEXT("false"))continue;
            const FString IconKey=(Slot==RuneSlot?TEXT("blade_2_"):TEXT("blade_material_"))+O.Id;
            Check(FPaths::FileExists(IconDirectory/(Definition+TEXT("_")+IconKey+TEXT(".png")))||FPaths::FileExists(IconDirectory/(IconKey+TEXT(".png"))),
                Definition+TEXT(" workbench icon ")+O.Id);
        }
        Finishes.Add(TEXT("false"));
        for(const auto& Special:{TEXT("red_magic_crystal"),TEXT("high_energy_magic_crystal"),TEXT("blackthorn_steel"),TEXT("whitehart_mithril")})
        {
            const FString Id=Special;
            const bool Eligible=(Id==TEXT("red_magic_crystal")||Id==TEXT("high_energy_magic_crystal"))?Crystal:Highland;
            Check((G->Option(Definition,TEXT("blade_material"),Id)!=nullptr)==Eligible,Definition+TEXT(" special restriction ")+Id);
            if(!Eligible)continue;
            FGunsmithParts Selection;Selection.Add(TEXT("blade_material"),Id);
            const auto M=G->Calculate(Definition,Selection).Melee;
            const bool Correct=Id==TEXT("red_magic_crystal")?FMath::IsNearlyEqual(M.HitHealthReturnRatio,.05)&&FMath::IsNearlyEqual(M.PhysicalDamage,1.1):
                Id==TEXT("high_energy_magic_crystal")?FMath::IsNearlyEqual(M.HitManaReturnRatio,.1)&&FMath::IsNearlyEqual(M.MagicDamage,1.1):
                Id==TEXT("blackthorn_steel")?FMath::IsNearlyEqual(M.MeleeCriticalChanceAdd,25.):FMath::IsNearlyEqual(M.MeleeCriticalDamageBonus,.5);
            Check(Correct,Definition+TEXT(" exclusive material stat aggregation ")+Id);
        }
        for(const auto& Private:{TEXT("frost_crystal"),TEXT("time_sand_gold")})
        {
            Check((G->Option(Definition,TEXT("blade_material"),Private)!=nullptr)==RuneSword,Definition+TEXT(" legendary restriction ")+Private);
            if(RuneSword)Check(ColdSteelModification::Tier(Definition,TEXT("blade_material"),Private)==EGunsmithModificationTier::Legendary,Definition+TEXT(" legendary UI tier ")+Private);
        }
        // Check the real modifier aggregation, including hammer-specific JSON parsing.
        for(int32 Index=1;!Crystal&&Index<Common.Num();++Index)
        {
            FGunsmithParts Selection;Selection.Add(TEXT("blade_material"),Common[Index]);
            const auto M=G->Calculate(Definition,Selection).Melee;bool Correct=false;
            switch(Index)
            {
            case 1:Correct=FMath::IsNearlyEqual(M.PhysicalDamage,1.1)&&FMath::IsNearlyEqual(M.Stamina,.95);break;
            case 2:Correct=FMath::IsNearlyEqual(M.BlockStamina,.8)&&FMath::IsNearlyEqual(M.ToughnessDamage,1.15);break;
            case 3:Correct=FMath::IsNearlyEqual(M.AttackSpeed,1.1)&&FMath::IsNearlyEqual(M.Stamina,.9)&&FMath::IsNearlyEqual(M.PhysicalDamage,.95);break;
            case 4:Correct=FMath::IsNearlyEqual(M.MeleeCriticalChanceAdd,10.)&&FMath::IsNearlyEqual(M.MeleeCriticalDamageBonus,.2)&&FMath::IsNearlyEqual(M.Stamina,1.1);break;
            case 5:Correct=FMath::IsNearlyEqual(M.PhysicalDamage,1.15)&&FMath::IsNearlyEqual(M.ToughnessDamage,1.25)&&FMath::IsNearlyEqual(M.AttackSpeed,.9);break;
            }
            Check(Correct,Definition+TEXT(" material stat aggregation ")+Common[Index]);
        }
        TArray<FString> Guards={TEXT("false")};if(RuneSword){Guards.Reset();for(const auto& O:Catalog->Options.FindChecked(TEXT("guard")))Guards.Add(O.Id);}
        const int32 Start=Cases;
        for(const auto& Part:*Parts)for(const auto& Guard:Guards)
        {
            auto* Actor=World->SpawnActor<AActor>();auto* Root=NewObject<UStaticMeshComponent>(Actor);
            Actor->SetRootComponent(Root);Actor->AddInstanceComponent(Root);Root->RegisterComponent();
            for(const auto& Rune:*Runes)
            {
            TMap<FName,FString> PreviousKeys;
            const FString ExpectedMask=TEXT("T_Mask_")+((Definition==TEXT("ue_frost_crystal_sword")&&(Rune.Id==TEXT("false")||Rune.Id==ColdSteelFrostRunes::SpiritBurst))?FString(TEXT("erosion_rune")):Rune.Id);
            for(int32 Step=0;Step<Finishes.Num();++Step)
            {
                const auto& Finish=Finishes[Step];const uint8 Mode=Finish==TEXT("false")?0:
                    Crystal?uint8(7+Step):Highland&&Step>=Common.Num()?uint8(10+Step-Common.Num()):uint8(Step);
                const FString Label=Definition+TEXT("/")+Part.Id+TEXT("/")+Guard+TEXT("/")+Rune.Id+TEXT("/")+Finish;
                TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
                auto Installed=MakeShared<FJsonObject>();Installed->SetStringField(PartSlot,Part.Id);Installed->SetStringField(RuneSlot,Rune.Id);
                Installed->SetStringField(TEXT("blade_material"),Finish);if(RuneSword)Installed->SetStringField(TEXT("guard"),Guard);
                Data->SetObjectField(TEXT("gunsmith_parts"),Installed);Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));++Cases;
                Check(G->Installed(Item).FindRef(TEXT("blade_material"))==(Mode?Finish:FString()),Label+TEXT(" normalize"));
                Check(ColdSteelModularSword::BladeFinishMode(Item)==Mode,Label+TEXT(" mode"));
                if(!ColdSteelModularSword::Apply(Root,Item)){Check(false,Label+TEXT(" assembly"));continue;}
                int32 Carriers=0,LocalRunes=0,ObserverRunes=0;
                for(auto* Source:ColdSteelModularSword::Components(Root))
                {
                    const bool Carrier=ColdSteelModularSword::IsBladeFinishCarrier(Source,Item);
                    const bool GuardRoot=RuneSword&&Source->ComponentHasTag(TEXT("SwordSlot=guard"));
                    FName Slot;for(const auto& Tag:Source->ComponentTags)if(Tag.ToString().StartsWith(TEXT("SwordSlot="))){Slot=Tag;break;}
                    const FString SurfaceLabel=Label+TEXT("/")+Slot.ToString();
                    LocalRunes+=CheckRune(Source,SurfaceLabel+TEXT(" local"),ExpectedMask);
                    FFPSBodyAttachment Description;FPSBodyRuneVisual::Capture(Source,&Item,Description);
                    Check(Description.BladeFinishMode==(Carrier?Mode:0)&&Description.bBladeFinishGuardRoot==GuardRoot,SurfaceLabel+TEXT(" capture"));
                    int32 Surfaces=0;
                    for(int32 Index=0;Index<Source->GetNumMaterials();++Index)
                    {
                        float Value=0.f;if(!Scalar(Source->GetMaterial(Index),TEXT("BladeFinishMode"),Value))continue;
                        ++Surfaces;Check(FMath::IsNearlyEqual(Value,float(Carrier?Mode:0)),SurfaceLabel+TEXT(" local finish and ornament scope"));
                    }
                    if(Carrier){++Carriers;Check(Surfaces>0,SurfaceLabel+TEXT(" finish capable"));}
                    if(!Carrier&&Description.RuneDefinition.IsEmpty())continue;
                    TArray<uint8> Bytes;
                    {FMemoryWriter Writer(Bytes);FObjectAndNameAsStringProxyArchive Ar(Writer,false);FFPSBodyAttachment::StaticStruct()->SerializeItem(Ar,&Description,nullptr);}
                    FFPSBodyAttachment Read;
                    {FMemoryReader Reader(Bytes);FObjectAndNameAsStringProxyArchive Ar(Reader,true);FFPSBodyAttachment::StaticStruct()->SerializeItem(Ar,&Read,nullptr);}
                    const FString Key=FPSBodyRuneVisual::Key(Read);
                    Check(Key==FPSBodyRuneVisual::Key(Description)&&Read.BladeFinishMode==Description.BladeFinishMode,SurfaceLabel+TEXT(" snapshot roundtrip"));
                    if(Carrier&&Step>0)Check(PreviousKeys.FindRef(Slot)!=Key,SurfaceLabel+TEXT(" cache invalidation"));PreviousKeys.Add(Slot,Key);
                    auto* Remote=NewObject<UStaticMeshComponent>(Actor);Actor->AddInstanceComponent(Remote);Remote->SetStaticMesh(Source->GetStaticMesh());
                    for(int32 Index=0;Index<Source->GetNumMaterials();++Index)
                    {
                        UMaterialInterface* M=Source->GetMaterial(Index);while(auto* MID=Cast<UMaterialInstanceDynamic>(M))M=MID->Parent;Remote->SetMaterial(Index,M);
                    }
                    FPSBodyRuneVisual::Apply(Remote,Read);ObserverRunes+=CheckRune(Remote,SurfaceLabel+TEXT(" observer"),ExpectedMask);
                    for(int32 Index=0;Index<Source->GetNumMaterials();++Index)
                    {
                        float Local=0.f,Observer=0.f;if(!Scalar(Source->GetMaterial(Index),TEXT("BladeFinishMode"),Local))continue;
                        Check(Scalar(Remote->GetMaterial(Index),TEXT("BladeFinishMode"),Observer)&&FMath::IsNearlyEqual(Local,Observer),SurfaceLabel+TEXT(" observer finish"));
                    }
                    Actor->RemoveInstanceComponent(Remote);Remote->DestroyComponent();
                }
                const bool HasRune=Rune.Id!=TEXT("false")||Definition==TEXT("ue_frost_crystal_sword");
                Check(Carriers==(RuneSword?2:1),Label+TEXT(" carrier count"));
                Check((LocalRunes>0)==HasRune,Label+TEXT(" selected rune mounted"));
                Check(LocalRunes==ObserverRunes,Label+TEXT(" observer rune parity"));
            }
            }
            ColdSteelModularSword::Clear(Root);Actor->Destroy();
        }
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("weapon"),Definition);Row->SetNumberField(TEXT("parts"),Parts->Num());
        Row->SetNumberField(TEXT("rune_states"),Runes->Num());Row->SetNumberField(TEXT("material_states"),Materials->Num());Row->SetNumberField(TEXT("cases"),Cases-Start);
        Weapons.Add(MakeShared<FJsonValueObject>(Row));UE_LOG(LogTemp,Display,TEXT("SHARED_FINISH_WEAPON %s cases=%d"),*Definition,Cases-Start);
    }
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("cases"),Cases);Report->SetNumberField(TEXT("checks"),Checks);
    Report->SetNumberField(TEXT("failures"),Failures);Report->SetArrayField(TEXT("errors"),Errors);Report->SetArrayField(TEXT("weapons"),Weapons);
    Report->SetBoolField(TEXT("actual_network_transport"),false);Report->SetBoolField(TEXT("visual_rendering"),false);
    FString Output=FPaths::ProjectSavedDir()/TEXT("SharedTwoHandFinishAudit.json");FParse::Value(*Params,TEXT("Output="),Output);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Output);
    UE_LOG(LogTemp,Display,TEXT("SHARED_FINISH_AUDIT cases=%d checks=%d failures=%d report=%s"),Cases,Checks,Failures,*Output);
    GI->Shutdown();GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failures?1:0;
}
