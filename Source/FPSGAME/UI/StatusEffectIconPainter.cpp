#include "StatusEffectIconPainter.h"
#include "StatusEffectsComponent.h"
#include "ColdSteelUIStyle.h"
#include "Rendering/DrawElementTypes.h"

namespace
{
enum class EGlyph : uint8
{
    Dragon, Phoenix, Shield, Drop, Skull, Eye, Spiral, Reticle, Diamond, Star, Hourglass,
    Snow, Flame, Chain, Stride, Leaf, Flask, Lightning, Stone, Ledger, Pick, Mountain,
    Wave, Antlers, Music, Root, Armor, Lotus, Taiji, Crystal, Cloud, Arrow, Bone, Fang, Sun
};
struct FIcon { EGlyph Glyph; uint8 Variant=0; };
FIcon ResolveIcon(const FStatusEffectView& V)
{
    // Explicit identities: related effects share an engraved motif with different secondary marks.
    static const TMap<FName,FIcon> Icons={
        {TEXT("tangDragonMight"),{EGlyph::Dragon,0}}, {TEXT("tangPhoenixDance"),{EGlyph::Phoenix,0}},
        {TEXT("physicalVulnerability"),{EGlyph::Armor,1}}, {TEXT("tigerRoar"),{EGlyph::Fang,1}},
        {TEXT("fountainBlessing"),{EGlyph::Drop,0}}, {TEXT("sanityCollapse"),{EGlyph::Eye,1}},
        {TEXT("composure"),{EGlyph::Reticle,0}}, {TEXT("wager"),{EGlyph::Diamond,0}},
        {TEXT("berserk"),{EGlyph::Fang,0}}, {TEXT("blind"),{EGlyph::Eye,2}},
        {TEXT("stun"),{EGlyph::Spiral,0}}, {TEXT("poison"),{EGlyph::Skull,0}},
        {TEXT("minePoison"),{EGlyph::Cloud,1}}, {TEXT("slow"),{EGlyph::Stride,1}},
        {TEXT("waxSealSlow"),{EGlyph::Flame,2}}, {TEXT("buff"),{EGlyph::Star,0}},
        {TEXT("shield"),{EGlyph::Shield,0}}, {TEXT("bleed"),{EGlyph::Drop,1}},
        {TEXT("corrosion"),{EGlyph::Flask,1}}, {TEXT("magicVulnerability"),{EGlyph::Crystal,1}},
        {TEXT("droneVulnerability"),{EGlyph::Reticle,2}}, {TEXT("marbleHeal"),{EGlyph::Stone,0}},
        {TEXT("goddessBless"),{EGlyph::Sun,0}}, {TEXT("demonPrayer"),{EGlyph::Flame,1}},
        {TEXT("fear"),{EGlyph::Skull,1}}, {TEXT("holyRenewal"),{EGlyph::Sun,1}},
        {TEXT("holyWard"),{EGlyph::Shield,1}}, {TEXT("chainSpell"),{EGlyph::Chain,0}},
        {TEXT("weaponHaste"),{EGlyph::Arrow,0}}, {TEXT("chill"),{EGlyph::Snow,0}},
        {TEXT("burn"),{EGlyph::Flame,0}}, {TEXT("frozen"),{EGlyph::Crystal,0}},
        {TEXT("petrified"),{EGlyph::Stone,1}}, {TEXT("flameArmor"),{EGlyph::Armor,2}}, {TEXT("iceArmor"),{EGlyph::Armor,4}},
        {TEXT("riposteInspiration"),{EGlyph::Arrow,1}}, {TEXT("runeMagicVulnerability"),{EGlyph::Crystal,2}},
        {TEXT("electrified"),{EGlyph::Lightning,0}}, {TEXT("haste"),{EGlyph::Stride,0}},
        {TEXT("inspire"),{EGlyph::Sun,2}}, {TEXT("statusImmune"),{EGlyph::Shield,2}},
        {TEXT("bind"),{EGlyph::Chain,1}}, {TEXT("marked"),{EGlyph::Reticle,1}},
        {TEXT("camelFright"),{EGlyph::Fang,2}}, {TEXT("magicResistanceShred"),{EGlyph::Diamond,1}},
        {TEXT("ginsengHeal"),{EGlyph::Root,0}}, {TEXT("foremanDebtMark"),{EGlyph::Ledger,1}},
        {TEXT("minersGratitude"),{EGlyph::Pick,0}}, {TEXT("minersCadence"),{EGlyph::Pick,1}},
        {TEXT("deepShaftEcho"),{EGlyph::Spiral,1}}, {TEXT("reedLament"),{EGlyph::Leaf,1}},
        {TEXT("bogHunterInstinct"),{EGlyph::Arrow,2}}, {TEXT("hunterBurden"),{EGlyph::Bone,1}},
        {TEXT("druidShelter"),{EGlyph::Leaf,0}}, {TEXT("swampWhisper"),{EGlyph::Spiral,2}},
        {TEXT("wildSap"),{EGlyph::Drop,2}}, {TEXT("marshGasNumbness"),{EGlyph::Cloud,2}},
        {TEXT("livingRootWard"),{EGlyph::Root,1}}, {TEXT("blackwaterChill"),{EGlyph::Snow,1}},
        {TEXT("waterloggedArmor"),{EGlyph::Armor,3}}, {TEXT("graveMurmur"),{EGlyph::Stone,2}},
        {TEXT("frogBoneCurse"),{EGlyph::Bone,2}}, {TEXT("witchDistillate"),{EGlyph::Flask,0}},
        {TEXT("bogWitchTonic"),{EGlyph::Flask,2}}, {TEXT("failedWitchBrew"),{EGlyph::Flask,3}},
        {TEXT("crocodileHideWard"),{EGlyph::Armor,0}}, {TEXT("ancientSpell"),{EGlyph::Ledger,0}},
        {TEXT("bloodFury"),{EGlyph::Fang,3}}, {TEXT("cursedArmorShell"),{EGlyph::Shield,3}},
        {TEXT("armorCurse"),{EGlyph::Skull,2}}, {TEXT("steadyMind"),{EGlyph::Leaf,2}},
        {TEXT("madVision"),{EGlyph::Eye,0}}, {TEXT("corpseWaxSeal"),{EGlyph::Flame,3}},
        {TEXT("waxStiffness"),{EGlyph::Chain,2}}, {TEXT("funeralTempo"),{EGlyph::Music,0}},
        {TEXT("discordantEcho"),{EGlyph::Music,1}}, {TEXT("plagueAntiserum"),{EGlyph::Flask,4}},
        {TEXT("plagueExposure"),{EGlyph::Skull,3}}, {TEXT("frostDisorientation"),{EGlyph::Reticle,3}},
        {TEXT("iceBridgePoise"),{EGlyph::Crystal,3}}, {TEXT("iceBridgeNumbness"),{EGlyph::Snow,2}},
        {TEXT("iceBridgeDetourChill"),{EGlyph::Snow,3}}, {TEXT("frostberryVigor"),{EGlyph::Leaf,3}},
        {TEXT("frostberryChill"),{EGlyph::Leaf,4}}, {TEXT("whiteStagStride"),{EGlyph::Antlers,0}},
        {TEXT("whiteStagMercy"),{EGlyph::Antlers,1}}, {TEXT("auroraCadence"),{EGlyph::Wave,0}},
        {TEXT("auroraFrostbite"),{EGlyph::Diamond,2}}, {TEXT("shroudedAurora"),{EGlyph::Wave,1}},
        {TEXT("avalancheBrace"),{EGlyph::Mountain,0}}, {TEXT("crevasseWhispers"),{EGlyph::Mountain,1}},
        {TEXT("glacierLungs"),{EGlyph::Cloud,0}}, {TEXT("crevasseNumbness"),{EGlyph::Snow,4}},
        {TEXT("crevasseDetourNumbness"),{EGlyph::Cloud,3}}, {TEXT("frozenSanctuary"),{EGlyph::Shield,4}},
        {TEXT("rejectedPrayer"),{EGlyph::Lotus,1}}, {TEXT("reliquaryBurden"),{EGlyph::Chain,3}},
        {TEXT("drenchedInIcewater"),{EGlyph::Drop,3}}, {TEXT("signalFlamePace"),{EGlyph::Flame,4}},
        {TEXT("blizzardFireguard"),{EGlyph::Flame,5}}, {TEXT("shutterBruise"),{EGlyph::Wave,2}},
        {TEXT("frostSpiritMark"),{EGlyph::Skull,4}}, {TEXT("frostSpiritRage"),{EGlyph::Skull,5}},
        {TEXT("crystalBackflow"),{EGlyph::Crystal,4}}, {TEXT("frostSpiritRejection"),{EGlyph::Skull,6}},
        {TEXT("auroraOmen"),{EGlyph::Star,1}}, {TEXT("falseOmen"),{EGlyph::Star,2}},
        {TEXT("starfallFracture"),{EGlyph::Mountain,2}}, {TEXT("infection"),{EGlyph::Skull,7}},
        {TEXT("observatoryFrostFracture"),{EGlyph::Crystal,5}}, {TEXT("zhenmoField"),{EGlyph::Taiji,0}},
        {TEXT("jingangHigh"),{EGlyph::Lotus,0}}, {TEXT("jingangMiddle"),{EGlyph::Lotus,2}},
        {TEXT("jingangLow"),{EGlyph::Lotus,3}}, {TEXT("jingangLeech"),{EGlyph::Lotus,4}},
        {TEXT("panchiCharge"),{EGlyph::Dragon,1}}, {TEXT("panchiCooldown"),{EGlyph::Hourglass,0}}
    };
    if(V.Type==TEXT("slow") && (V.Name.Contains(TEXT("残")) || V.Icon==TEXT("🦴")))return {EGlyph::Bone,0};
    if(const auto* Icon=Icons.Find(V.Type))return *Icon;
    return {V.Kind==TEXT("debuff")?EGlyph::Diamond:EGlyph::Star,3};
}
}

