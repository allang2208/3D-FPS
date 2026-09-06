import DevTool from '../dev-tool.js';
import { CollisionEditor } from '../collision-editor.js';
import { QuickBar } from '../quick-bar.js';
import { TechnologySystem } from '../../world/technology-system.js';
import { GoldManager } from '../../systems/gold-manager.js';
import { EnergyManager } from '../../systems/energy-manager.js';
import { PerformanceMonitor } from '../../systems/performance-monitor.js';
import { createNavigationDebug } from './navigation-debug.js';
import { isDungeonKeyCostIgnored } from '../../config/dev-cheats.js';
// src/ui/panels/dev-tools.js
// 动态创建交互开发工具面板 (dev-tool-panel)

export function createDevToolPanel() {
    // 根容器
    const root = document.createElement('div');
    root.id = 'devToolPanel';
    root.className = 'dev-tool-panel';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-labelledby', 'devToolTitle');
    root.tabIndex = -1;

    // ===== 头部 =====
    const header = document.createElement('div');
    header.className = 'dev-tool-header';

    const title = document.createElement('h2');
    title.id = 'devToolTitle';
    title.className = 'dev-tool-title';
    title.textContent = '交互开发工具';
    header.appendChild(title);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'dev-tool-close';
    closeBtn.id = 'devToolClose';
    closeBtn.setAttribute('aria-label', '关闭交互开发工具');
    closeBtn.textContent = '✕';
    header.appendChild(closeBtn);

    root.appendChild(header);

    // ===== Tab 栏 =====
    const tabs = document.createElement('div');
    tabs.className = 'dev-tool-tabs';
    tabs.setAttribute('role', 'tablist');
    tabs.setAttribute('aria-label', '开发工具子页');

    const tabWeapon = document.createElement('button');
    tabWeapon.className = 'dev-tool-tab active';
    tabWeapon.dataset.tab = 'weapon';
    tabWeapon.addEventListener('click', () => DevTool.switchTab('weapon'));
    tabWeapon.textContent = '武器';
    tabs.appendChild(tabWeapon);

    const tabCollision = document.createElement('button');
    tabCollision.className = 'dev-tool-tab';
    tabCollision.dataset.tab = 'collision';
    tabCollision.addEventListener('click', () => DevTool.switchTab('collision'));
    tabCollision.textContent = '碰撞';
    tabs.appendChild(tabCollision);

    const tabSkill = document.createElement('button');
    tabSkill.className = 'dev-tool-tab';
    tabSkill.dataset.tab = 'skill';
    tabSkill.addEventListener('click', () => {
        DevTool.switchTab('skill');
        fillSkillSelect();
        skillToggleSyncs.forEach((sync) => sync());
    });
    tabSkill.textContent = '技能';
    tabs.appendChild(tabSkill);

    const tabWorld = document.createElement('button');
    tabWorld.className = 'dev-tool-tab';
    tabWorld.dataset.tab = 'world';
    tabWorld.addEventListener('click', () => {
        DevTool.switchTab('world');
        renderWorldDebug();
    });
    tabWorld.textContent = '位面';
    tabs.appendChild(tabWorld);

    const tabFog = document.createElement('button');
    tabFog.className = 'dev-tool-tab';
    tabFog.dataset.tab = 'fog';
    tabFog.addEventListener('click', () => {
        DevTool.switchTab('fog');
        renderFogDebug();
    });
    tabFog.textContent = '迷雾';
    tabs.appendChild(tabFog);

    const tabPerformance = document.createElement('button');
    tabPerformance.className = 'dev-tool-tab';
    tabPerformance.dataset.tab = 'performance';
    tabPerformance.addEventListener('click', () => {
        DevTool.switchTab('performance');
        renderPerformanceDebug();
    });
    tabPerformance.textContent = '性能';
    tabs.appendChild(tabPerformance);

    const tabNavigation = document.createElement('button');
    tabNavigation.className = 'dev-tool-tab';
    tabNavigation.dataset.tab = 'navigation';
    tabNavigation.textContent = '导航';
    tabNavigation.addEventListener('click', () => {
        DevTool.switchTab('navigation');
        navigationDebug.refresh(true);
    });
    tabs.appendChild(tabNavigation);
    tabs.addEventListener('keydown', (event) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        const buttons = [...tabs.querySelectorAll('.dev-tool-tab')];
        const current = buttons.indexOf(event.target);
        if (current < 0) return;
        event.preventDefault();
        event.stopPropagation();
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
            : (current + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
        buttons[next].focus();
        buttons[next].click();
    });

    root.appendChild(tabs);

    // ===== Tab 内容：武器 =====
    const contentWeapon = document.createElement('div');
    contentWeapon.className = 'dev-tool-tab-content active';
    contentWeapon.dataset.tabContent = 'weapon';

    // 上方菜单栏
    const menu = document.createElement('div');
    menu.className = 'dev-tool-menu';

    // 动画选择
    const menuItemAnim = document.createElement('div');
    menuItemAnim.className = 'dev-tool-menu-item';
    menuItemAnim.innerHTML = '<label for="devToolAnimSelect">动画</label>';
    const animSelect = document.createElement('select');
    animSelect.id = 'devToolAnimSelect';
    const animOptions = [
        ['idle', '待机'],
        ['walk', '移动'],
        ['running', '奔跑'],
        ['attack', '攻击'],
        ['attack2', '二段攻击'],
        ['attack3', '三段攻击'],
        ['dash', '冲刺攻击'],
        ['recover', '收势'],
        ['whirlwind_recover', '风车收势'],
        ['dash_recover', '冲刺收势'],
        ['dodge_roll', '翻滚'],
        ['dodge_jump', '跳跃闪避'],
        ['cast', '空手施法'],
        ['staff_cast', '法杖施法'],
        ['bow_draw', '拉弓'],
        ['bow_release', '射箭'],
        ['gun_idle', '持枪待机'],
        ['gun_idle_pistol', '持枪待机·手枪'],
        ['gun_idle_dual', '持枪待机·双持'],
        ['gun_fire', '射击'],
        ['reload', '换弹'],
        ['hurt', '受击'],
        ['death', '死亡'],
    ];
    animOptions.forEach(([value, text]) => {
        const opt = document.createElement('option');
        opt.value = value;
        opt.textContent = text;
        animSelect.appendChild(opt);
    });
    menuItemAnim.appendChild(animSelect);
    menu.appendChild(menuItemAnim);

    // 持枪移动分层姿态：独立于 walk/running 动画选择，便于直接审计长枪、单手枪和双持。
    const menuItemGunPose = document.createElement('div');
    menuItemGunPose.className = 'dev-tool-menu-item';
    menuItemGunPose.innerHTML = '<label for="devToolGunPoseSelect">持枪姿态</label>';
    const gunPoseSelect = document.createElement('select');
    gunPoseSelect.id = 'devToolGunPoseSelect';
    [
        ['', '按武器自动'],
        ['gun_idle', '长枪'],
        ['gun_idle_pistol', '单手枪'],
        ['gun_idle_dual', '双持手枪'],
    ].forEach(([value, text]) => {
        const opt = document.createElement('option');
        opt.value = value;
        opt.textContent = text;
        gunPoseSelect.appendChild(opt);
    });
    menuItemGunPose.appendChild(gunPoseSelect);
    menu.appendChild(menuItemGunPose);

    // 帧控制
    const menuItemFrame = document.createElement('div');
    menuItemFrame.className = 'dev-tool-menu-item dev-tool-frame-controls';
    menuItemFrame.innerHTML = '<label for="devToolFrameSlider">帧</label>';
    const frameSlider = document.createElement('input');
    frameSlider.type = 'range';
    frameSlider.id = 'devToolFrameSlider';
    frameSlider.min = '0';
    frameSlider.max = '0';
    frameSlider.value = '0';
    menuItemFrame.appendChild(frameSlider);
    const frameLabel = document.createElement('span');
    frameLabel.id = 'devToolFrameLabel';
    frameLabel.textContent = '1 / 1';
    menuItemFrame.appendChild(frameLabel);
    const playBtn = document.createElement('button');
    playBtn.id = 'devToolPlayBtn';
    playBtn.className = 'dev-tool-menu-btn';
    playBtn.textContent = '▶ 播放';
    menuItemFrame.appendChild(playBtn);
    // 播放帧率（留空=动画配置 frameRate；DevTool._getPreviewFps 读取）
    const fpsInput = document.createElement('input');
    fpsInput.type = 'number';
    fpsInput.id = 'devToolFps';
    fpsInput.min = '1';
    fpsInput.max = '120';
    fpsInput.step = '1';
    fpsInput.placeholder = 'fps';
    fpsInput.title = '播放帧率（留空=动画配置帧率）';
    fpsInput.setAttribute('aria-label', '预览播放帧率');
    menuItemFrame.appendChild(fpsInput);

    // 武器选择
    const menuItemWeapon = document.createElement('div');
    menuItemWeapon.className = 'dev-tool-menu-item';
    menuItemWeapon.innerHTML = '<label for="devToolWeaponSelect">武器</label>';
    const weaponSelect = document.createElement('select');
    weaponSelect.id = 'devToolWeaponSelect';
    const weaponOptions = [
        ['sword', '⚔️ 剑（生锈长剑）'],
        ['staff', '🪄 法杖（学徒长杖）'],
        ['bow', '🏹 弓（训练弓）'],
        ['pistol', '🔫 手枪（G18）'],
        ['deagle', '🔫 沙漠之鹰'],
        ['revolver357', '🔫 .357麦格农左轮'],
        ['p4040', '🔫 P4040'],
        ['beretta93r', '🔫 Beretta 93R'],
        ['m1911a1', '🔫 M1911A1'],
        ['usp45', '🔫 USP .45'],
        ['fiveSeven', '🔫 FN Five-seveN'],
        ['pkm', '🔥 PKM'],
        ['rpd', '🔥 RPD'],
        ['m249', '🔥 M249 SAW'],
        ['ultimax100', '🔥 Ultimax 100 Mk8'],
        ['mg42', '🔥 MG42'],
        ['fusion_core_lmg', '🔥 熔核轻机枪'],
        ['singularity_loom_lmg', '🌀 奇点织机'],
        ['celestial_cartographer_lmg', '✦ 天穹测绘者'],
        ['grave_covenant_cantor_lmg', '♰ 冥约颂炮'],
        ['akm', '🔥 AKM'],
        ['qbz191', '🔥 QBZ-191'],
        ['qjb201', '🔥 QJB-201'],
        ['super90', '🔫 Super90'],
        ['saiga12k', '🔫 S12K'],
        ['s686', '🔫 S686'],
        ['m870_breacher', '🔫 M870 短管型'],
        ['ksg12', '🔫 KSG-12'],
        ['spas12', '🔫 SPAS-12'],
        ['aa12', '🔫 AA-12'],
        ['winchester1887', '🔫 Winchester 1887'],
        ['terminus_pendulum', '🔫 末日钟摆'],
        ['void_funeral_tide', '🔫 虚空葬潮'],
        ['black_sun_verdict', '🔫 黑日圣裁'],
        ['royal_hunt_finale', '🔫 王猎终局'],
        ['energy_lmg', '🔫 能量轻机枪'],
    ];
    weaponOptions.forEach(([value, text]) => {
        const opt = document.createElement('option');
        opt.value = value;
        opt.textContent = text;
        weaponSelect.appendChild(opt);
    });
    menuItemWeapon.appendChild(weaponSelect);
    menu.appendChild(menuItemWeapon);
    menu.appendChild(menuItemFrame);

    // 功能按钮
    const weaponActions = document.createElement('div');
    weaponActions.className = 'dev-tool-actions dev-tool-weapon-actions';
    const btnSave = document.createElement('button');
    btnSave.className = 'dev-tool-menu-btn primary';
    btnSave.id = 'devToolSave';
    btnSave.textContent = '💾 保存';
    weaponActions.appendChild(btnSave);

    const btnReset = document.createElement('button');
    btnReset.className = 'dev-tool-menu-btn';
    btnReset.id = 'devToolReset2';
    btnReset.textContent = '🔄 重置';
    weaponActions.appendChild(btnReset);

    const btnCoord = document.createElement('button');
    btnCoord.className = 'dev-tool-menu-btn';
    btnCoord.id = 'devToolCoord';
    btnCoord.textContent = '📐 坐标工具';
    weaponActions.appendChild(btnCoord);

    const btnFlip = document.createElement('button');
    btnFlip.className = 'dev-tool-menu-btn';
    btnFlip.id = 'devToolFlip';
    btnFlip.textContent = '↔ 朝左';
    btnFlip.title = '切换武器朝向预览（朝左时位置镜像 + 旋转取反 + 贴图翻转，与游戏 flipX 绑定同口径）';
    weaponActions.appendChild(btnFlip);
    menu.appendChild(weaponActions);

    contentWeapon.appendChild(menu);

    // 下方双栏
    const content = document.createElement('div');
    content.className = 'dev-tool-content';

    // 左栏：人物动画展示
    const left = document.createElement('div');
    left.className = 'dev-tool-left';

    const canvasWrap = document.createElement('div');
    canvasWrap.className = 'dev-tool-canvas-wrap';

    const canvas = document.createElement('canvas');
    canvas.id = 'devToolCanvas';
    canvas.width = 640;
    canvas.height = 520;
    canvas.tabIndex = 0;
    canvas.setAttribute('aria-label', '角色与武器预览，R切换调整模式');
    canvasWrap.appendChild(canvas);

    // 缩放控制按钮
    const zoomControls = document.createElement('div');
    zoomControls.className = 'dev-tool-zoom-controls';
    
    const btnZoomOut = document.createElement('button');
    btnZoomOut.className = 'dev-tool-zoom-btn';
    btnZoomOut.id = 'devToolZoomOut';
    btnZoomOut.textContent = '−';
    btnZoomOut.title = '缩小';
    zoomControls.appendChild(btnZoomOut);
    
    const zoomLabel = document.createElement('span');
    zoomLabel.className = 'dev-tool-zoom-label';
    zoomLabel.id = 'devToolZoomLabel';
    zoomLabel.textContent = '100%';
    zoomControls.appendChild(zoomLabel);
    
    const btnZoomIn = document.createElement('button');
    btnZoomIn.className = 'dev-tool-zoom-btn';
    btnZoomIn.id = 'devToolZoomIn';
    btnZoomIn.textContent = '+';
    btnZoomIn.title = '放大';
    zoomControls.appendChild(btnZoomIn);
    
    const btnZoomReset = document.createElement('button');
    btnZoomReset.className = 'dev-tool-zoom-btn';
    btnZoomReset.id = 'devToolZoomReset';
    btnZoomReset.textContent = '⟲';
    btnZoomReset.title = '重置缩放';
    zoomControls.appendChild(btnZoomReset);
    
    const overlay = document.createElement('div');
    overlay.className = 'dev-tool-canvas-overlay';
    const hint = document.createElement('div');
    hint.className = 'dev-tool-hint-text';
    hint.id = 'devToolHint';
    hint.innerHTML = '拖动武器到人物位置 → 按 <kbd>R</kbd> 进入调整模式';
    overlay.appendChild(hint);
    canvasWrap.appendChild(overlay);
    left.appendChild(canvasWrap);
    left.appendChild(zoomControls);

    const frameStrip = document.createElement('div');
    frameStrip.className = 'dev-tool-frame-strip';
    frameStrip.id = 'devToolFrameStrip';
    left.appendChild(frameStrip);

    const info = document.createElement('div');
    info.className = 'dev-tool-info';
    info.id = 'devToolInfo';

    const infoRow1 = document.createElement('div');
    infoRow1.className = 'dev-tool-info-row';
    infoRow1.innerHTML = '<span>状态:</span> <span id="devToolStatus">待机</span>';
    info.appendChild(infoRow1);

    const infoRow2 = document.createElement('div');
    infoRow2.className = 'dev-tool-info-row';
    infoRow2.innerHTML = '<span>武器:</span> <span id="devToolWeaponName">无</span>';
    info.appendChild(infoRow2);

    left.appendChild(info);
    content.appendChild(left);

    // 右栏：武器选择和控制
    const right = document.createElement('div');
    right.className = 'dev-tool-right';

    const sectionTitle = document.createElement('div');
    sectionTitle.className = 'dev-tool-section-title';
    sectionTitle.textContent = '武器贴图';
    right.appendChild(sectionTitle);

    const weaponPreview = document.createElement('div');
    weaponPreview.className = 'dev-tool-weapon-preview';
    weaponPreview.id = 'devToolWeaponPreview';
    const placeholder = document.createElement('div');
    placeholder.className = 'dev-tool-weapon-placeholder';
    placeholder.textContent = '选择武器类型';
    weaponPreview.appendChild(placeholder);
    const weaponImg = document.createElement('img');
    weaponImg.id = 'devToolWeaponImg';
    weaponImg.src = '';
    weaponImg.style.cssText = 'display:none; cursor: var(--bp-cursor-grab, grab);';
    weaponImg.alt = 'weapon';
    weaponImg.setAttribute('draggable', 'true');
    weaponPreview.appendChild(weaponImg);
    right.appendChild(weaponPreview);

    const controls = document.createElement('div');
    controls.className = 'dev-tool-controls';

    const controlRows = [
        { label: '屏幕偏移X:', id: 'devToolOffX', value: '0', step: '1' },
        { label: '屏幕偏移Y:', id: 'devToolOffY', value: '0', step: '1' },
        { label: 'Rotation:', id: 'devToolRot', value: '0', step: '1' },
        { label: 'Scale:', id: 'devToolScl', value: '1', step: '0.1' },
        { label: '模糊X:', id: 'devToolBlurX', value: '0', step: '0.5' },
        { label: '模糊Y:', id: 'devToolBlurY', value: '0', step: '0.5' },
        { label: '拉伸X:', id: 'devToolStrX', value: '1', step: '0.01' },
        { label: '拉伸Y:', id: 'devToolStrY', value: '1', step: '0.01' },
    ];
    controlRows.forEach(({ label, id, value, step }) => {
        const row = document.createElement('div');
        row.className = 'dev-tool-control-row';
        row.innerHTML = `<label for="${id}">${label}</label>`;
        const input = document.createElement('input');
        input.type = 'number';
        input.id = id;
        input.value = value;
        input.step = step;
        row.appendChild(input);
        controls.appendChild(row);
    });

    // 📍 固定点工具按钮（dev-tool.js 绑定事件）：武器贴图校准标记点，跨帧跟随
    const markerRow = document.createElement('div');
    markerRow.className = 'dev-tool-control-row dev-tool-marker-row';
    const markerBtn = document.createElement('button');
    markerBtn.id = 'devToolMarker';
    markerBtn.className = 'dev-tool-menu-btn';
    markerBtn.title = '在武器贴图上放置校准标记点，所有帧同步显示';
    markerBtn.textContent = '📍 固定点';
    markerRow.appendChild(markerBtn);
    controls.appendChild(markerRow);

    right.appendChild(controls);

    const modeHint = document.createElement('div');
    modeHint.className = 'dev-tool-mode-hint';
    modeHint.id = 'devToolModeHint';
    modeHint.innerHTML = '<div>🖱 左键拖动</div><div>🔄 滚轮缩放</div><div>按 <kbd>R</kbd> 切换旋转/缩放模式</div>';
    right.appendChild(modeHint);

    const dataOutput = document.createElement('div');
    dataOutput.className = 'dev-tool-data-output';
    dataOutput.id = 'devToolDataOutput';
    dataOutput.style.cssText = 'display:none;';
    right.appendChild(dataOutput);

    content.appendChild(right);
    contentWeapon.appendChild(content);
    root.appendChild(contentWeapon);

    // ===== Tab 内容：碰撞体积编辑 =====
    const contentCollision = document.createElement('div');
    contentCollision.className = 'dev-tool-tab-content';
    contentCollision.dataset.tabContent = 'collision';
    contentCollision.style.cssText = 'display:none;';

    const collisionWrap = document.createElement('div');
    collisionWrap.className = 'dev-tool-page';

    const collisionDesc = document.createElement('div');
    collisionDesc.className = 'dev-tool-page-intro';
    collisionDesc.innerHTML = '<p>在主神空间中实时编辑碰撞判定：</p>'
        + '<p>🟩 怪物/NPC：矩形八点拖拽 + 圆柱半径/高矮 + 整体平移</p>'
        + '<p>🧱 墙：拖 face 线段两端点改跨度，橙点调碰撞厚度（按类型生效）</p>'
        + '<p>🚪 门：打开/关闭两状态分别调整；打开态拖金色门洞边缘调通行宽度</p>'
        + '<p>🛢 障碍物：footprint 矩形八点拖拽；🪤 陷阱：触发半径圈 + 数量/伤害/冷却</p>'
        + '<p>调整后即时生效，「保存」写入 data/enemy-config.json / game-config.json / wall-geo-overrides.json / dungeon-config.json。</p>';
    collisionWrap.appendChild(collisionDesc);

    const collisionOpenBtn = document.createElement('button');
    collisionOpenBtn.className = 'dev-tool-menu-btn primary collision-open-btn';
    collisionOpenBtn.textContent = '🎯 打开碰撞体积编辑器';
    // 编辑器需要看到游戏画面：先收起本面板，再打开浮动编辑器（参照坐标工具的做法）
    collisionOpenBtn.addEventListener('click', () => {
        DevTool.hide();
        CollisionEditor.open();
    });
    collisionWrap.appendChild(collisionOpenBtn);

    contentCollision.appendChild(collisionWrap);
    root.appendChild(contentCollision);

    // ===== Tab 内容：技能等级调试 =====
    const contentSkill = document.createElement('div');
    contentSkill.className = 'dev-tool-tab-content';
    contentSkill.dataset.tabContent = 'skill';
    contentSkill.style.cssText = 'display:none;';

    const skillWrap = document.createElement('div');
    skillWrap.className = 'dev-tool-page';

    const skillDesc = document.createElement('div');
    skillDesc.className = 'dev-tool-page-intro';
    skillDesc.innerHTML = '<h3>技能与玩法调试</h3><p>技能等级、战斗、资源、建筑部队和科技分区操作；调试修改即时生效。</p>';
    skillWrap.appendChild(skillDesc);

    const skillGrid = document.createElement('div');
    skillGrid.className = 'dev-tool-card-grid';
    const createSkillCard = (label) => {
        const card = document.createElement('section');
        card.className = 'dev-tool-card';
        const heading = document.createElement('h3');
        heading.textContent = label;
        card.appendChild(heading);
        skillGrid.appendChild(card);
        return card;
    };
    const skillToggleSyncs = [];
    const skillRow = createSkillCard('技能等级');
    const combatCard = createSkillCard('战斗开关');
    const resourceCard = createSkillCard('资源与地牢');
    const productionCard = createSkillCard('建筑与部队');
    const technologyCard = createSkillCard('科技调试');

    const skillSelect = document.createElement('select');
    skillSelect.id = 'devToolSkillSelect';
    const skillLabel = document.createElement('label');
    skillLabel.htmlFor = skillSelect.id;
    skillLabel.textContent = '选择技能';
    skillRow.appendChild(skillLabel);
    skillRow.appendChild(skillSelect);

    const levelRow = document.createElement('div');
    levelRow.className = 'dev-tool-actions dev-tool-skill-level';
    const levelLabel = document.createElement('label');
    levelLabel.htmlFor = 'devToolSkillLevel';
    levelLabel.textContent = '等级:';
    const levelInput = document.createElement('input');
    levelInput.type = 'number';
    levelInput.id = 'devToolSkillLevel';
    levelInput.min = '1';
    levelInput.max = '20';
    levelInput.value = '1';
    const btnMinus = document.createElement('button');
    btnMinus.className = 'dev-tool-menu-btn';
    btnMinus.textContent = '−';
    btnMinus.setAttribute('aria-label', '技能降低一级');
    const btnPlus = document.createElement('button');
    btnPlus.className = 'dev-tool-menu-btn';
    btnPlus.textContent = '+';
    btnPlus.setAttribute('aria-label', '技能提升一级');
    const btnApply = document.createElement('button');
    btnApply.className = 'dev-tool-menu-btn';
    btnApply.textContent = '✓ 应用';
    btnApply.classList.add('primary');
    levelRow.append(levelLabel, levelInput, btnMinus, btnPlus, btnApply);
    skillRow.appendChild(levelRow);

    const skillStatus = document.createElement('div');
    skillStatus.id = 'devToolSkillStatus';
    skillStatus.className = 'dev-tool-status';
    skillStatus.setAttribute('role', 'status');
    skillStatus.setAttribute('aria-live', 'polite');
    skillRow.appendChild(skillStatus);

    // ===== 测试开关：技能无CD无消耗 =====
    const cheatRow = document.createElement('div');
    cheatRow.className = 'dev-tool-setting-group';
    const btnCheat = document.createElement('button');
    btnCheat.id = 'devToolSkillCheat';
    btnCheat.className = 'dev-tool-menu-btn';
    const syncCheatBtn = () => {
        const on = !!(window.Game && window.Game._devNoSkillCost);
        btnCheat.textContent = on ? '⏱ 技能无CD无消耗：开' : '⏱ 技能无CD无消耗：关';
        btnCheat.setAttribute('aria-pressed', String(on));
    };
    btnCheat.addEventListener('click', () => {
        if (!window.Game) {
            if (DevTool && typeof DevTool._showToast === 'function') DevTool._showToast('❌ 请先进入游戏');
            return;
        }
        const next = !window.Game._devNoSkillCost;
        window.Game._devNoSkillCost = next;
        // 开启时清空当前所有冷却，立即生效
        if (next) {
            const p = window.Game.player;
            if (p) {
                for (const k of Object.keys(p)) {
                    if (k.endsWith('Cooldown')) p[k] = 0;
                }
            }
            for (const k of Object.keys(QuickBar.cooldowns || {})) QuickBar.cooldowns[k] = 0;
        }
        syncCheatBtn();
        if (DevTool && typeof DevTool._showToast === 'function') {
            DevTool._showToast(next ? '✅ 技能无CD无消耗 已开启' : '技能无CD无消耗 已关闭');
        }
    });
    syncCheatBtn();
    skillToggleSyncs.push(syncCheatBtn);
    const cheatHint = document.createElement('span');
    cheatHint.textContent = '测试用：施放技能不消耗 MP/体力、无冷却';
    cheatHint.className = 'dev-tool-help';
    cheatRow.append(btnCheat, cheatHint);
    combatCard.appendChild(cheatRow);

    // ===== 测试开关：无限资源（军事招募仍按正式规则消耗粮食） =====
    const resourceRow = document.createElement('div');
    resourceRow.className = 'dev-tool-setting-group dev-tool-resource-toggles';
    const btnResource = document.createElement('button');
    btnResource.id = 'devToolInfiniteResource';
    btnResource.className = 'dev-tool-menu-btn';
    const syncResourceBtn = () => {
        const on = !!(window.Game && window.Game._devInfiniteResources);
        btnResource.textContent = on ? '∞ 无限资源：开' : '∞ 无限资源：关';
        btnResource.setAttribute('aria-pressed', String(on));
    };
    btnResource.addEventListener('click', () => {
        if (!window.Game) {
            if (DevTool && typeof DevTool._showToast === 'function') DevTool._showToast('❌ 请先进入游戏');
            return;
        }
        const next = !window.Game._devInfiniteResources;
        window.Game._devInfiniteResources = next;
        syncResourceBtn();
        if (DevTool && typeof DevTool._showToast === 'function') {
            DevTool._showToast(next ? '✅ 无限资源 已开启（军事招募仍消耗粮食）' : '无限资源 已关闭');
        }
    });
    syncResourceBtn();
    skillToggleSyncs.push(syncResourceBtn);
    // 与无限资源独立，紧邻其右侧；只绕过地牢入场钥匙门禁和扣除。
    const btnDungeonKey = document.createElement('button');
    btnDungeonKey.type = 'button';
    btnDungeonKey.id = 'devToolNoDungeonKeyCost';
    btnDungeonKey.className = 'dev-tool-menu-btn';
    btnDungeonKey.title = '开启后进入地牢不检查、不消耗对应等级钥匙（代币）；仍需满足地牢解锁条件';
    const syncDungeonKeyBtn = () => {
        const on = isDungeonKeyCostIgnored();
        btnDungeonKey.textContent = `🔑 地牢免钥匙：${on ? '开' : '关'}`;
        btnDungeonKey.setAttribute('aria-pressed', String(on));
    };
    btnDungeonKey.addEventListener('click', () => {
        if (!window.Game?.isRunning) {
            DevTool?._showToast?.('❌ 请先进入游戏');
            return;
        }
        const next = !isDungeonKeyCostIgnored();
        window.Game._devNoDungeonKeyCost = next;
        syncDungeonKeyBtn();
        window.ExpeditionSystem?.refreshDungeonKeyRequirement?.();
        DevTool?._showToast?.(next
            ? '✅ 地牢免钥匙 已开启（不检查、不消耗代币）'
            : '地牢免钥匙 已关闭（恢复钥匙检查与消耗）');
    });
    syncDungeonKeyBtn();
    skillToggleSyncs.push(syncDungeonKeyBtn);
    const resourceHint = document.createElement('span');
    resourceHint.textContent = '测试用：经济事务免金币/能源；军事招募仍消耗粮食';
    resourceHint.className = 'dev-tool-help';
    resourceRow.append(btnResource, btnDungeonKey, resourceHint);
    resourceCard.appendChild(resourceRow);

    // ===== 测试开关：建筑升级 / 造兵等待 / 军事人口 =====
    const createGameplayToggleRow = ({ id, flag, icon, label, hint, onEnabled }) => {
        const row = document.createElement('div');
        row.className = 'dev-tool-setting-group';
        const button = document.createElement('button');
        button.id = id;
        button.className = 'dev-tool-menu-btn';
        const sync = () => {
            const on = !!(window.Game && window.Game[flag]);
            button.textContent = `${icon} ${label}：${on ? '开' : '关'}`;
            button.setAttribute('aria-pressed', String(on));
        };
        button.addEventListener('click', () => {
            if (!window.Game?.isRunning) {
                DevTool?._showToast?.('❌ 请先进入游戏');
                return;
            }
            const next = !window.Game[flag];
            window.Game[flag] = next;
            if (next) onEnabled?.(window.Game);
            sync();
            DevTool?._showToast?.(next ? `✅ ${label} 已开启` : `${label} 已关闭`);
        });
        sync();
        skillToggleSyncs.push(sync);
        const hintText = document.createElement('span');
        hintText.textContent = hint;
        hintText.className = 'dev-tool-help';
        row.append(button, hintText);
        productionCard.appendChild(row);
    };

    createGameplayToggleRow({
        id: 'devToolInstantBuildingUpgrade',
        flag: '_devInstantBuildingUpgrades',
        icon: '🏗',
        label: '建筑升级瞬间完成',
        hint: '测试用：当前与后续建筑升级项目在下一帧完成，仍正常扣费并检查科技',
    });
    createGameplayToggleRow({
        id: 'devToolInstantTroopProduction',
        flag: '_devInstantTroopProduction',
        icon: '⚔',
        label: '造兵瞬间完成',
        hint: '测试用：跳过招募读条，仍消耗粮食并检查科技、出口与特色编制',
    });
    createGameplayToggleRow({
        id: 'devToolIgnoreMilitaryPopulation',
        flag: '_devIgnoreMilitaryPopulation',
        icon: '♟',
        label: '造兵无视人口',
        hint: '测试用：允许军事人口超过房屋容量；关闭后超额部队保留，但新招募恢复受限',
        onEnabled: (game) => {
            for (const entity of game.entities?.values?.() || []) {
                if (!entity?._isTroopProducer) continue;
                if (entity._spawnPopulationBlocked) entity._spawnRetryTimer = 0;
                entity._spawnPopulationBlocked = false;
                for (const queue of Object.values(entity._parallelQueues || {})) {
                    if (queue?.populationBlocked) queue.retryTimer = 0;
                    if (queue) queue.populationBlocked = false;
                }
            }
        },
    });

    // ===== 测试按钮：一次性增加正式经济资源 =====
    const grantResourceRow = document.createElement('div');
    grantResourceRow.className = 'dev-tool-actions';
    const createGrantButton = (id, label, grant) => {
        const button = document.createElement('button');
        button.id = id;
        button.className = 'dev-tool-menu-btn';
        button.textContent = label;
        button.addEventListener('click', () => {
            if (!window.Game?.isRunning) {
                DevTool?._showToast?.('❌ 请先进入游戏');
                return;
            }
            grant();
        });
        return button;
    };
    const grantGoldBtn = createGrantButton('devToolGrantGold', '+10000 金币', () => {
        const added = GoldManager.depositGold(10000, { notifyFull: true });
        DevTool?._showToast?.(added === 10000 ? '✅ 金币 +10000' : `⚠️ 背包空间不足，金币 +${added}`);
    });
    const grantEnergyBtn = createGrantButton('devToolGrantEnergy', '+10000 能源', () => {
        const before = EnergyManager.getEnergy();
        EnergyManager.importLegacyEnergy(10000);
        const stored = Math.max(0, EnergyManager.getEnergy() - before);
        DevTool?._showToast?.(stored === 10000
            ? '✅ 能源 +10000'
            : `✅ 能源 +10000（${stored} 已入库，其余等待仓库空间）`);
    });
    const grantFoodBtn = createGrantButton('devToolGrantFood', '+10000 食物', () => {
        const before = EnergyManager.getFood();
        EnergyManager.importLegacyFood(10000);
        const stored = Math.max(0, EnergyManager.getFood() - before);
        DevTool?._showToast?.(stored === 10000
            ? '✅ 食物 +10000'
            : `✅ 食物 +10000（${stored} 已入库，其余等待仓库空间）`);
    });
    grantResourceRow.append(grantGoldBtn, grantEnergyBtn, grantFoodBtn);
    resourceCard.appendChild(grantResourceRow);

    // ===== 测试按钮：一次性解锁全部科技与受控功能 =====
    const technologyRow = document.createElement('div');
    technologyRow.className = 'dev-tool-setting-group';
    const unlockTechnologyBtn = document.createElement('button');
    unlockTechnologyBtn.id = 'devToolUnlockAllTechnology';
    unlockTechnologyBtn.className = 'dev-tool-menu-btn';
    const syncTechnologyBtn = () => {
        const completed = TechnologySystem.state.completed.length;
        const total = TechnologySystem.getNodes().length;
        unlockTechnologyBtn.textContent = completed >= total ? `🔬 全部科技已解锁（${total}/${total}）` : `🔬 解锁全部科技（${completed}/${total}）`;
        unlockTechnologyBtn.classList.toggle('is-complete', completed >= total);
    };
    unlockTechnologyBtn.addEventListener('click', () => {
        if (!window.Game?.isRunning) {
            DevTool?._showToast?.('❌ 请先进入游戏');
            return;
        }
        const unlocked = TechnologySystem.unlockAll({ source: 'dev' });
        syncTechnologyBtn();
        DevTool?._showToast?.(unlocked > 0
            ? `✅ 已解锁全部科技（新增 ${unlocked} 项，含未开放位面的专项科技）`
            : '全部科技已经解锁（含位面专项科技）');
    });
    syncTechnologyBtn();
    skillToggleSyncs.push(syncTechnologyBtn);
    const instantTechnologyBtn = document.createElement('button');
    instantTechnologyBtn.id = 'devToolInstantTechnologyResearch';
    instantTechnologyBtn.className = 'dev-tool-menu-btn';
    const syncInstantTechnologyBtn = () => {
        const on = !!(window.Game && window.Game._devInstantTechnologyResearch);
        instantTechnologyBtn.textContent = `⚡ 瞬间研发：${on ? '开' : '关'}`;
        instantTechnologyBtn.setAttribute('aria-pressed', String(on));
    };
    instantTechnologyBtn.addEventListener('click', () => {
        if (!window.Game?.isRunning) {
            DevTool?._showToast?.('❌ 请先进入游戏');
            return;
        }
        const next = !window.Game._devInstantTechnologyResearch;
        window.Game._devInstantTechnologyResearch = next;
        syncInstantTechnologyBtn();
        DevTool?._showToast?.(next
            ? '✅ 瞬间研发已开启：在科技树详情中完成所选科技'
            : '瞬间研发已关闭');
    });
    syncInstantTechnologyBtn();
    skillToggleSyncs.push(syncInstantTechnologyBtn);
    const technologyHint = document.createElement('span');
    technologyHint.textContent = '测试用：解锁全部科技，或开启后在科技树详情中瞬间完成所选科技及其前置';
    technologyHint.className = 'dev-tool-help';
    technologyRow.append(unlockTechnologyBtn, instantTechnologyBtn, technologyHint);
    technologyCard.appendChild(technologyRow);

    // ===== 测试开关：友军伤害（开启后玩家可对友方单位造成伤害） =====
    const ffRow = document.createElement('div');
    ffRow.className = 'dev-tool-setting-group';
    const btnFF = document.createElement('button');
    btnFF.id = 'devToolFriendlyFire';
    btnFF.className = 'dev-tool-menu-btn danger';
    const syncFFBtn = () => {
        const on = !!(window.Game && window.Game._devFriendlyFire);
        btnFF.textContent = on ? '💥 友军伤害：开' : '💥 友军伤害：关';
        btnFF.setAttribute('aria-pressed', String(on));
    };
    btnFF.addEventListener('click', () => {
        if (!window.Game) {
            if (DevTool && typeof DevTool._showToast === 'function') DevTool._showToast('❌ 请先进入游戏');
            return;
        }
        const next = !window.Game._devFriendlyFire;
        window.Game._devFriendlyFire = next;
        syncFFBtn();
        if (DevTool && typeof DevTool._showToast === 'function') {
            DevTool._showToast(next ? '✅ 友军伤害 已开启（可攻击友方单位）' : '友军伤害 已关闭');
        }
    });
    syncFFBtn();
    skillToggleSyncs.push(syncFFBtn);
    const ffHint = document.createElement('span');
    ffHint.textContent = '测试用：玩家可对友方单位（队友/建筑）造成伤害';
    ffHint.className = 'dev-tool-help';
    ffRow.append(btnFF, ffHint);
    combatCard.appendChild(ffRow);

    skillWrap.appendChild(skillGrid);
    contentSkill.appendChild(skillWrap);
    root.appendChild(contentSkill);

    // ===== Tab 内容：位面生命周期调试 =====
    const contentWorld = document.createElement('div');
    contentWorld.className = 'dev-tool-tab-content';
    contentWorld.dataset.tabContent = 'world';
    contentWorld.style.cssText = 'display:none;';

    const worldWrap = document.createElement('div');
    worldWrap.className = 'dev-tool-page';
    worldWrap.innerHTML = `
        <div class="dev-tool-page-intro">
            <p>🌐 位面生命周期调试：查看状态、世代、快照和真实入侵候选池。</p>
            <p class="dev-tool-warning">测试打通会跳过地牢、科技、资源和传送门构造，自动生成传送门与市政厅。建筑、矿脉、道路、迷雾和玩家落点仅在本次运行保留，离开后再次进入会继续现场。</p>
            <p>立即生成入侵、天气与推进时间可用于测试；测试位面不会进入正式位面快照、跨位面收益、入侵轮次或存档。只有新游戏、读档或“重置测试位面”会主动清空测试现场。</p>
        </div>
        <div class="dev-tool-card-grid">
        <section class="dev-tool-card"><h3>游戏时间与当前位面</h3><div class="dev-tool-actions">
            <button id="devWorldRefresh" class="dev-tool-menu-btn">刷新</button>
            <button id="devWorldAdvance1" class="dev-tool-menu-btn">推进 1 天</button>
            <button id="devWorldAdvance5" class="dev-tool-menu-btn">推进 5 天</button>
            <button id="devWorldInstantInvasion" type="button" class="dev-tool-menu-btn danger" title="在当前所在位面按正式规则开战；已有来袭军团时保留其战损并立即抵达">立即生成入侵</button>
        </div><div id="devWorldInvasionResult" class="dev-tool-status" role="status" aria-live="polite"></div></section>
        <section class="dev-tool-card"><h3>指定位面操作</h3><label for="devWorldSelect">目标位面</label>
            <select id="devWorldSelect"></select><div class="dev-tool-actions">
            <button id="devWorldUnlock" class="dev-tool-menu-btn">测试打通并直连</button>
            <button id="devWorldEnter" class="dev-tool-menu-btn primary">进入测试位面</button>
            <button id="devWorldReset" class="dev-tool-menu-btn danger" title="清空本次运行中的测试现场并重新生成地块">重置测试位面</button>
            <button id="devWorldDestroy" class="dev-tool-menu-btn danger">模拟毁门</button>
        </div></section>
        </div>
        <div id="devWorldSummary" class="dev-tool-card dev-tool-summary"></div>
        <div id="devWorldRows" class="dev-tool-card-grid"></div>`;
    contentWorld.appendChild(worldWrap);
    root.appendChild(contentWorld);

    const renderWorldDebug = () => {
        const system = window.WorldInvasionSystem;
        const summary = root.querySelector('#devWorldSummary');
        const rows = root.querySelector('#devWorldRows');
        const select = root.querySelector('#devWorldSelect');
        const enterButton = root.querySelector('#devWorldEnter');
        const resetButton = root.querySelector('#devWorldReset');
        if (!system?.getDebugModel || !summary || !rows || !select) {
            if (summary) summary.textContent = '位面系统尚未初始化';
            return;
        }
        const model = system.getDebugModel();
        const currentSelection = select.value;
        select.innerHTML = model.worlds.map((world) =>
            `<option value="${world.sceneId}">${world.name} (${world.sceneId})${world.testOnly ? ' · 运行期测试' : ''}</option>`).join('');
        if (model.worlds.some((world) => world.sceneId === currentSelection)) select.value = currentSelection;
        const selectedWorld = model.worlds.find((world) => world.sceneId === select.value);
        if (enterButton) {
            const isCurrent = window.SceneManager?.currentScene === selectedWorld?.sceneId;
            enterButton.disabled = !selectedWorld?.testOnly || !window.Game?.player
                || !!window.SceneManager?.isLoading || isCurrent;
            enterButton.title = selectedWorld?.testOnly
                ? (isCurrent ? '当前已经位于该测试位面' : '从交互开发工具直接进入该运行期测试现场')
                : '请先对目标位面执行“测试打通并直连”';
        }
        if (resetButton) {
            resetButton.disabled = !selectedWorld?.testOnly || !!window.SceneManager?.isLoading;
            resetButton.title = selectedWorld?.testOnly
                ? '清空本次运行中的测试现场并重新生成地块'
                : '请先对目标位面执行“测试打通并直连”';
        }
        const elapsedDays = model.nowGameTimeMs / Math.max(1, model.dayDurationMs);
        const invasion = model.active
            ? `${model.active.targetWorld} 第${model.active.waveIndex}/${model.active.waveCount}波`
            : '无';
        summary.innerHTML = `游戏时间：${elapsedDays.toFixed(2)} 天 · 入侵轮次：${model.cycle} · `
            + `当前入侵：${invasion}<br>候选池：${model.candidatePool.length ? model.candidatePool.join(', ') : '空'}`;
        rows.innerHTML = model.worlds.map((world) => {
            const protectionDays = world.protectionRemainingMs / Math.max(1, model.dayDurationMs);
            const requiredDungeons = world.requiredDungeons || [];
            const completedRequirements = requiredDungeons.filter((entry) => entry.completed).length;
            const requirementText = requiredDungeons.length
                ? `${completedRequirements}/${requiredDungeons.length} · ${requiredDungeons.map((entry) =>
                    `${entry.dungeonType}${entry.completed ? '✓' : '✕'}`).join(', ')}`
                : '无';
            const snapshot = world.snapshot.exists
                ? `epoch ${world.snapshot.worldEpoch} · 建筑 ${world.snapshot.structures} · 单位 ${world.snapshot.units}`
                    + ` · 资源点 ${world.snapshot.resourceNodes} · 道路 ${world.snapshot.roads}`
                : '无快照';
            const sandstorm = world.sceneId === 'scene8'
                ? window.World122SandstormSystem?.getDebugModel?.()
                : null;
            let sandstormHtml = '';
            if (sandstorm) {
                const remainingDays = sandstorm.remainingMs === null
                    ? null : sandstorm.remainingMs / Math.max(1, sandstorm.dayDurationMs);
                const statusText = sandstorm.phase === 'active'
                    ? `进行中 · 剩余 ${remainingDays?.toFixed(2) ?? '--'} 天 · 视野 ×${sandstorm.visionMultiplier}`
                    : (sandstorm.phase === 'warning'
                        ? `预警中 · ${remainingDays?.toFixed(2) ?? '--'} 天后爆发`
                        : (remainingDays === null ? '平静 · 尚未排期' : `平静 · ${remainingDays.toFixed(2)} 天后预警`));
                sandstormHtml = `<div class="dev-tool-world-event">
                    <span class="dev-tool-warning">🌪 沙尘暴：${statusText}</span>
                    <button type="button" class="dev-tool-menu-btn" data-dev-world-action="sandstorm" data-scene-id="scene8">触发沙尘暴</button>
                </div>`;
            }
            const drought = world.sceneId === 'scene8'
                ? window.World122DroughtSystem?.getDebugModel?.()
                : null;
            let droughtHtml = '';
            if (drought) {
                const remainingDays = drought.remainingMs === null
                    ? null : drought.remainingMs / Math.max(1, drought.dayDurationMs);
                const statusText = drought.phase === 'active'
                    ? `进行中 · 剩余 ${remainingDays?.toFixed(2) ?? '--'} 天 · 粮食 ×${drought.foodProductionMultiplier}`
                    : (drought.phase === 'warning'
                        ? `高温预警 · ${remainingDays?.toFixed(2) ?? '--'} 天后开始`
                        : (remainingDays === null ? '正常 · 尚未排期' : `正常 · ${remainingDays.toFixed(2)} 天后预警`));
                droughtHtml = `<div class="dev-tool-world-event">
                    <span class="dev-tool-warning">☀ 干旱：${statusText}</span>
                    <button type="button" class="dev-tool-menu-btn" data-dev-world-action="drought" data-scene-id="scene8">触发干旱</button>
                </div>`;
            }
            const fogTide = world.sceneId === 'scene11'
                ? window.__phaserScene?.getWorld125AtmosphereDebugModel?.()
                : null;
            let fogTideHtml = '';
            if (fogTide) {
                const statusText = fogTide.active
                    ? `进行中 · 视野 ×${fogTide.unitVisionMultiplier} · 僵尸移速 ×${fogTide.zombieMoveSpeedMultiplier} / 攻击间隔 ×${fogTide.zombieAttackIntervalMultiplier}`
                    : (fogTide.available ? `待命 · 可用守夜烛台 ${fogTide.candleCount || 0} 座` : '待命 · 请先进入世界-125');
                const actionText = fogTide.active ? '结束死寂雾潮' : '触发死寂雾潮';
                fogTideHtml = `<div class="dev-tool-world-event">
                    <span>☣ 死寂雾潮：${statusText}</span>
                    <button type="button" class="dev-tool-menu-btn" data-dev-world-action="fog-tide" data-scene-id="scene11"
                        ${fogTide.enabled ? '' : 'disabled'} aria-pressed="${!!fogTide.active}">${actionText}</button>
                </div>`;
            }
            const rain = window.__phaserScene?.getRainWeatherDebugModel?.(world.sceneId);
            const mineWeather = world.sceneId === 'scene12' ? window.World126WeatherSystem?.getDebugModel?.() : null;
            const mineWeatherHtml = mineWeather ? `<div class="dev-tool-world-event">
                <div>矿洞天气：${mineWeather.name} · ${mineWeather.active ? '剩余' : '距开始'} ${mineWeather.remainingDays.toFixed(2)}天
                    · 天气敌人 ${mineWeather.alive}/18 · 本轮已生成 ${mineWeather.generated}/36 · 待生成 ${mineWeather.pending}</div>
                ${mineWeather.error ? '<div class="dev-tool-warning">怪物资源加载失败，稍后重试；可正常离场</div>' : ''}
                <div class="dev-tool-actions">${mineWeather.kinds.map((entry) =>
                    `<button type="button" class="dev-tool-menu-btn" data-dev-world-action="mine-weather" data-scene-id="scene12"
                        data-weather-kind="${entry.id}" ${mineWeather.available ? '' : 'disabled'} aria-pressed="${mineWeather.active && mineWeather.kind === entry.id}">${mineWeather.active && mineWeather.kind === entry.id ? '结束' : '触发'}${entry.name}</button>`).join('')}</div>
            </div>` : '';
            let rainHtml = '';
            if (rain?.enabled) {
                const statusText = rain.active
                    ? `${rain.intensityName}进行中 · ${rain.quality} 品质 · 无玩法影响`
                    : (rain.available ? '待命 · 无玩法影响' : '待命 · 请先进入该位面');
                const intensityButtons = (rain.intensities || []).map((intensity) => {
                    const selected = rain.active && rain.intensityId === intensity.id;
                    const label = selected ? `结束${intensity.name}` : intensity.name;
                    return `<button type="button" class="dev-tool-menu-btn" data-dev-world-action="rain" data-scene-id="${world.sceneId}"
                        data-rain-intensity="${intensity.id}" ${rain.available ? '' : 'disabled'}
                        aria-pressed="${selected}">${label}</button>`;
                }).join('');
                rainHtml = `<div class="dev-tool-world-event">
                    <span>🌧 降雨：${statusText}</span>
                    <span class="dev-tool-actions">${intensityButtons}</span>
                </div>`;
            }
            const destruction = window.WorldDestructionChallengeSystem?.getWorldModel?.(world.sceneId);
            let destructionHtml = '';
            if (destruction) {
                const nextBatchSeconds = destruction.remainingMs === null
                    ? null : Math.ceil(destruction.remainingMs / 1000);
                const statusText = destruction.active
                    ? `进行中 · 第 ${destruction.cycleNumber} 周期 · 普通 ${destruction.normalSpawned} / 精英 ${destruction.eliteSpawned} / 领主 ${destruction.lordSpawned}`
                        + ` · 本周期精英×${destruction.eliteCountThisCycle} / 领主×${destruction.lordCountThisCycle}`
                        + (destruction.aliveCount === null ? '' : ` · 存活 ${destruction.aliveCount}/${destruction.softMaxAlive}（硬上限${destruction.hardMaxAlive}）`)
                        + (destruction.pendingSpawnCount > 0 ? ` · 待生成 ${destruction.pendingSpawnCount}` : '')
                        + ` · 下批 ${nextBatchSeconds ?? '--'}s`
                    : (destruction.canTrigger ? '待命' : '不可触发 · 需要存活的传送门');
                destructionHtml = `<div class="dev-tool-world-event">
                    <span class="dev-tool-danger-text">☄ 毁灭挑战：${statusText}</span>
                    <button type="button" class="dev-tool-menu-btn danger" data-dev-world-action="destruction-challenge" data-scene-id="${world.sceneId}"
                        ${destruction.canTrigger ? '' : 'disabled'}>${destruction.active ? '挑战进行中' : '触发毁灭挑战'}</button>
                </div>`;
            }
            return `<div class="dev-tool-card dev-tool-world-card${world.candidate ? ' is-candidate' : ''}">
                <div><b>${world.name}</b>${world.testOnly ? ' · 运行期测试' : ''} · ${world.status} · epoch ${world.worldEpoch} · HP ${Math.ceil(world.hp)}</div>
                <div class="dev-tool-help">
                    候选：${world.candidate ? '是' : '否'} · 保护：${world.protected ? `${protectionDays.toFixed(2)} 天` : '无'} ·
                    生成 v${world.generationVersion} / seed ${world.generationSeed}
                </div>
                <div class="dev-tool-help">地牢前置：${requirementText} · 首次构造：${world.constructionEnabled ? '开放' : '配置关闭'}</div>
                <div class="dev-tool-help">快照：${snapshot}</div>
                ${sandstormHtml}
                ${droughtHtml}
                ${fogTideHtml}
                ${mineWeatherHtml}
                ${rainHtml}
                ${destructionHtml}
            </div>`;
        }).join('');
    };

    root.querySelector('#devWorldRefresh').addEventListener('click', renderWorldDebug);
    root.querySelector('#devWorldSelect').addEventListener('change', renderWorldDebug);
    root.querySelector('#devWorldRows').addEventListener('click', (event) => {
        const button = event.target?.closest?.('[data-dev-world-action]');
        if (!button) return;
        const action = button.dataset.devWorldAction;
        if (action === 'sandstorm' && button.dataset.sceneId === 'scene8') {
            const result = window.World122SandstormSystem?.debugTriggerNow?.();
            if (DevTool && typeof DevTool._showToast === 'function') {
                DevTool._showToast(result?.ok
                    ? '🌪 世界122沙尘暴已触发'
                    : `✕ ${result?.reason || '沙尘暴系统尚未初始化'}`);
            }
        } else if (action === 'drought' && button.dataset.sceneId === 'scene8') {
            const rainState = window.WorldWeatherSystem?.getVisualState?.('scene8');
            if (rainState?.active) {
                window.__phaserScene?.toggleRainWeather?.('scene8', rainState.intensityId);
            }
            const result = window.World122DroughtSystem?.debugTriggerNow?.();
            if (DevTool && typeof DevTool._showToast === 'function') {
                DevTool._showToast(result?.ok
                    ? '☀ 世界122干旱已触发'
                    : `✕ ${result?.reason || '干旱系统尚未初始化'}`);
            }
        } else if (action === 'fog-tide' && button.dataset.sceneId === 'scene11') {
            const result = window.__phaserScene?.toggleWorld125FogTide?.();
            if (DevTool && typeof DevTool._showToast === 'function') {
                DevTool._showToast(result?.ok
                    ? (result.model?.active ? '☣ 世界125死寂雾潮已触发' : '✓ 世界125死寂雾潮已结束')
                    : `✕ ${result?.reason || '死寂雾潮系统尚未初始化'}`);
            }
        } else if (action === 'mine-weather' && button.dataset.sceneId === 'scene12') {
            const result = window.World126WeatherSystem?.debugToggle?.(button.dataset.weatherKind);
            DevTool?._showToast?.(result?.ok ? '矿洞天气状态已更新' : `✕ ${result?.reason || '矿洞天气尚未初始化'}`);
        } else if (action === 'rain') {
            const sceneId = button.dataset.sceneId;
            const intensityId = button.dataset.rainIntensity || 'light';
            const result = window.__phaserScene?.toggleRainWeather?.(sceneId, intensityId);
            if (DevTool && typeof DevTool._showToast === 'function') {
                DevTool._showToast(result?.ok
                    ? (result.model?.active
                        ? `🌧 ${sceneId} ${result.model.intensityName}已触发`
                        : `✓ ${sceneId} 降雨已结束`)
                    : `✕ ${result?.reason || '降雨系统尚未初始化'}`);
            }
        } else if (action === 'destruction-challenge') {
            const sceneId = button.dataset.sceneId;
            const result = window.WorldDestructionChallengeSystem?.trigger?.(sceneId);
            if (DevTool && typeof DevTool._showToast === 'function') {
                DevTool._showToast(result?.ok
                    ? `☄ ${sceneId} 毁灭挑战已触发`
                    : `✕ ${result?.reason || '毁灭挑战系统尚未初始化'}`);
            }
        }
        renderWorldDebug();
    });
    root.querySelector('#devWorldAdvance1').addEventListener('click', () => {
        window.WorldInvasionSystem?.debugAdvanceDays?.(1);
        window.World122SandstormSystem?.syncToCurrentTime?.({ notifyPlayer: false });
        window.World122DroughtSystem?.syncToCurrentTime?.({ notifyPlayer: false });
        renderWorldDebug();
    });
    root.querySelector('#devWorldAdvance5').addEventListener('click', () => {
        window.WorldInvasionSystem?.debugAdvanceDays?.(5);
        window.World122SandstormSystem?.syncToCurrentTime?.({ notifyPlayer: false });
        window.World122DroughtSystem?.syncToCurrentTime?.({ notifyPlayer: false });
        renderWorldDebug();
    });
    const instantInvasionButton = root.querySelector('#devWorldInstantInvasion');
    instantInvasionButton.addEventListener('click', async () => {
        if (instantInvasionButton.disabled) return;
        const status = root.querySelector('#devWorldInvasionResult');
        instantInvasionButton.disabled = true;
        instantInvasionButton.setAttribute('aria-busy', 'true');
        instantInvasionButton.textContent = '正在准备入侵…';
        status.textContent = '正在准备同族编队并读取资源预算；不会推进世界时间。';
        try {
            const result = await window.WorldInvasionSystem?.debugGenerateInvasionHere?.();
            status.textContent = result?.ok
                ? `✓ ${result.familyName}已在当前位面开始${result.testOnly ? '测试入侵（不计正式轮次）' : '入侵'}${result.fromMarch ? '（现有军团立即抵达，保留战损）' : '（已跳过集结和一天行军）'}；怪物按正式波次及资源加载进度出场。`
                : `✕ ${result?.reason || '位面入侵系统尚未初始化'}`;
            DevTool?._showToast?.(status.textContent);
        } catch (error) {
            status.textContent = `✕ 生成入侵失败：${error?.message || error}`;
            DevTool?._showToast?.(status.textContent);
        } finally {
            instantInvasionButton.disabled = false;
            instantInvasionButton.removeAttribute('aria-busy');
            instantInvasionButton.textContent = '立即生成入侵';
            renderWorldDebug();
        }
    });
    root.querySelector('#devWorldUnlock').addEventListener('click', () => {
        const sceneId = root.querySelector('#devWorldSelect')?.value;
        if (!sceneId) return;
        const result = window.WorldProgressionSystem?.debugUnlockWorld?.(sceneId);
        if (DevTool && typeof DevTool._showToast === 'function') {
            if (!result?.ok) {
                DevTool._showToast(`✕ ${result?.reason || '打通位面失败'}`);
            } else {
                DevTool._showToast(result.alreadyConnected
                    ? `✓ ${sceneId} 已经在传送网络中${result.testOnly ? '，测试现场保持不变' : ''}`
                    : `✓ ${sceneId} 测试直连已开启，可从本页直接进入`);
            }
        }
        window.Game?.ProducerBuildingSystem?._panel?.refresh?.();
        renderWorldDebug();
    });
    const enterWorldButton = root.querySelector('#devWorldEnter');
    enterWorldButton.addEventListener('click', async () => {
        const sceneId = root.querySelector('#devWorldSelect')?.value;
        if (!sceneId || enterWorldButton.disabled
            || !window.WorldProgressionSystem?.isDevWorldUnlocked?.(sceneId)) return;
        enterWorldButton.disabled = true;
        enterWorldButton.setAttribute('aria-busy', 'true');
        enterWorldButton.textContent = '正在进入…';
        try {
            DevTool.hide();
            const entered = await window.SceneManager?.switchScene?.(
                sceneId,
                window.Game?.player,
                undefined,
                { observer: false }
            );
            if (!entered || window.SceneManager?.currentScene !== sceneId) {
                DevTool?._showToast?.(`✕ ${sceneId} 测试位面进入失败`);
            }
        } catch (error) {
            DevTool?._showToast?.(`✕ 测试位面进入失败：${error?.message || error}`);
        } finally {
            enterWorldButton.removeAttribute('aria-busy');
            enterWorldButton.textContent = '进入测试位面';
            renderWorldDebug();
        }
    });
    const resetWorldButton = root.querySelector('#devWorldReset');
    resetWorldButton.addEventListener('click', async () => {
        const sceneId = root.querySelector('#devWorldSelect')?.value;
        if (!sceneId || resetWorldButton.disabled
            || !window.confirm(`确认清空 ${sceneId} 本次运行中的全部测试现场？`)) return;
        resetWorldButton.disabled = true;
        resetWorldButton.setAttribute('aria-busy', 'true');
        resetWorldButton.textContent = '正在重置…';
        try {
            const result = await window.SceneManager?.resetDevWorld?.(sceneId);
            DevTool?._showToast?.(result?.ok
                ? `✓ ${sceneId} 测试位面已重置，下次进入将重新生成`
                : `✕ ${result?.reason || '测试位面重置失败'}`);
        } catch (error) {
            DevTool?._showToast?.(`✕ 测试位面重置失败：${error?.message || error}`);
        } finally {
            resetWorldButton.removeAttribute('aria-busy');
            resetWorldButton.textContent = '重置测试位面';
            window.Game?.ProducerBuildingSystem?._panel?.refresh?.();
            renderWorldDebug();
        }
    });
    root.querySelector('#devWorldDestroy').addEventListener('click', () => {
        const sceneId = root.querySelector('#devWorldSelect')?.value;
        if (!sceneId || !window.confirm(`确认模拟摧毁 ${sceneId} 的传送门？`)) return;
        const result = window.WorldInvasionSystem?.debugDestroyPortal?.(sceneId);
        if (!result?.ok && DevTool && typeof DevTool._showToast === 'function') {
            DevTool._showToast(`✕ ${result?.reason || '模拟毁门失败'}`);
        }
        renderWorldDebug();
    });

    // ===== Tab 内容：战争迷雾调试 =====
    const contentFog = document.createElement('div');
    contentFog.className = 'dev-tool-tab-content';
    contentFog.dataset.tabContent = 'fog';
    contentFog.style.cssText = 'display:none;';
    const fogWrap = document.createElement('div');
    fogWrap.className = 'dev-tool-page';
    fogWrap.innerHTML = `
        <div class="dev-tool-page-intro">
            <p>🌫 战争迷雾调试：显示逻辑格、三态、视野源半径和实时更新开销。</p>
            <p class="dev-tool-help">调试层只影响显示，不修改探索记录、AI、战斗或 RTS 目标门禁。</p>
        </div>
        <div class="dev-tool-card dev-tool-actions">
            <label><input id="devFogEnabled" type="checkbox"> 调试覆盖层</label>
            <label><input id="devFogStates" type="checkbox" checked> 三态填色</label>
            <label><input id="devFogGrid" type="checkbox" checked> 网格</label>
            <label><input id="devFogSources" type="checkbox" checked> 视野源</label>
            <label><input id="devFogBlockers" type="checkbox" checked> LOS 阻挡格</label>
            <label><input id="devFogMask" type="checkbox" checked> 主遮罩</label>
            <button id="devFogRefresh" class="dev-tool-menu-btn">刷新数据</button>
        </div>
        <div class="dev-tool-card-grid">
            <section class="dev-tool-card"><h3>迷雾状态</h3><div id="devFogSummary" class="dev-tool-summary"></div></section>
            <section class="dev-tool-card"><h3>视野源</h3><div id="devFogSourcesList" class="dev-tool-data-list"></div></section>
        </div>`;
    contentFog.appendChild(fogWrap);
    root.appendChild(contentFog);

    const fogControl = (id) => root.querySelector(`#${id}`);
    const renderFogDebug = () => {
        const scene = window.__phaserScene;
        const model = scene?.getFogDebugModel?.();
        const summary = fogControl('devFogSummary');
        const list = fogControl('devFogSourcesList');
        if (!model || !summary || !list) {
            if (summary) summary.textContent = '当前场景未启用战争迷雾';
            if (list) list.textContent = '';
            return;
        }
        fogControl('devFogEnabled').checked = !!model.options?.enabled;
        fogControl('devFogStates').checked = model.options?.showStates !== false;
        fogControl('devFogGrid').checked = model.options?.showGrid !== false;
        fogControl('devFogSources').checked = model.options?.showSources !== false;
        fogControl('devFogBlockers').checked = model.options?.showBlockers !== false;
        fogControl('devFogMask').checked = model.render?.maskVisible !== false;
        summary.innerHTML = `${model.sceneId} · ${model.columns}×${model.rows} · revision ${model.revision}<br>`
            + `可见 ${model.visibleCells} · 已探索 ${model.exploredCells} · 未探索 ${model.unexploredCells}<br>`
            + `视野源 ${model.update?.sourceCount || 0} · 逻辑 ${(model.update?.durationMs || 0).toFixed(3)}ms`
            + ` · 变化格 ${model.update?.changedCells || 0} · 新探索 ${model.update?.exploredCells || 0}<br>`
            + `遮罩 ${(model.render?.durationMs || 0).toFixed(3)}ms · 特效契约 ${model.effects?.explicit || 0}`
            + ` / 兼容 ${model.effects?.legacy || 0}<br>`
            + `LOS 阻挡 ${model.occlusion?.blockerCount || 0} · 阻挡格 ${model.occlusion?.blockedCells || 0}`
            + ` · 最高 ${Math.round(model.occlusion?.maxBlockerHeight || 0)}`
            + ` · 重建 ${(model.occlusion?.durationMs || 0).toFixed(3)}ms<br>`
            + `可见性受控 ${model.visibility?.controlledEntities || 0} · 当前隐藏 ${model.visibility?.enforcedHiddenEntities || 0}`
            + ` · 同步 ${(model.visibility?.durationMs || 0).toFixed(3)}ms`;
        list.innerHTML = (model.sources || []).map((source) => (
            `<div>${source.name} · ${source.profile} · R${Math.round(source.radius)}`
            + ` · (${Math.round(source.x)}, ${Math.round(source.y)})</div>`
        )).join('') || '当前没有有效视野源';
    };
    const applyFogDebug = () => {
        const scene = window.__phaserScene;
        scene?.setFogDebugOptions?.({
            enabled: !!fogControl('devFogEnabled')?.checked,
            showStates: !!fogControl('devFogStates')?.checked,
            showGrid: !!fogControl('devFogGrid')?.checked,
            showSources: !!fogControl('devFogSources')?.checked,
            showBlockers: !!fogControl('devFogBlockers')?.checked,
            maskVisible: !!fogControl('devFogMask')?.checked,
        });
        renderFogDebug();
    };
    for (const id of ['devFogEnabled', 'devFogStates', 'devFogGrid', 'devFogSources', 'devFogBlockers', 'devFogMask']) {
        fogControl(id).addEventListener('change', applyFogDebug);
    }
    fogControl('devFogRefresh').addEventListener('click', renderFogDebug);

    // ===== Tab 内容：性能采样 =====
    const contentPerformance = document.createElement('div');
    contentPerformance.className = 'dev-tool-tab-content';
    contentPerformance.dataset.tabContent = 'performance';
    contentPerformance.style.cssText = 'display:none;';
    const performanceWrap = document.createElement('div');
    performanceWrap.className = 'dev-tool-page';
    performanceWrap.innerHTML = `
        <div class="dev-tool-page-intro">
            <p>📊 性能采样：区分 JS/CPU 执行、帧调度缺口，并定位 Phaser 更新、天气、迷雾、阴影与实体视觉压力。</p>
            <p class="dev-tool-help">本页只读，不修改战斗、AI、画质或游戏速度；Phaser 渲染提交的 CPU 耗时会单列，GPU 执行/合成与调度等待仍保留在“非 JS 采样间隔”中。</p>
        </div>
        <div class="dev-tool-actions">
            <label>
                统计周期
                <select id="devPerformanceWindow">
                    <option value="60">最近 60 帧</option>
                    <option value="120" selected>最近 120 帧</option>
                    <option value="240">最近 240 帧</option>
                </select>
            </label>
            <button id="devPerformanceRefresh" class="dev-tool-menu-btn">刷新</button>
            <button id="devPerformanceReset" class="dev-tool-menu-btn">重置采样</button>
            <button id="devPerformanceCopy" class="dev-tool-menu-btn">📋 复制性能报告</button>
            <span id="devPerformanceCopyStatus" class="dev-tool-status" role="status" aria-live="polite"></span>
        </div>
        <div class="dev-tool-card-grid">
            <div id="devPerformanceSummary" class="dev-tool-card dev-tool-summary"></div>
            <div id="devPerformanceDiagnostics" class="dev-tool-card dev-tool-summary"></div>
            <div id="devPerformanceSections" class="dev-tool-card dev-tool-span-all"></div>
            <div id="devPerformanceCounters" class="dev-tool-card dev-tool-summary dev-tool-span-all"></div>
        </div>`;
    contentPerformance.appendChild(performanceWrap);
    root.appendChild(contentPerformance);

    const performanceControl = (id) => root.querySelector(`#${id}`);
    const performanceLabels = {
        gameUpdate: '逻辑主循环',
        legacyRender: 'Canvas 渲染',
        phaserSync: 'Phaser 同步（旧总项）',
        phaserWorldSystems: 'Phaser · 世界系统',
        phaserTerrainFog: 'Phaser · 地形/迷雾',
        phaserEntityVisuals: 'Phaser · 实体/特效同步',
        phaserShadowsVisibility: 'Phaser · 阴影/可见性',
        phaserWeather: 'Phaser · 天气粒子',
        phaserWorldAtmosphere: 'Phaser · 位面氛围',
        phaserRenderSubmit: 'Phaser · 渲染提交',
        domUi: 'DOM UI 刷新',
        'wallCollapse.landing': '坍塌落点搜索',
        'collision.separation': '单位碰撞分离',
    };
    const getPerformanceWindowFrames = () => (
        Number(performanceControl('devPerformanceWindow')?.value) || 120
    );
    const getPerformanceRanking = (model) => Object.entries(model.sections)
        .map(([name, value]) => ({ name, label: performanceLabels[name] || name, ...value }))
        .sort((a, b) => b.averageMs - a.averageMs || b.maxMs - a.maxMs || a.name.localeCompare(b.name));
    const formatPerformanceValue = (value, digits = 2) => {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) return String(value ?? '');
        return numeric.toFixed(digits).replace(/\.00$/, '');
    };
    const escapePerformanceHtml = (value) => String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    const getPerformanceDiagnostics = (model) => {
        if (!model.sampleFrames) return ['等待至少 30 帧采样后生成诊断线索。'];
        const ranking = getPerformanceRanking(model);
        const top = ranking[0];
        const diagnostics = [];
        if (model.averageRawDtMs >= model.slowFrameThresholdMs
            && model.cpuFrameBudgetPercent < 60) {
            diagnostics.push(
                `平均帧间隔 ${model.averageRawDtMs.toFixed(2)}ms，但已测 JS/CPU 只占 ${model.cpuFrameBudgetPercent.toFixed(1)}%；`
                + '优先排查 GPU/合成、垂直同步或浏览器调度，不要只按 CPU 分项占比下结论。'
            );
        }
        if (model.windowIntervalSlowFrames > model.windowCpuSlowFrames) {
            diagnostics.push(
                `帧间隔慢帧 ${model.windowIntervalSlowFrames} 帧，高于 CPU 慢帧 ${model.windowCpuSlowFrames} 帧；`
                + '卡顿主要发生在当前 JS 采样区间之外。'
            );
        }
        if (top && (top.p95Ms >= 4 || top.maxMs >= 8)) {
            diagnostics.push(
                `当前最重 CPU 分项是“${top.label}”：P95 ${top.p95Ms.toFixed(2)}ms、峰值 ${top.maxMs.toFixed(2)}ms。`
            );
        }
        if (model.p99FrameMs > Math.max(4, model.averageFrameMs * 2.5)) {
            diagnostics.push(
                `CPU 尾部抖动明显：平均 ${model.averageFrameMs.toFixed(2)}ms，P99 ${model.p99FrameMs.toFixed(2)}ms；`
                + '结合异常帧样本查看是否由周期任务触发。'
            );
        }
        const counters = model.counters || {};
        const rainAlive = (Number(counters['weather.rainStreakAlive']) || 0)
            + (Number(counters['weather.rainSplashAlive']) || 0);
        const sandAlive = (Number(counters['weather.sandGroundAlive']) || 0)
            + (Number(counters['weather.sandForegroundAlive']) || 0);
        if (rainAlive > 0 || sandAlive > 0) {
            diagnostics.push(
                `天气粒子快照：雨 ${rainAlive}、扬沙 ${sandAlive}；`
                + '可用同场景开/关天气的两份报告做 A/B 对比。'
            );
        }
        if (Number(counters['fog.maskRenderMs']) >= 1) {
            diagnostics.push(`迷雾遮罩最近一次同步耗时 ${Number(counters['fog.maskRenderMs']).toFixed(2)}ms。`);
        }
        const shadowVisibleJobs = Number(counters['shadow.visibleJobs']) || 0;
        const shadowCulledJobs = Number(counters['shadow.viewportCulled']) || 0;
        const shadowPreCulled = Number(counters['shadow.preGeometryCulled']) || 0;
        const shadowPostCulled = Number(counters['shadow.postGeometryCulled']) || 0;
        const shadowTriangles = Number(counters['shadow.triangles']) || 0;
        const shadowRebuildMs = Number(counters['shadow.lastRebuildMs']) || 0;
        const shadowRebuildPeakMs = Number(counters['shadow.rebuildPeakMs']) || 0;
        const shadowRebuildTotalMs = Number(counters['shadow.rebuildTotalMs']) || 0;
        const shadowRawVertices = Number(counters['shadow.rawContourVertices']) || 0;
        const shadowContourVertices = Number(counters['shadow.contourVertices']) || 0;
        const shadowReduction = Number(counters['shadow.contourReductionPercent']) || 0;
        if (shadowVisibleJobs > 0 || shadowCulledJobs > 0) {
            diagnostics.push(
                `结构阴影快照：质量 ${counters['shadow.quality'] || 'unknown'}，`
                + `图层${Number(counters['shadow.layerVisible']) ? '显示' : '隐藏'}，`
                + `可见 ${shadowVisibleJobs}、视口裁切 ${shadowCulledJobs}`
                + `（几何前 ${shadowPreCulled} / 几何后 ${shadowPostCulled}）、`
                + `裁切缓冲 ${Number(counters['shadow.viewportPaddingPx']) || 0}px、`
                + `轮廓 ${shadowRawVertices}→${shadowContourVertices}（-${shadowReduction.toFixed(1)}%）、`
                + `缓存三角形 ${shadowTriangles}、命令缓冲 ${Number(counters['shadow.commandBufferLength']) || 0}。`
            );
        }
        if (shadowRebuildMs >= 2 || shadowRebuildPeakMs >= 2) {
            diagnostics.push(
                `结构阴影脏重建：最近 ${shadowRebuildMs.toFixed(2)}ms、`
                + `峰值 ${shadowRebuildPeakMs.toFixed(2)}ms、累计 ${shadowRebuildTotalMs.toFixed(2)}ms；`
                + `累计重建 ${Number(counters['shadow.rebuilds']) || 0} 次，`
                + '请结合太阳移动开启/关闭报告判断重建尖峰，稳态提交则看 phaserRenderSubmit。'
            );
        }
        if (!diagnostics.length) diagnostics.push('当前窗口未命中明显的启发式告警；仍应结合 CPU 排行、异常帧和运行计数器判断。');
        return diagnostics;
    };
    const getPerformanceCounterGroups = (counters) => {
        const groups = new Map();
        for (const [name, value] of Object.entries(counters || {}).sort(([a], [b]) => a.localeCompare(b))) {
            const separator = name.indexOf('.');
            const group = separator > 0 ? name.slice(0, separator) : 'other';
            if (!groups.has(group)) groups.set(group, []);
            groups.get(group).push([name, value]);
        }
        return groups;
    };
    const buildPerformanceReport = (model) => {
        const ranking = getPerformanceRanking(model);
        const counterGroups = getPerformanceCounterGroups(model.counters);
        const diagnostics = getPerformanceDiagnostics(model);
        const markdownCell = (value) => String(value ?? '').replace(/\|/g, '\\|').replace(/[\r\n]+/g, ' ');
        const frameSectionSummary = (frame) => Object.entries(frame.sections || {})
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([name, value]) => `${performanceLabels[name] || name} ${Number(value).toFixed(2)}ms`)
            .join('；') || '无分项';
        const lines = [
            '# 无限轮回性能采样报告',
            '',
            `- 导出时间：${new Date().toLocaleString('zh-CN', { hour12: false })}`,
            `- 统计周期：最近 ${model.requestedFrames} 帧（实际 ${model.sampleFrames} 帧，约 ${(model.sampleDurationMs / 1000).toFixed(2)} 秒）`,
            `- 平均 FPS：${model.averageFps.toFixed(1)}`,
            `- 帧间隔：平均 ${model.averageRawDtMs.toFixed(2)}ms / P50 ${model.p50RawDtMs.toFixed(2)}ms / P95 ${model.p95RawDtMs.toFixed(2)}ms / P99 ${model.p99RawDtMs.toFixed(2)}ms / 峰值 ${model.maxRawDtMs.toFixed(2)}ms`,
            `- 已测 JS/CPU：平均 ${model.averageFrameMs.toFixed(2)}ms / P95 ${model.p95FrameMs.toFixed(2)}ms / P99 ${model.p99FrameMs.toFixed(2)}ms / 峰值 ${model.maxFrameMs.toFixed(2)}ms`,
            `- 非 JS 采样间隔：平均 ${model.averageFrameIntervalGapMs.toFixed(2)}ms / P95 ${model.p95FrameIntervalGapMs.toFixed(2)}ms / 峰值 ${model.maxFrameIntervalGapMs.toFixed(2)}ms`,
            `- 已测 JS/CPU 占平均帧间隔：${model.cpuFrameBudgetPercent.toFixed(1)}%（未归入分项的 CPU 平均 ${model.unprofiledCpuAverageMs.toFixed(3)}ms）`,
            `- CPU 慢帧：${model.windowCpuSlowFrames}/${model.sampleFrames}（${model.windowCpuSlowFramePercent.toFixed(1)}%）`,
            `- 帧间隔慢帧：${model.windowIntervalSlowFrames}/${model.sampleFrames}（${model.windowIntervalSlowFramePercent.toFixed(1)}%）`,
            `- 任一口径慢帧：${model.windowSlowFrames}/${model.sampleFrames}（${model.windowSlowFramePercent.toFixed(1)}%，阈值 ${model.slowFrameThresholdMs.toFixed(2)}ms）`,
            '',
            '## 自动诊断线索',
            '',
            ...diagnostics.map((message) => `- ${message}`),
            '',
            '## CPU 耗时排行',
            '',
            '> “占已测分项”用于比较 CPU 分项内部优先级；“占墙钟”按整个统计周期计算。渲染提交、GPU、合成与等待不包含在 CPU 分项中。',
            '',
            '| 排名 | 项目 | 占已测分项 | 占墙钟 | 平均 | P50 | P95 | P99 | 峰值 | 活跃帧 |',
            '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|',
        ];
        if (ranking.length) {
            ranking.forEach((item, index) => {
                lines.push(`| ${index + 1} | ${markdownCell(item.label)} (${markdownCell(item.name)}) | ${item.sharePercent.toFixed(1)}% | ${item.wallSharePercent.toFixed(1)}% | ${item.averageMs.toFixed(3)}ms | ${item.p50Ms.toFixed(3)}ms | ${item.p95Ms.toFixed(3)}ms | ${item.p99Ms.toFixed(3)}ms | ${item.maxMs.toFixed(3)}ms | ${item.activeFrames}/${model.sampleFrames} |`);
            });
        } else {
            lines.push('| - | 暂无采样 | 0% | 0% | 0ms | 0ms | 0ms | 0ms | 0ms | 0/0 |');
        }
        const appendFrameTable = (title, frames) => {
            lines.push('', `## ${title}`, '');
            lines.push('| 窗口帧序 | 帧间隔 | JS/CPU | 非 JS 间隔 | 最重分项 |');
            lines.push('|---:|---:|---:|---:|---|');
            if (!frames?.length) {
                lines.push('| - | 0ms | 0ms | 0ms | 无样本 |');
                return;
            }
            for (const frame of frames) {
                lines.push(`| ${frame.sampleIndex}/${model.sampleFrames} | ${frame.rawDtMs.toFixed(2)}ms | ${frame.cpuMs.toFixed(2)}ms | ${frame.intervalGapMs.toFixed(2)}ms | ${markdownCell(frameSectionSummary(frame))} |`);
            }
        };
        appendFrameTable('帧间隔最慢样本', model.slowestIntervalFrames);
        appendFrameTable('JS/CPU 最慢样本', model.slowestCpuFrames);
        lines.push('', '## 运行环境与计数器快照', '');
        lines.push('> 以下是导出瞬间的快照，不是窗口平均值。', '');
        if (counterGroups.size) {
            for (const [group, entries] of counterGroups) {
                lines.push(`### ${markdownCell(group)}`, '');
                for (const [name, value] of entries) {
                    lines.push(`- ${markdownCell(name)}：${markdownCell(formatPerformanceValue(value))}`);
                }
                lines.push('');
            }
        } else {
            lines.push('- 暂无计数器数据', '');
        }
        lines.push(
            '## 口径说明',
            '',
            '- “已测 JS/CPU”包含逻辑主循环、DOM/旧 Canvas 绘制、拆分后的 Phaser update 阶段及 Phaser 渲染提交的 CPU 区间。',
            '- “非 JS 采样间隔”是帧间隔减去已测 JS/CPU 的剩余值，可能包含 GPU/合成、垂直同步、浏览器调度、空闲等待及尚未挂点的代码；它不是纯 GPU 耗时。',
            '- 帧间隔来自逻辑循环 rawDt，并受 sampling.rawDtCapMs 上限约束；长于该上限的停顿会被截断。',
            '- Phaser 子阶段为互斥分段，不再用总项与子项重复累计；旧版本采样中的 phaserSync 仅作兼容显示。',
            '- 自动诊断是启发式线索，不等同于浏览器 Performance trace 或 GPU profiler 结论。'
        );
        return lines.join('\n');
    };
    const copyPerformanceReport = async (text) => {
        try {
            if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable');
            await navigator.clipboard.writeText(text);
            return;
        } catch (_error) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.readOnly = true;
            textarea.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0;';
            document.body.appendChild(textarea);
            let copied = false;
            try {
                textarea.select();
                copied = document.execCommand('copy');
            } finally {
                textarea.remove();
            }
            if (!copied) throw new Error('copy failed');
        }
    };
    const renderPerformanceDebug = () => {
        const model = PerformanceMonitor.getSnapshot(getPerformanceWindowFrames());
        const summary = performanceControl('devPerformanceSummary');
        const diagnostics = performanceControl('devPerformanceDiagnostics');
        const sections = performanceControl('devPerformanceSections');
        const counters = performanceControl('devPerformanceCounters');
        if (!summary || !diagnostics || !sections || !counters) return;
        const ranking = getPerformanceRanking(model);
        const topAverageMs = ranking[0]?.averageMs || 1;
        summary.innerHTML = `周期 最近 ${model.requestedFrames} 帧 · 已采样 ${model.sampleFrames} 帧`
            + ` · 约 ${(model.sampleDurationMs / 1000).toFixed(2)} 秒<br>`
            + `<b>平均 ${model.averageFps.toFixed(1)} FPS</b><br>`
            + `帧间隔 平均 ${model.averageRawDtMs.toFixed(2)}ms · P95 ${model.p95RawDtMs.toFixed(2)}ms`
            + ` · P99 ${model.p99RawDtMs.toFixed(2)}ms · 峰值 ${model.maxRawDtMs.toFixed(2)}ms<br>`
            + `已测 JS/CPU 平均 ${model.averageFrameMs.toFixed(2)}ms · P95 ${model.p95FrameMs.toFixed(2)}ms`
            + ` · 占帧间隔 ${model.cpuFrameBudgetPercent.toFixed(1)}%<br>`
            + `非 JS 采样间隔 平均 ${model.averageFrameIntervalGapMs.toFixed(2)}ms`
            + ` · P95 ${model.p95FrameIntervalGapMs.toFixed(2)}ms<br>`
            + `CPU 慢帧 ${model.windowCpuSlowFrames}/${model.sampleFrames}`
            + `（${model.windowCpuSlowFramePercent.toFixed(1)}%）`
            + ` · 帧间隔慢帧 ${model.windowIntervalSlowFrames}/${model.sampleFrames}`
            + `（${model.windowIntervalSlowFramePercent.toFixed(1)}%）`;
        diagnostics.innerHTML = '<b>自动诊断线索</b>'
            + '<div class="dev-tool-diagnostics">'
            + getPerformanceDiagnostics(model)
                .map((message) => `• ${escapePerformanceHtml(message)}`)
                .join('<br>')
            + '</div>';
        sections.innerHTML = '<b>CPU 耗时排行（平均耗时降序）</b>'
            + '<div class="dev-tool-help">占已测分项用于判断 CPU 优先级；占墙钟用于判断它对实际帧间隔的影响。</div>'
            + (ranking.length ? ranking.map((item, index) => {
                const barWidth = Math.max(2, item.averageMs / topAverageMs * 100);
                return `<div class="dev-tool-perf-row">`
                    + `<div class="dev-tool-perf-bar" style="width:${barWidth.toFixed(1)}%;"></div>`
                    + `<div class="dev-tool-perf-heading">`
                    + `<span><b>#${index + 1} ${escapePerformanceHtml(item.label)}</b> <span class="dev-tool-help">${escapePerformanceHtml(item.name)}</span></span>`
                    + `<span class="dev-tool-number">分项 ${item.sharePercent.toFixed(1)}% · 墙钟 ${item.wallSharePercent.toFixed(1)}%</span></div>`
                    + `<div class="dev-tool-perf-metrics">平均 ${item.averageMs.toFixed(3)}ms`
                    + ` · P50 ${item.p50Ms.toFixed(3)}ms · P95 ${item.p95Ms.toFixed(3)}ms`
                    + ` · P99 ${item.p99Ms.toFixed(3)}ms · 峰值 ${item.maxMs.toFixed(3)}ms`
                    + ` · 活跃 ${item.activeFrames}/${model.sampleFrames} 帧</div></div>`;
            }).join('') : '<div class="dev-tool-help">等待采样数据……</div>');
        const counterGroups = getPerformanceCounterGroups(model.counters);
        counters.innerHTML = '<b>运行环境与计数器快照</b>'
            + '<div class="dev-tool-help">每 500ms 更新一次；导出时记录当前值，不是周期平均。</div>'
            + ([...counterGroups.entries()].map(([group, entries]) => (
                `<div class="dev-tool-counter-heading"><b>${escapePerformanceHtml(group)}</b></div>`
                + entries.map(([name, value]) => (
                    `${escapePerformanceHtml(name)}：${escapePerformanceHtml(formatPerformanceValue(value))}`
                )).join('<br>')
            )).join('') || '<div class="dev-tool-help">暂无计数器数据</div>');
    };
    performanceControl('devPerformanceWindow').addEventListener('change', renderPerformanceDebug);
    performanceControl('devPerformanceRefresh').addEventListener('click', renderPerformanceDebug);
    performanceControl('devPerformanceReset').addEventListener('click', () => {
        PerformanceMonitor.reset();
        renderPerformanceDebug();
    });
    performanceControl('devPerformanceCopy').addEventListener('click', async () => {
        const button = performanceControl('devPerformanceCopy');
        const status = performanceControl('devPerformanceCopyStatus');
        const model = PerformanceMonitor.getSnapshot(getPerformanceWindowFrames());
        try {
            await copyPerformanceReport(buildPerformanceReport(model));
            if (button) button.textContent = '✅ 已复制';
            if (status) status.textContent = `已导出 ${model.sampleFrames} 帧数据`;
        } catch (_error) {
            if (button) button.textContent = '⚠️ 复制失败';
            if (status) status.textContent = '剪贴板不可用，请重新打开面板后再试';
        }
        window.setTimeout(() => {
            if (button?.isConnected) button.textContent = '📋 复制性能报告';
            if (status?.isConnected) status.textContent = '';
        }, 1800);
    });
    const navigationDebug = createNavigationDebug({
        copyText: copyPerformanceReport,
        showPerformance: () => {
            DevTool.switchTab('performance');
            renderPerformanceDebug();
        },
    });
    root.appendChild(navigationDebug.content);
    root._performanceRefreshTimer = window.setInterval(() => {
        if (!root.isConnected) {
            window.clearInterval(root._performanceRefreshTimer);
            root._performanceRefreshTimer = null;
            return;
        }
        if (!DevTool._active) return;
        if (DevTool._currentTab === 'performance') renderPerformanceDebug();
        else if (DevTool._currentTab === 'navigation') navigationDebug.refresh();
    }, 500);

    // ===== 技能等级调试逻辑 =====
    const fillSkillSelect = () => {
        const player = window.Game && window.Game.player;
        const sel = document.getElementById('devToolSkillSelect');
        if (!sel) return;
        const current = sel.value;
        sel.innerHTML = '';
        for (const [id, sk] of Object.entries(player?.skills || {})) {
            if (!sk || sk.hidden === true || sk.disabled === true) continue;
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = `${sk.name || id}（Lv.${sk.level}/${sk.maxLevel || 20}）`;
            sel.appendChild(opt);
        }
        const hasSkills = sel.options.length > 0;
        for (const control of [sel, levelInput, btnMinus, btnPlus, btnApply]) control.disabled = !hasSkills;
        if (!hasSkills) {
            const empty = document.createElement('option');
            empty.textContent = player ? '暂无可调整的技能' : '请先进入游戏';
            empty.value = '';
            sel.appendChild(empty);
            skillStatus.textContent = empty.textContent;
            return;
        }
        if ([...sel.options].some((option) => option.value === current)) sel.value = current;
        updateSkillStatus();
    };
    const updateSkillStatus = () => {
        const player = window.Game && window.Game.player;
        const sel = document.getElementById('devToolSkillSelect');
        const status = document.getElementById('devToolSkillStatus');
        const input = document.getElementById('devToolSkillLevel');
        if (!player || !sel || !status || !input) return;
        const sk = player.skills[sel.value];
        if (!sk) { status.textContent = ''; return; }
        input.max = sk.maxLevel || 20;
        input.value = sk.level;
        status.textContent = sk.level >= (sk.maxLevel || 20)
            ? `${sk.name}：已满级`
            : `${sk.name}：当前 Lv.${sk.level}，升级需 ${sk.maxExp - sk.exp} 经验`;
    };
    const applySkillLevel = (delta) => {
        const player = window.Game && window.Game.player;
        const sel = document.getElementById('devToolSkillSelect');
        const input = document.getElementById('devToolSkillLevel');
        if (!player || !sel || !input || !player.skills[sel.value]) {
            if (DevTool && typeof DevTool._showToast === 'function') DevTool._showToast('❌ 请先进入游戏');
            return;
        }
        const target = delta ? Number(player.skills[sel.value].level) + delta : Number(input.value || 1);
        const result = typeof window.setSkillLevel === 'function'
            ? window.setSkillLevel(sel.value, target)
            : Promise.resolve({ ok: false, error: 'setSkillLevel 未挂载' });
        Promise.resolve(result).then(r => {
            if (r && r.ok) {
                updateSkillStatus();
                fillSkillSelect();
                if (DevTool && typeof DevTool._showToast === 'function') DevTool._showToast(`✅ ${r.name} → Lv.${r.level}`);
            } else if (DevTool && typeof DevTool._showToast === 'function') {
                DevTool._showToast(`❌ ${(r && r.error) || '设置失败'}`);
            }
        });
    };
    skillSelect.addEventListener('change', updateSkillStatus);
    btnPlus.addEventListener('click', () => applySkillLevel(1));
    btnMinus.addEventListener('click', () => applySkillLevel(-1));
    btnApply.addEventListener('click', () => applySkillLevel(0));

    for (const button of root.querySelectorAll('button')) button.type = 'button';
    for (const tab of tabs.querySelectorAll('.dev-tool-tab')) {
        const key = tab.dataset.tab;
        tab.id = `devToolTab-${key}`;
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-controls', `devToolPage-${key}`);
        tab.setAttribute('aria-selected', String(key === 'weapon'));
        tab.tabIndex = key === 'weapon' ? 0 : -1;
        const page = root.querySelector(`[data-tab-content="${key}"]`);
        page.id = `devToolPage-${key}`;
        page.setAttribute('role', 'tabpanel');
        page.setAttribute('aria-labelledby', tab.id);
        page.tabIndex = 0;
    }
    return root;
}
