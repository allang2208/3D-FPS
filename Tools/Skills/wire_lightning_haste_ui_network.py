from pathlib import Path
import json
from integrate_lightning_haste import ROOT,edit,replace,add_lines

def branch(s,marker):
    a=s.index(marker);b=s.index('{',a);depth=1;i=b+1
    while depth:
        if s[i]=='{':depth+=1
        elif s[i]=='}':depth-=1
        i+=1
    return s[a:i]

def clone(text):return text.replace('IceArmor','LightningHaste').replace('iceArmor','lightningHaste')

def run():
    # This script uses its own receipt so a core wiring pass cannot skip these files.
    import integrate_lightning_haste as store
    store.PROGRESS=ROOT/'SourceAssets/LightningHaste20261019/ui-network-progress.json'
    store.COMPLETED=json.loads(store.PROGRESS.read_text(encoding='utf-8')) if store.PROGRESS.exists() else []
    edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.h',lambda s:add_lines(add_lines(s,'#include "../Skills/IceArmorTypes.h"'),'FIceArmorCast PendingIceArmorStats;'))
    def network(s):
        s=add_lines(s,'#include "../Skills/FPSIceArmorComponent.h"')
        for marker in ['if(Request.SkillId==TEXT("iceArmor"))\n        {','else if(Request.SkillId==TEXT("iceArmor"))\n    {']:
            original=branch(s,marker);s=replace(s,original,clone(original)+'\n        '+original)
        s=add_lines(s,'if(SkillId==TEXT("iceArmor")){')
        s=replace(s,'{ TEXT("iceArmor") },','{ TEXT("iceArmor") }, { TEXT("lightningHaste") },')
        for context in ['PendingCastSkill','Request.SkillId']:
            s=s.replace('||'+context+'==TEXT("iceArmor")','||'+context+'==TEXT("iceArmor")||'+context+'==TEXT("lightningHaste")')
            s=s.replace('&&'+context+'!=TEXT("iceArmor")','&&'+context+'!=TEXT("iceArmor")&&'+context+'!=TEXT("lightningHaste")')
        return s
    edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp',network)
    def quickslot(s):
        s=add_lines(s,'#include "../Skills/FPSIceArmorComponent.h"')
        old=branch(s,'else if(Displayed.Skill==TEXT("iceArmor"))');s=replace(s,old,clone(old)+'\n        '+old)
        old=branch(s,'if(Binding.Skill==TEXT("iceArmor"))');return replace(s,old,clone(old)+'\n    else '+old)
    edit('Source/FPSGAME/UI/ColdSteelQuickSlot.cpp',quickslot)
    edit('Source/FPSGAME/UI/ColdSteelSkillPage.h',lambda s:add_lines(add_lines(add_lines(s,'TObjectPtr<UTexture2D> IceArmorIconTexture;'),'TSharedPtr<SButton> IceArmorDetailButton;'),'FSlateBrush IceArmorIconBrush;'))
    def page(s):
        s=replace(s,'Cards[]={{TEXT("iceArmor"),IceArmorDetailButton}', 'Cards[]={{TEXT("lightningHaste"),LightningHasteDetailButton},{TEXT("iceArmor"),IceArmorDetailButton}')
        s=replace(s,'Id==TEXT("iceArmor")?&IceArmorIconBrush:','Id==TEXT("lightningHaste")?&LightningHasteIconBrush:Id==TEXT("iceArmor")?&IceArmorIconBrush:')
        s=replace(s,'if(Id==TEXT("iceArmor"))return Model->IceArmorDefinition();','if(Id==TEXT("lightningHaste"))return Model->LightningHasteDefinition();if(Id==TEXT("iceArmor"))return Model->IceArmorDefinition();')
        s=replace(s,'if(Id==TEXT("iceArmor"))return Model->MasteryProgress(Id);','if(Id==TEXT("lightningHaste"))return Model->MasteryProgress(Id);if(Id==TEXT("iceArmor"))return Model->MasteryProgress(Id);')
        s=s.replace('IceArmorDetailButton.Reset();','LightningHasteDetailButton.Reset();IceArmorDetailButton.Reset();')
        old=branch(s,'if(Model&&!IceArmorIconTexture)')
        s=replace(s,old,clone(old)+'\n    '+old)
        s=add_lines(s,'IceArmorIconBrush.ImageSize=')
        s=replace(s,'    if(Id==TEXT("iceArmor")){Tags=', '    if(Id==TEXT("lightningHaste")){Tags=TEXT("雷电 / 强化 / 动作加速 · 无需法杖");SkillIcon=&LightningHasteIconBrush;}\n    if(Id==TEXT("iceArmor")){Tags=')
        marker='    if(SelectedSkill==TEXT("iceArmor"))\n    {'
        s=replace(s,marker,'''    if(SelectedSkill==TEXT("lightningHaste"))
    {
        const auto C=Model->LightningHasteStats(Progress(SelectedSkill).Level+(bNext?1:0));
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("+%.1f%%"),C.MoveBonus*100);
        case 1:return FString::Printf(TEXT("+%.1f%%"),C.ActionBonus*100);
        case 2:return FString::Printf(TEXT("%.1f s"),C.Duration);
        case 3:return FString::Printf(TEXT("%.0f"),C.ManaCost);
        default:return FString::Printf(TEXT("%.1f s"),C.Cooldown);
        }
    }
'''+marker)
        marker='    else if(SelectedSkill==TEXT("iceArmor"))\n    {'
        s=replace(s,marker,'''    else if(SelectedSkill==TEXT("lightningHaste"))
    {
        const auto& T=D.LightningHaste;
        AddReward(TEXT("成功施放并生效"),T.CastExperience);AddReward(TEXT("持续期间每次有效击杀"),T.KillExperience);
        AddReward(TEXT("超过5名敌人：额外奖励"),T.Kill6Bonus);AddReward(TEXT("超过10名敌人：额外奖励"),T.Kill11Bonus);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("第6名、第11名击杀分别达到连杀档位；两个额外奖励只取最高档。枪械、近战、弓、魔法与灼烧归属击杀都计入；同一目标只计一次。结束或死亡时结算已获得的修炼。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
'''+marker)
        old='''        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(IceArmorDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("iceArmor")))[Overview(true,TEXT("iceArmor"))]];'''
        s=replace(s,old,clone(old)+'\n'+old)
        marker='        else if(SelectedSkill==TEXT("iceArmor"))\n        {'
        s=replace(s,marker,'''        else if(SelectedSkill==TEXT("lightningHaste"))
        {
            const TCHAR* Rows[]={TEXT("移动速度增加"),TEXT("动作速度增加"),TEXT("持续时间"),TEXT("消耗魔法"),TEXT("生效后冷却")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("短暂引雷后，电弧环绕双手与双脚，提高移动、近战攻速、枪械射速、换弹、拉弓、施法与蓄力、武技、武器操作、格挡、翻越和物品使用速度。无需法杖，换武器后继续生效；生效期间不能重复施放。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Definition(SelectedSkill).LightningHaste;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(FString::Printf(TEXT("令 K＝等级−1：移速增加 %.1f%%＋%.1f%%×K；动作速度增加 %.1f%%＋%.1f%%×K；持续 %.1f＋%.1f×K 秒；基础蓝耗 %.0f＋%.0f×K，基础冷却 %.0f 秒，从生效时计时。速度加成在原有速度基础上相乘，每个动作只计一次。"),T.MoveBase*100,T.MovePerLevel*100,T.ActionBase*100,T.ActionPerLevel*100,T.DurationBase,T.DurationPerLevel,T.ManaBase,T.ManaPerLevel,T.Cooldown),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("冷却、持续伤害间隔、效果持续时间、弹速与跳跃重力保持原时间规则。施法前预扣魔法，未生效取消会退款；生效后死亡或离场结束，已取得的修炼保留。活动增益不跨存档恢复。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
'''+marker)
        return replace(s,'if(SelectedSkill==TEXT("iceArmor"))Button=IceArmorDetailButton;','if(SelectedSkill==TEXT("lightningHaste"))Button=LightningHasteDetailButton;if(SelectedSkill==TEXT("iceArmor"))Button=IceArmorDetailButton;')
    edit('Source/FPSGAME/UI/ColdSteelSkillPage.cpp',page)
    edit('Source/FPSGAME/Skills/PlayerSkillAssets.cpp',lambda s:replace(replace(s,'#include "IceArmorTypes.h"','#include "IceArmorTypes.h"\n#include "LightningHasteTypes.h"'),'    if (Skill == TEXT("quickCombat"))','    if(Skill==TEXT("lightningHaste"))for(const TCHAR* Path:{LightningHasteAssets::Arc,LightningHasteAssets::CastSound,LightningHasteAssets::EndSound})AddSkillAsset(Out,Path);\n    if (Skill == TEXT("quickCombat"))'))
    edit('Source/FPSGAME/UI/StatusEffectIconPainter.cpp',lambda s:replace(s,'{TEXT("iceArmor"),{EGlyph::Armor,4}}','{TEXT("iceArmor"),{EGlyph::Armor,4}}, {TEXT("lightningHaste"),{EGlyph::Lightning,0}}'))
    def status(s):
        d=json.loads(s)
        rows=next(v for v in d.values() if isinstance(v,list))
        rows.append({'type':'lightningHaste','icon':'雷','name':'雷电迅捷','color':'#87AFFF','description':'电弧环绕四肢，移动和动作速度提高。','kind':'buff','group':'combat'})
        return json.dumps(d,ensure_ascii=False,indent=2)+'\n'
    edit('Content/ColdSteelData/status_effects.json',status)
    print('Saved UI, training presentation, assets, and authoritative casting routes.')

if __name__=='__main__':run()