int32 ColdSteelUI::PaintStatusEffectIcon(const FGeometry& G,FSlateWindowElementList& Out,
    int32 Layer,FVector2D Offset,float Size,const FStatusEffectView& View,const FLinearColor& Tint)
{
    const float S=Size/32.f;
    const auto Icon=ResolveIcon(View);
    const auto Plate=RoundedBrush(FLinearColor::White,5*S,FLinearColor::Transparent,0);
    FSlateDrawElement::MakeBox(Out,Layer,G.ToPaintGeometry(FVector2D(Size),FSlateLayoutTransform(Offset)),&Plate,ESlateDrawEffect::None,Content*Tint);
    auto Stroke=[&](const TArray<FVector2D>& P,const FLinearColor& Color,float Thickness=1.35f)
    {
        TArray<FVector2D> Shadow,Points;
        for(const auto& V:P){Points.Add(Offset+V*S);Shadow.Add(Offset+(V+FVector2D(.45,.65))*S);}
        FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Shadow,ESlateDrawEffect::None,Gray(4,220)*Tint,true,(Thickness+1.1f)*S);
        FSlateDrawElement::MakeLines(Out,Layer+2,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Color*Tint,true,Thickness*S);
    };
    auto Line=[&](std::initializer_list<FVector2D> P){Stroke(TArray<FVector2D>(P),TextPrimary);};
    auto AccentLine=[&](std::initializer_list<FVector2D> P){Stroke(TArray<FVector2D>(P),FMath::Lerp(View.Color,TextPrimary,.32f));};
    auto Arc=[&](FVector2D Center,float R,float A,float B,const FLinearColor& Color)
    {
        TArray<FVector2D> Points;
        for(int32 I=0;I<=20;++I){const float Angle=FMath::Lerp(A,B,I/20.f);Points.Add(Center+FVector2D(FMath::Cos(Angle),FMath::Sin(Angle))*R);}
        Stroke(Points,Color);
    };
    Stroke({{7,1},{25,1},{31,7},{31,25},{25,31},{7,31},{1,25},{1,7},{7,1}},Border,.8f);
    Stroke({{2,11},{2,7},{7,2},{14,2}},TextSecondary,.8f);
    switch(Icon.Glyph)
    {
    case EGlyph::Dragon:
        Line({{8,24},{19,24},{24,20},{20,15},{13,16},{10,12},{14,8},{22,10},{25,8},{23,14},{18,12}});
        Line({{15,8},{12,5},{19,8},{20,5},{23,8}});AccentLine({{9,19},{5,21},{8,25},{6,27}});break;
    case EGlyph::Phoenix:
        Line({{16,26},{13,18},{6,13},{5,7},{12,12},{16,16},{20,12},{27,7},{26,13},{19,18},{16,26}});
        Line({{14,15},{14,9},{17,6},{21,8},{18,10},{18,15}});AccentLine({{10,21},{13,24},{16,27},{19,24},{22,21}});break;
    case EGlyph::Shield:
        Line({{16,5},{25,9},{24,19},{21,24},{16,28},{11,24},{8,19},{7,9},{16,5}});
        AccentLine({{11,16},{15,20},{22,12}});break;
    case EGlyph::Drop:
        Line({{16,5},{9,14},{7,20},{9,25},{13,27},{19,27},{23,25},{25,20},{23,14},{16,5}});
        AccentLine({{11,17},{10,21},{13,24}});break;
    case EGlyph::Skull:
        Line({{10,24},{10,20},{7,18},{7,12},{10,7},{16,5},{22,7},{25,12},{25,18},{22,20},{22,24},{10,24}});
        AccentLine({{10,13},{13,16},{10,17},{10,13}});AccentLine({{22,13},{19,16},{22,17},{22,13}});
        Line({{15,21},{16,18},{17,21}});Line({{13,24},{13,27}});Line({{19,24},{19,27}});break;
    case EGlyph::Eye:
        Line({{4,16},{9,10},{16,8},{23,10},{28,16},{23,22},{16,24},{9,22},{4,16}});
        Arc({16,16},5,0,2*PI,View.Color);if(Icon.Variant)AccentLine({{7,26},{25,6}});break;
    case EGlyph::Spiral:
    {
        TArray<FVector2D> P;for(int32 I=0;I<=44;++I){float A=I*.23f,R=10.f-I*.18f;P.Add(FVector2D(16+FMath::Cos(A)*R,16+FMath::Sin(A)*R));}Stroke(P,TextPrimary);
        AccentLine({{5,7},{8,4},{11,7}});break;
    }
    case EGlyph::Reticle:
        Arc({16,16},8,0,2*PI,TextPrimary);Arc({16,16},2,0,2*PI,View.Color);
        Line({{16,3},{16,10}});Line({{16,22},{16,29}});Line({{3,16},{10,16}});Line({{22,16},{29,16}});break;
    case EGlyph::Diamond:
        Line({{16,4},{27,16},{16,28},{5,16},{16,4}});AccentLine({{16,9},{22,16},{16,23},{10,16},{16,9}});break;
    case EGlyph::Star:
        Line({{16,4},{19,12},{28,16},{19,20},{16,28},{12,20},{4,16},{12,12},{16,4}});
        AccentLine({{16,11},{16,21}});break;
    case EGlyph::Hourglass:
        Line({{7,5},{25,5},{23,11},{18,16},{23,21},{25,27},{7,27},{9,21},{14,16},{9,11},{7,5}});
        AccentLine({{12,9},{20,9},{16,13},{12,9}});AccentLine({{11,24},{16,19},{21,24}});break;
    case EGlyph::Snow:
        for(int32 I=0;I<6;++I){float A=I*PI/3;FVector2D D(FMath::Cos(A),FMath::Sin(A)),P(-D.Y,D.X);Stroke({FVector2D(16),FVector2D(16)+D*11},TextPrimary);Stroke({FVector2D(16)+D*6+P*3,FVector2D(16)+D*8,FVector2D(16)+D*6-P*3},View.Color);}break;
    case EGlyph::Flame:
        Line({{16,4},{21,11},{22,16},{26,13},{27,20},{24,26},{18,28},{11,27},{6,22},{7,15},{11,10},{11,17},{16,12},{16,4}});
        AccentLine({{16,17},{20,23},{18,26},{14,26},{12,23},{16,17}});break;
    case EGlyph::Chain:
        Line({{7,20},{5,16},{5,11},{10,6},{15,6},{19,10},{19,14},{14,19},{10,19}});
        Line({{13,18},{13,22},{17,26},{22,26},{27,21},{27,16},{23,12},{20,12}});AccentLine({{11,21},{21,11}});break;
    case EGlyph::Stride:
        Line({{10,5},{15,6},{15,14},{12,19},{16,23},{15,26},{5,26},{5,23},{9,15},{10,5}});
        AccentLine({{21,8},{27,12},{21,16}});Line({{20,22},{27,22}});break;
    case EGlyph::Leaf:
        Line({{7,25},{7,15},{11,8},{18,5},{26,5},{26,13},{22,21},{16,24},{7,25}});
        AccentLine({{6,27},{23,9}});Line({{11,22},{11,15}});Line({{16,17},{22,17}});break;
    case EGlyph::Flask:
        Line({{12,5},{20,5},{20,7},{19,7},{19,14},{25,24},{24,27},{8,27},{7,24},{13,14},{13,7},{12,7},{12,5}});
        AccentLine({{10,21},{14,20},{19,22},{23,21}});Line({{15,11},{17,11}});break;
    case EGlyph::Lightning:
        Line({{17,4},{7,18},{15,18},{12,28},{25,12},{17,12},{20,4},{17,4}});AccentLine({{13,16},{19,16}});break;
    case EGlyph::Stone:
        Line({{8,27},{8,11},{11,6},{21,6},{24,11},{24,27},{8,27}});Line({{5,28},{27,28}});
        AccentLine({{16,10},{16,22}});AccentLine({{12,14},{20,14}});break;
    case EGlyph::Ledger:
        Line({{7,5},{24,5},{24,27},{7,27},{7,5}});Line({{11,5},{11,27}});
        AccentLine({{14,11},{21,11}});Line({{14,16},{21,16}});Line({{14,21},{19,21}});break;
    case EGlyph::Pick:
        Line({{8,27},{22,8},{24,10},{11,29},{8,27}});Line({{5,11},{12,6},{21,6},{26,10},{28,15},{21,11},{14,9},{5,11}});break;
    case EGlyph::Mountain:
        Line({{4,26},{14,6},{22,20},{25,15},{29,26},{4,26}});AccentLine({{10,14},{14,17},{17,12}});break;
    case EGlyph::Wave:
        for(int32 J=0;J<3;++J){TArray<FVector2D> P;for(int32 I=0;I<=20;++I)P.Add({5.+I*1.1,10.+J*6+FMath::Sin(I*.35)*2.5});Stroke(P,J==1?View.Color:TextPrimary);}break;
    case EGlyph::Antlers:
        Line({{16,27},{16,15},{10,11},{8,5}});Line({{10,11},{4,9},{4,5}});Line({{16,15},{22,11},{24,5}});Line({{22,11},{28,9},{28,5}});AccentLine({{11,20},{16,24},{21,20}});break;
    case EGlyph::Music:
        Line({{12,23},{12,8},{25,5},{25,20}});Line({{12,12},{25,9}});Arc({9,24},3,0,2*PI,View.Color);Arc({22,21},3,0,2*PI,TextPrimary);break;
    case EGlyph::Root:
        Line({{16,7},{16,20},{12,27}});Line({{16,20},{22,27}});Line({{16,16},{8,23},{5,23}});
        AccentLine({{16,13},{9,11},{6,6},{12,6},{16,13},{21,7},{27,6},{24,12},{16,13}});break;
    case EGlyph::Armor:
        Line({{11,5},{8,9},{4,11},{7,18},{10,16},{9,27},{23,27},{22,16},{25,18},{28,11},{24,9},{21,5},{19,9},{13,9},{11,5}});
        AccentLine({{16,12},{16,23}});Line({{11,19},{21,19}});
        if(Icon.Variant==4){AccentLine({{12,14},{20,22}});AccentLine({{20,14},{12,22}});}break;
    case EGlyph::Lotus:
        Line({{16,25},{10,18},{10,11},{16,5},{22,11},{22,18},{16,25}});
        Line({{16,25},{8,23},{4,17},{4,12},{10,15}});Line({{16,25},{24,23},{28,17},{28,12},{22,15}});AccentLine({{16,10},{16,21}});break;
    case EGlyph::Taiji:
        Arc({16,16},11,0,2*PI,TextPrimary);Arc({16,10.5},5.5,-PI*.5,PI*.5,View.Color);Arc({16,21.5},5.5,PI*.5,PI*1.5,View.Color);
        Arc({16,10},1.4,0,2*PI,TextPrimary);Arc({16,22},1.4,0,2*PI,TextPrimary);break;
    case EGlyph::Crystal:
        Line({{16,4},{25,11},{23,23},{16,29},{9,23},{7,11},{16,4}});AccentLine({{16,4},{12,12},{16,29},{20,12},{16,4}});Line({{7,11},{25,11}});break;
    case EGlyph::Cloud:
        Line({{8,23},{5,21},{4,17},{7,13},{11,13},{13,7},{18,6},{23,10},{24,14},{27,15},{28,20},{25,23},{8,23}});
        AccentLine({{10,27},{22,27}});break;
    case EGlyph::Arrow:
        Line({{6,22},{23,5},{23,13}});Line({{23,5},{15,5}});AccentLine({{5,14},{14,14},{14,23}});break;
    case EGlyph::Bone:
        Line({{8,8},{6,6},{3,8},{4,11},{8,13},{19,24},{21,28},{25,28},{27,25},{25,22},{22,22},{11,11},{11,7},{8,5},{6,6}});break;
    case EGlyph::Fang:
        Line({{5,8},{12,11},{14,26},{9,21},{5,8}});Line({{27,8},{20,11},{18,26},{23,21},{27,8}});AccentLine({{12,6},{16,10},{20,6}});break;
    case EGlyph::Sun:
        Arc({16,16},6,0,2*PI,TextPrimary);for(int32 I=0;I<8;++I){const float A=I*PI/4;const FVector2D D(FMath::Cos(A),FMath::Sin(A));Stroke({FVector2D(16)+D*9,FVector2D(16)+D*12},View.Color);}break;
    }
    // Small, separate seal marks distinguish variants without covering the main silhouette.
    if(Icon.Variant>0)
    {
        const int32 Count=1+(Icon.Variant-1)%3;
        for(int32 I=0;I<Count;++I)Stroke({{25.+I*2,28},{26.+I*2,26}},View.Color,1.f);
        if(Icon.Variant>3)Stroke({{3,5},{5,3}},View.Color,1.2f);
    }
    return Layer+2;
}
