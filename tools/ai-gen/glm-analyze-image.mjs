#!/usr/bin/env node
/* 用智谱 GLM-4.6V 分析本地图片（绕过 deepseek-vision-skill 的 provider 白名单）
 *
 * 移植自 game-dev-3d/tools/glm-analyze-image.mjs，增强：
 * - 超过阈值的大图先自动缩放（减少 base64 payload，避免 API 拒绝）
 * - 支持多张图、--prompt
 *
 * 用法：
 *   node tools/ai-gen/glm-analyze-image.mjs "图1.png" "图2.png" [--prompt "问题"]
 */
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const CONFIG = JSON.parse(fs.readFileSync('C:/Users/allan/.codex/skills/deepseek-vision-skill/config.json', 'utf8'));
const ENDPOINT = CONFIG.endpoint || 'https://open.bigmodel.cn/api/paas/v4/chat/completions';
const MODEL = CONFIG.model || 'glm-4.6v';
const MAX_B64_MB = 6; // 超过此体量的 base64 先缩放，防止 API 拒绝

function args() {
  const out = { prompt: '请详细描述这张图片的内容。', paths: [] };
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--prompt') { out.prompt = argv[++i] ?? out.prompt; }
    else { out.paths.push(argv[i]); }
  }
  return out;
}

// 用 Python+Pillow 把大图缩放到宽<=2048 且 base64 体积可控（保留长宽比）
function prepare(file) {
  const p = path.resolve(file);
  const raw = fs.statSync(p).size;
  if (raw < MAX_B64_MB * 1024 * 1024 * 0.75) return p;
  const tmp = path.join(process.env.TEMP || '/tmp', `glm-vision-${process.pid}-${Date.now()}.png`);
  const script = `from PIL import Image; im=Image.open(r"${p.replace(/\\/g, '\\\\')}").convert('RGB');
im.thumbnail((2048, 2048)); im.save(r"${tmp.replace(/\\/g, '\\\\')}")`;
  execFileSync('python', ['-c', script]);
  return tmp;
}

const { prompt, paths } = args();
if (paths.length === 0) {
  console.error('用法: node glm-analyze-image.mjs <图1> [图2...] [--prompt "问题"]');
  process.exit(1);
}

const content = [
  { type: 'text', text: prompt },
  ...paths.map((f) => {
    const prepared = prepare(f);
    const b64 = fs.readFileSync(prepared).toString('base64');
    if (prepared !== path.resolve(f)) { try { fs.unlinkSync(prepared); } catch {} }
    return { type: 'image_url', image_url: { url: `data:image/png;base64,${b64}` } };
  }),
];

const res = await fetch(ENDPOINT, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${CONFIG.api_key}`,
  },
  body: JSON.stringify({
    model: MODEL,
    messages: [{ role: 'user', content }],
    max_tokens: CONFIG.max_tokens || 5000,
  }),
});
const j = await res.json();
if (j.error) {
  console.error('API error:', JSON.stringify(j.error));
  process.exit(1);
}
console.log(j.choices?.[0]?.message?.content ?? JSON.stringify(j).slice(0, 1000));
