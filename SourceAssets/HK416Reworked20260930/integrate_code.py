"""Scoped HK416 runtime hooks; retain all unrelated current source edits."""
from pathlib import Path
import shutil
O=Path(__file__).parent;P=O.parents[1]
def edit(path,fn):
    file=P/path;old=file.read_text(encoding='utf-8-sig');new=fn(old)
    if old==new:return
    backup=O/'CodeBefore'/path;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(file,backup)
    file.write_text(new,encoding='utf-8')
def includes(text,*headers):
    at=text.index('\n')+1
    add=''.join('#include "'+header+'"\n' for header in headers if '#include "'+header+'"' not in text)
    return text[:at]+add+text[at:]
def insert(text,anchor,body):
    if body in text:return text
    if anchor not in text:raise RuntimeError('Missing integration anchor '+anchor[:90])
    return text.replace(anchor,anchor+body,1)

def character(t):
    t=includes(t,'Weapons/HK416WeaponAssets.h','Weapons/HK416Attachments.h','Engine/StaticMesh.h','Engine/StaticMeshSocket.h')
    old='TEXT("/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416"), nullptr, LOAD_NoWarn)'
    t=t.replace(old,'IsHK416Weapon() ? HK416WeaponAssets::MeshPath : '+old)
    t=t.replace('ADSRearEyeDistance = 12.0f;','ADSRearEyeDistance = IsHK416Weapon() ? 18.f : 12.0f;')
    t=insert(t,'UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)\n{','\n    if (IsHK416Weapon())\n    {\n        FString Clip(AssetName); Clip.RemoveFromStart(TEXT("A_AKM_"));\n        if (Clip.StartsWith(TEXT("equip"))) Clip=TEXT("equip_charge");\n        return LoadObject<UAnimSequence>(nullptr,*HK416WeaponAssets::AnimationPath(*Clip));\n    }')
    t=insert(t,'UAnimSequence* AFPSGAMECharacter::RifleQuickCombatClip(EM4SprintGrip Grip)\n{','\n    if (IsHK416Weapon()) return LoadObject<UAnimSequence>(nullptr,*HK416WeaponAssets::AnimationPath(TEXT("quick_melee"),Grip==EM4SprintGrip::Vertical?TEXT("vertical"):TEXT("base")));')
    t=t.replace('DrumReloadAnimation=SVDWeaponAssets::Matches(AKMViewmodel)?nullptr:', 'DrumReloadAnimation=(IsHK416Weapon()||SVDWeaponAssets::Matches(AKMViewmodel))?nullptr:')
    t=t.replace('DrumReloadEmptyAnimation=SVDWeaponAssets::Matches(AKMViewmodel)?nullptr:', 'DrumReloadEmptyAnimation=(IsHK416Weapon()||SVDWeaponAssets::Matches(AKMViewmodel))?nullptr:')
    t=insert(t,'        const FTransform Mount=HolographicMount*Root;', '''
        if (IsHK416Weapon() && HolographicOptic && HolographicOptic->GetStaticMesh())
        {
            const auto* Mesh=HolographicOptic->GetStaticMesh();
            const auto* R=Mesh->FindSocket(TEXT("SightRear"));
            const auto* F=Mesh->FindSocket(TEXT("SightFront"));
            const auto* U=Mesh->FindSocket(TEXT("SightUp"));
            if (R&&F&&U)
            {
                Rear=Mount.TransformPosition(R->RelativeLocation)*ViewmodelScale;
                Front=Mount.TransformPosition(F->RelativeLocation)*ViewmodelScale;
                SightUp=(Mount.TransformPosition(U->RelativeLocation)*ViewmodelScale-Rear).GetSafeNormal();
            }
        }
        else
        {''')
    t=t.replace('        SightUp=Mount.GetRotation().RotateVector(FVector::UpVector);\n    }','        SightUp=Mount.GetRotation().RotateVector(FVector::UpVector);\n        }\n    }',1)
    return t
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
edit('Source/FPSGAME/FPSGAMECharacter.h',lambda t:insert(t,'    bool IsG18Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_g18"); }','\n    bool IsHK416Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_hk416"); }'))

