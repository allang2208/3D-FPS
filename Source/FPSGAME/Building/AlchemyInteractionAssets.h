#pragma once
#include "CoreMinimal.h"
#include "UObject/SoftObjectPath.h"

// Shared by authority, replicated presentation and client busy time.
namespace AlchemyInteraction
{
inline constexpr float PourSeconds=3.3f;
inline constexpr float BottleSeconds=4.6f;
inline constexpr float FlowStart=1.15f,FlowEnd=2.15f;
inline constexpr int32 HoverStencil=229;
inline const FVector HeatControl(205,-48,94.43);
inline FSoftObjectPath Asset(const TCHAR* Name)
{const FString N(Name);return FSoftObjectPath(TEXT("/Game/Building/PotionWorkbench20261015/InteractionV7/")+N+TEXT(".")+N);}
inline FSoftObjectPath BottlingAsset(const TCHAR* Name)
{const FString N(Name);return FSoftObjectPath(TEXT("/Game/Building/PotionWorkbench20261015/InteractionV10/")+N+TEXT(".")+N);}
inline float Smooth(float X){return FMath::SmoothStep(0.f,1.f,X);}
inline float Poured(float T){return Smooth((T-FlowStart)/(FlowEnd-FlowStart));}
struct FReagent {const TCHAR* Item;const TCHAR* Mesh;float Mouth;float Height;bool Granular;};
inline const FReagent Reagents[]={
    {TEXT("alchemy_pure_base_fluid"),TEXT("BaseFluid"),11.33f,12.3475f,false},
    {TEXT("alchemy_redvein_extract"),TEXT("RedRoot"),8.95f,12.01f,false},
    {TEXT("alchemy_bluemarrow_crystals"),TEXT("BlueFungus"),5.3f,6.095f,true},
    {TEXT("alchemy_active_catalyst"),TEXT("Catalyst"),5.4f,6.2215f,true}};
inline const FReagent* Reagent(const FString& Item)
{for(const auto& R:Reagents)if(Item==R.Item)return &R;return nullptr;}
inline FSoftObjectPath ReagentAsset(const FReagent& R,const TCHAR* Suffix)
{return Asset(*(FString(TEXT("SM_Alchemy"))+R.Mesh+Suffix));}
}
