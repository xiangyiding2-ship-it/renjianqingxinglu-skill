# 人间清醒录 V1.0 生产管线详细规范

## 1. 文案阶段
- 账号定位：治愈 + 认知提升 + 反焦虑 + 人生观察
- 表达：安静、克制、真实、深夜聊天感
- 结构：现象→共鸣→反常识→心理机制→深入解释→重新理解→克制结尾
- 长度：60-120 秒旁白（约 300-550 字）
- 禁止：鸡汤、说教、成功学、伪造研究/数据/名言
- 人工闸门：文案展示后必须停，等用户"确认"

## 2. TTS 阶段
- 接口：`POST https://openspeech.bytedance.com/api/v1/tts`
- 鉴权：`Authorization: Bearer;{TOKEN}`
- 音色：`zh_female_wanwanxiaohe_moon_bigtts`
- 语速：1.0
- `request.with_timestamp = true`（必须）
- 返回：`data`（base64 mp3）+ `addition.frontend.words[]`

### words 结构
```json
{"word": "你", "start_time": 95, "end_time": 265, "confidence": 0.8}
```
- 标点附在前一个字上（"觉。"）
- start_time 单位毫秒，全部可信
- **最后一个 word 的 end_time 已知异常**（约为音频时长 2 倍），禁止使用

## 3. 字幕时间算法
- 按用户确认的句子顺序消费 words
- `startMs[i]` = 第 i 句第一个 word.start_time
- `endMs[i]`（非末句）= startMs[i+1] - 80ms
- `endMs[-1]` = ffprobe 实际音频 duration
- 文字 = 用户确认原文，不改写
- 禁止：逐字/逐词/KTV/打字机

## 4. 字幕视觉
- 字体：ZCOOLXiaoWei
- 颜色：#E8DDC9
- 安全区：画面 38%-47% 高度
- 长句最多两行，按语义自然断行
- 整句淡入→保持→淡出

## 5. Remotion 模板
- 项目：`radio-template/`
- 1080×1920 9:16
- 背景 #080604，UI 金 #C9A45C
- 右上：头像 + 人间清醒录 + HUMAN CLEAR RECORD
- 上方：本期关键词 + 大金字
- 中部：动态字幕
- 下部：细竖条金色声浪（音频实时驱动）

## 6. QC 清单
### 字幕 QC
- startMs 递增、endMs>startMs
- 无重叠、无倒序、无负时长
- 不超过音频长度
- words 拼接文本 == 原文（无丢字/加字）
### 音频 QC
- mp3 可播放、ffprobe duration 正常
- addition.duration 与 ffprobe 差异 < 200ms
### 渲染后 QC
- 1080×1920
- 视频/音频时长差 < 200ms
- 字幕不溢出、不裁切、不重叠

## 7. 错误处理
- 任何 QC 失败 → 立即停止，报告具体哪句/哪个 word
- 不猜时间、不强行渲染