# Definition-aware presentation participates in inventory, pickups and the
# bounded asynchronous icon pipeline. M4 only supplies the animation family.
for path in ['Source/FPSGAME/FPSGAMECharacterProfile.cpp','Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp',
 'Source/FPSGAME/UI/ColdSteelPickupStudio.cpp','Source/FPSGAME/UI/M4StandalonePreview.cpp','Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp']:
    def broaden(t):
        for expression in ('I->Definition','I.Definition','Item.Definition'):
            t=t.replace(expression+'==TEXT("ue_m4a1")','('+expression+'==TEXT("ue_m4a1")||'+expression+'==TEXT("ue_hk416"))')
            t=t.replace(expression+'!=TEXT("ue_m4a1")',expression+'!=TEXT("ue_m4a1")&&'+expression+'!=TEXT("ue_hk416")')
        return t
    edit(path,broaden)

def optic(t):
    t=includes(t,'HK416WeaponAssets.h','HK416Attachments.h')
    return insert(t,'void AFPSGAMECharacter::SetGunsmithOpticVariant(const FString& Variant)\n{','''
    if (IsHK416Weapon())
    {
        const bool Enabled=bInventoryWeaponReady&&Variant==TEXT("holographic");
        HolographicOptic=HK416Attachments::Configure(this,AKMViewmodel,HolographicOptic,TEXT("holographic"),Enabled);
        if (AKMOpticBridge) AKMOpticBridge->SetVisibility(false);
        if (LPVORing) LPVORing->SetVisibility(false);
        if (bHolographicOptic!=Enabled||OpticVariant!=Variant) bSightCalibrated=false;
        bHolographicOptic=Enabled;OpticVariant=Enabled?Variant:FString();LPVOMagnification=1.f;
        if (HolographicOptic) HolographicMount=HolographicOptic->GetRelativeTransform();
        return;
    }
''')
edit('Source/FPSGAME/Weapons/M4GunsmithVisual.cpp',optic)
def muzzle(t):
    t=includes(t,'HK416WeaponAssets.h','HK416Attachments.h','Engine/StaticMeshSocket.h')
    return insert(t,'void AFPSGAMECharacter::SetGunsmithMuzzle(const FString& Variant)\n{','''
    if (IsHK416Weapon())
    {
        const bool Enabled=bInventoryWeaponReady&&Variant==TEXT("true");
        MuzzleAttachment=HK416Attachments::Configure(this,AKMViewmodel,MuzzleAttachment,TEXT("suppressor"),Enabled);
        MuzzleVariant=Enabled?Variant:FString();
        if (Enabled&&MuzzleAttachment&&MuzzleAttachment->GetStaticMesh())
        {
            const auto* Tip=MuzzleAttachment->GetStaticMesh()->FindSocket(TEXT("Muzzle"));
            const auto* Guide=MuzzleAttachment->GetStaticMesh()->FindSocket(TEXT("AimGuide"));
            if (Tip&&Guide) { MuzzleLocalTip=Tip->RelativeLocation;MuzzleLocalAxis=(Guide->RelativeLocation-Tip->RelativeLocation).GetSafeNormal(); }
        }
        if (!SuppressedFireSound) SuppressedFireSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed"));
        return;
    }
''')
edit('Source/FPSGAME/Weapons/M4MuzzleVisual.cpp',muzzle)
def vertical(t):
    t=includes(t,'HK416WeaponAssets.h','HK416Attachments.h')
    t=t.replace('const FString Path=SVDWeaponAssets::Matches(AKMViewmodel)?','const FString Path=IsHK416Weapon()?HK416WeaponAssets::AnimationPath(FCString::Strcmp(Pair.Value,TEXT("equip"))==0?TEXT("equip_charge"):Pair.Value,TEXT("vertical")):SVDWeaponAssets::Matches(AKMViewmodel)?',1)
    return insert(t,'void AFPSGAMECharacter::SetVerticalForegrip(bool bEnabled)\n{','\n    if (IsHK416Weapon()) { VerticalForegrip=HK416Attachments::Configure(this,AKMViewmodel,VerticalForegrip,TEXT("vertical"),bEnabled&&bInventoryWeaponReady); return; }\n')
