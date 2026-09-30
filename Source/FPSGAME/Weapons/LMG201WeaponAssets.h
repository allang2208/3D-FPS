#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace LMG201WeaponAssets
{
inline constexpr const TCHAR* Definition=TEXT("ue_lmg201");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10.SK_LMG201_Cover10");
inline constexpr int32 FireVariantCount = 4;
inline constexpr const TCHAR* ClothBoxId=TEXT("lmg201_cloth_box");
inline constexpr const TCHAR* DrumMeshPath=TEXT("/Game/Weapons/LMG201/Drum46/SM_LMG201_LargeDrum");
inline FString DrumAnimationPath(const TCHAR* Family,const TCHAR* Clip)
{
    return FString::Printf(TEXT("/Game/Weapons/LMG201/Drum46/Animations/%s/A_LMG201_%s_drum_%s"),Family,Family,Clip);
}
// ClothReload44 source-time contacts (reference video phases; see SourceAssets ClothReload44).
inline constexpr float ClothCoverOpen=1.12f,ClothBoxOut=2.10f,ClothOldHidden=2.45f,ClothNewVisible=2.80f;
inline constexpr float ClothBoxSeat=3.35f,ClothBeltSeat=4.78f,ClothCoverClose=5.22f;
inline constexpr float ClothDuration=6.2f,ClothReturnStart=5.45f,ClothTrayPull=1.74f;
// The empty reload has no spent belt in the tray: the hand leaves the lid for the
// pouch directly and the remaining actions spread over the same 6.2 s clip. Map a
// normal-clip source time onto the empty clip (ClothReload44 author_motion.py EMPTY_KNOTS).
inline float ClothEventTime(float NormalSeconds,bool Empty)
{
    constexpr float From[]={1.46f,2.f,ClothReturnStart,ClothDuration},To[]={1.46f,1.8f,5.46f,ClothDuration};
    if(!Empty||NormalSeconds<=From[0])return NormalSeconds;
    for(int32 I=1;I<UE_ARRAY_COUNT(From);++I)
        if(NormalSeconds<=From[I])
            return FMath::Lerp(To[I-1],To[I],(NormalSeconds-From[I-1])/(From[I]-From[I-1]));
    return NormalSeconds;
}
inline FString ClothAnimationPath(const TCHAR* Family,const TCHAR* Clip)
{
    return FString::Printf(TEXT("/Game/Weapons/LMG201/ClothReload44/Animations/%s/A_LMG201_%s_%s"),Family,Family,Clip);
}
inline FString FireSoundPath(int32 Variant)
{
    return FString::Printf(TEXT("/Game/Weapons/LMG201/FireAudio01/S_LMG201_Fire_%02d.S_LMG201_Fire_%02d"),Variant,Variant);
}
inline bool Matches(const USkeletalMeshComponent* Mesh)
{
    return Mesh&&Mesh->GetSkeletalMeshAsset()&&Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/LMG201/"));
}
inline FString AnimationPath(const TCHAR* Clip)
{
    if(FCString::Strcmp(Clip,TEXT("reload"))==0||FCString::Strcmp(Clip,TEXT("reload_empty"))==0)
        return FString::Printf(TEXT("/Game/Weapons/LMG201/Magazine24/Animations/base/A_LMG201_base_%s"),Clip);
    return FString::Printf(TEXT("/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_%s.A_LMG201_%s"),Clip,Clip);
}
// The new cloth feed has its own identity. Retired metal-box sections and old
// saved attachment ids remain retired; factory magazines are still available.
inline void SetMagazineSections(USkeletalMeshComponent* Mesh,int32& CachedVisibility,
    bool Cloth=false,bool Reload=false,bool Empty=false,float SourceTime=0.f,int32 Rounds=1,bool Drum=false)
{
    const bool OldBox=Cloth&&(!Reload||SourceTime<ClothEventTime(ClothOldHidden,Empty));
    const bool NewBox=Cloth&&Reload&&SourceTime>=ClothEventTime(ClothNewVisible,Empty);
    const bool OldBelt=OldBox&&Rounds>0&&(!Reload||!Empty);
    const int32 State=1+(Cloth?2:0)+(OldBox?4:0)+(NewBox?8:0)+(OldBelt?16:0)+(Drum?32:0);
    if(!Matches(Mesh)||CachedVisibility==State)return;
    const auto* Asset=Mesh->GetSkeletalMeshAsset();
    const auto* Render=Asset->GetResourceForRendering();
    if(!Render)return;
    for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString();
            if(Name.StartsWith(TEXT("M_LMG201_Magazine")))Mesh->ShowMaterialSection(M,S,!Cloth&&!Drum,L);
            else if(Name.StartsWith(TEXT("M_LMG201_Cloth33__OldBox")))Mesh->ShowMaterialSection(M,S,OldBox,L);
            else if(Name.StartsWith(TEXT("M_LMG201_Cloth33__NewBox")))Mesh->ShowMaterialSection(M,S,NewBox,L);
            else if(Name.StartsWith(TEXT("M_LMG201_Cloth33__OldBelt")))Mesh->ShowMaterialSection(M,S,OldBelt,L);
            else if(Name.StartsWith(TEXT("M_LMG201_Cloth33__NewBelt")))Mesh->ShowMaterialSection(M,S,NewBox,L);
            else if(Name.StartsWith(TEXT("M_LMG201_Feed__")))Mesh->ShowMaterialSection(M,S,false,L);
        }
    CachedVisibility=State;
}
inline FString PartPath(const TCHAR* Part)
{
    return FString::Printf(TEXT("/Game/Weapons/LMG201/Production20260927/SM_LMG201_%s"),Part);
}
inline FString SightPath(int32 Index){return PartPath(Index==0?TEXT("RearSight"):TEXT("FrontSight"));}
inline FString AttachmentPath(const FString& Key)
{
    return TEXT("/Game/Weapons/LMG201/Production20260927/Attachments/SM_LMG201_")+Key;
}
// Bone-local metres, matching Blender FIT with FBX's reflected Y.
// Reference02 saddles place the folded leaves above the rail/barrel crown.
inline const FVector SightHinges[]={FVector(.0008,-.04252,.0855),FVector(.0008,.54212,.0648)};
inline const FVector MuzzleMount(.0008,.6877,.04866);
inline FTransform OpticMount(const FString& Variant)
{
    // WPN_root space: the fixed rear rail is separate from LMG201_Cover.
    // Keep this parent during reloads; these mounts are not on the moving lid.
    const double Along=Variant==TEXT("lpvo_1_6x")?.075:Variant==TEXT("prism_scope_2x")?.050:.035;
    return FTransform(FQuat(FVector::UpVector,PI*.5),FVector(.0008,Along,.082),FVector(.01));
}
// Static-mesh component local centimetres; each leg has its own hinge.
inline const FVector BipodHingeCm(.08,46.498,-1.398);
inline const FVector BipodPivotsCm[]={FVector(1.356,46.498,-1.398),FVector(-1.196,46.498,-1.398)};
inline const FVector BipodFeetCm[]={FVector(9.28,.696,-16.008),FVector(-9.338,.696,-16.008)};
}
