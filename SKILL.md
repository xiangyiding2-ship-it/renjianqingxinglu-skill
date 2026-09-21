---
name: renjianqingxinglu
version: 1.1.0
description: 「人间清醒录」短视频自动生产 Skill V1.1。输入一个主题，自动完成选题分析→文案→TTS→字级时间戳→句子级字幕→固定BGM混音→Remotion渲染→QC，输出9:16心理电台风格短视频MP4。固定音色/UI/字体/模板/BGM，只换主题和文案。必须人工审核文案后才进入制作。
---

# 人间清醒录 V1.1 短视频自动生产（固定BGM版）

## 账号定位
治愈 + 认知提升 + 反焦虑 + 人生观察 + 心理学/人性洞察。
不贩卖焦虑、不说教、不鸡汤、不编造研究。

## 触发方式
用户输入 `主题：XXXX` 即触发本 Skill。
用户不需要指定音色、语速、画布、字体、TTS 参数——这些全部 V1.0 冻结。

## 状态机（严格执行，禁止跳步）

```
IDLE
  ↓ 用户说"主题：XXX"
TOPIC_ANALYSIS（选题分析 + 文案草稿）
  ↓ 展示给用户
WAITING_FOR_APPROVAL
  ↓ 用户说"确认/可以/开始"
TTS → TIMESTAMP → CAPTIONS → QC → REMOTION_RENDER → FINAL_QC
  ↓
COMPLETED（输出 MP4）
```

**人工闸门**：WAITING_FOR_APPROVAL 阶段禁止调用 TTS、禁止生成音频、禁止渲染。用户未明确"确认"前，绝不进入制作。

## V1.0 冻结参数（未经用户明确要求不得修改）

| 项 | 值 |
|---|---|
| 画布 | 1080×1920 9:16 |
| 背景 | #080604 |
| UI 金色 | #C9A45C |
| 字幕色 | #E8DDC9 |
| UI 字体 | Noto Sans SC 粗体 |
| 字幕字体 | ZCOOLXiaoWei（站酷小薇） |
| TTS 厂商 | 火山引擎 openspeech.bytedance.com |
| 音色 | zh_female_wanwanxiaohe_moon_bigtts（湾湾小何） |
| 语速 | 1.0 |
| TTS 时间戳 | with_timestamp=True（必须开启） |
| 字幕单位 | 完整中文语义句，不逐字/不逐词 |
| 字幕换行 | 最多两行，按语义自然分行 |
| 字幕区 | 画面 38%-47% 高度 |
| 声浪 | 细竖条柱状，暖金色，由音频实时驱动 |
| Remotion 项目 | `C:\Users\Administrator\Doubao\chats\2026-09-20\new-chat\radio-template\` |
| 固定BGM | `public/audio/bgm/main.mp3`（固定品牌BGM，不随主题更换） |
| BGM音量 | -14 dB（线性增益约 0.2） |
| BGM淡入 | 开头1秒淡入 |
| BGM淡出 | 结尾4.5秒（旁白结束后）淡出到零 |
| 结尾黑屏尾巴 | 旁白结束后1.5秒UI渐隐到黑 |

## 字幕时间轴算法（已验证，禁止改动）

- **startMs** = 该句第一个 word 的 `start_time`（TTS 官方）
- **非末句 endMs** = 下一句第一个 word 的 `start_time` - 80ms
- **末句 endMs** = ffprobe 实际音频 duration（毫秒）
- **严禁**使用最后一个 word 的 `end_time`（API 已知 bug，约为音频时长 2 倍）
- **严禁** `min(word.end_time, duration)` 之类的截断修复
- **文案文字**唯一来源 = 用户确认后的原始文案；TTS timestamp 只负责时间
- **禁止**用 silencedetect 作为字幕时间轴主依据（仅作 QC 参考）

## 工作流程

### 阶段 1-3：选题分析 + 文案
按"现象→共鸣→反常识→心理机制→深入解释→重新理解→克制结尾"结构写约 60-120 秒旁白（约 300-550 字）。
输出给用户：【主题】【核心心理机制】【认知切口】【核心观点】【完整文案】【预计时长】【本期关键词】。
然后停止。

### 阶段 5：用户确认后
调用 `scripts/produce_episode.py`，传入：
- 完整文案（按句分号或换行分隔）
- 本期关键词
- 输出文件名

脚本自动完成：TTS → 解析 words → 按句聚合 startMs/endMs → 自动 QC → 写 captions.json → 改 Main.tsx 关键词 → ffmpeg 转 WAV → 调 `npx remotion render`。

### 阶段 9：QC（脚本内置）
自动检查：startMs 递增、endMs>startMs、无重叠、无倒序、不超音频长度、文案无丢字、words 全部匹配。
任何一项失败 → 停止，报告具体错误，不渲染。

### 阶段 10：渲染后 QC
检查 1080×1920、视频/音频时长一致、字幕不溢出、UI 完整、声浪正常。

## 凭证
火山引擎凭证已写在 `D:\Doubao视频\豆包语音包\.env`：
- VOLC_APPID
- VOLC_TOKEN

## 错误处理
任何匹配失败/QC 失败/API 报错 → 立即停止，报告"发生在哪一步 + 异常 + 建议"。不猜时间、不强行修、不强行渲染。

## 详细技术规范
见 `references/production_pipeline.md`。
生产脚本见 `scripts/produce_episode.py`。