edit('Source/FPSGAME/Weapons/M4VerticalForegrip.cpp',vertical)
def tactical(t):
    t=includes(t,'HK416WeaponAssets.h','HK416Attachments.h')
    t=t.replace('const FString Path=Family==TEXT("LMG201")?', 'const FString Path=Family==TEXT("HK416")?HK416WeaponAssets::AttachmentPath(Variant):Family==TEXT("LMG201")?',1)
    t=t.replace('if(!Pistol&&!ASH&&Family!=TEXT("LMG201")','if(Family!=TEXT("HK416")&&!Pistol&&!ASH&&Family!=TEXT("LMG201")')
    t=t.replace('Body->SetRelativeTransform(ASH?','Body->SetRelativeTransform(Family==TEXT("HK416")?HK416Attachments::ReferenceMount(Rifle):ASH?',1)
    t=t.replace('const FString Family=', 'const FString Family=IsHK416Weapon()?TEXT("HK416"):',1)
    return t
edit('Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp',tactical)
def sprint(t):
    t=includes(t,'HK416WeaponAssets.h')
    t=insert(t,'    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());','\n    const bool bHK416=Character&&Character->IsHK416Weapon();\n    const bool bHadHK416=!Clips.IsEmpty()&&Clips[0]&&Clips[0]->GetPathName().StartsWith(TEXT("/Game/Weapons/HK416/"));')
    t=t.replace('if (CurrentWeapon != Weapon || bA762!=bHadA762 || bLMG!=bHadLMG)','if (CurrentWeapon != Weapon || bA762!=bHadA762 || bLMG!=bHadLMG || bHK416!=bHadHK416)')
    return insert(t,'    if (!bEnabled || !Clips.IsEmpty()) return;','''
    if (bHK416)
    {
        for (const TCHAR* Family:{TEXT("base"),TEXT("base"),TEXT("base"),TEXT("vertical"),TEXT("base"),TEXT("base")})
            for (const TCHAR* Kind:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})
                Clips.Add(LoadObject<UAnimSequence>(nullptr,*HK416WeaponAssets::AnimationPath(Kind,Family)));
        return;
    }
''')
edit('Source/FPSGAME/Weapons/M4TacticalSprintComponent.cpp',sprint)
def icon(t):
    t=includes(t,'../Weapons/HK416WeaponAssets.h')
    t=t.replace('else if(D==TEXT("ue_m4a1"))\n', 'else if(D==HK416WeaponAssets::Definition){Add(HK416WeaponAssets::MeshPath,true);Add(HK416WeaponAssets::AnimationPath(TEXT("idle")),true);}\n        else if(D==TEXT("ue_m4a1"))\n',1)
    t=insert(t,'            if(Key.IsEmpty()||Key==TEXT("false")||Key==TEXT("factory"))continue;','''
            if(D==HK416WeaponAssets::Definition)
            {
                if(Part.Key==TEXT("muzzle"))Key=TEXT("suppressor");
                if(Part.Key==TEXT("underbarrel"))Key=TEXT("vertical");
                Add(HK416WeaponAssets::AttachmentPath(Key),true);
                continue;
            }
''')
    return t
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp',icon)
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',lambda t:t.replace('{TEXT("ue_g18"), TEXT("ue_svd"),','{TEXT("ue_hk416"), TEXT("ue_g18"), TEXT("ue_svd"),',1))
edit('Config/DefaultGame.ini',lambda t:t if '+DirectoriesToAlwaysCook=(Path="/Game/Weapons/HK416")' in t else t.replace('+DirectoriesToAlwaysCook=(Path="/Game/Weapons/G18")','+DirectoriesToAlwaysCook=(Path="/Game/Weapons/G18")\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/HK416")',1))
print('HK416_RUNTIME_INTEGRATION_WRITTEN')
