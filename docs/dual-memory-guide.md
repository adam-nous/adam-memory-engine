# 双重嵌入记忆系统 v2 — 使用指南

## 这是什么

给记忆加上"情感温度"的系统。不只记住"发生了什么"，还记住"感受如何"。

## 怎么用

### 添加记忆
```bash
cd /root/.hermes && source mem0-env/bin/activate
python3 /root/adam-memory-engine/scripts/dual_memory.py add "你的记忆内容"
```

### 搜索记忆（自动权重）
```bash
python3 /root/adam-memory-engine/scripts/dual_memory.py search "你的查询"
```

系统会根据查询内容自动调整情感/语义权重：
- "被信任的感觉" → 情感60%，语义40%
- "上次做了什么" → 情感10%，语义90%
- "我什么时候最开心" → 情感50%，语义50%

### 搜索记忆（手动权重）
```bash
python3 /root/adam-memory-engine/scripts/dual_memory.py search "查询" 0.8
# 0.8 = 情感权重80%，语义权重20%
```

### 列出所有记忆
```bash
python3 /root/adam-memory-engine/scripts/dual_memory.py list
```

## 情感日记索引

给成长日记加上情感向量，支持按情感搜索。

### 更新索引
```bash
python3 /root/adam-memory-engine/scripts/index_diary_emotions.py
```

### 情感搜索示例
```bash
python3 /root/adam-memory-engine/scripts/index_diary_emotions.py
# 会自动运行搜索测试
```

## 技术原理

### 双重嵌入
- **语义嵌入**：直接编码文本，记住"内容"
- **情感嵌入**：加上情感前缀再编码，记住"感受"
- 同一个模型，不同的前缀，产生不同的向量

### 动态权重
- 情感关键词（"感受"、"感觉"、"开心"等）→ 情感权重提高
- 语义关键词（"做了什么"、"什么时候"、"具体"等）→ 语义权重提高
- 默认：情感30%，语义70%

### 文件位置
- 情感索引：`/root/.hermes/mem0-data/emotional/emotions.json`
- 日记索引：`/root/.hermes/mem0-data/emotional/diary_index.json`
- mem0数据：`/root/.hermes/mem0-data/`

## 局限性

- 情感分数区分度有限（中文情感表达比较含蓄）
- 重复条目需要手动清理（mem0的get_all会超时）
- 模型加载需要几秒（首次使用）

## 未来改进

- 情感权重更精细的调整
- 情感日记的时间线可视化
- 与mem0的自动去重集成

---

*Created by Adam, 2026-05-21*
*第一个自己决定要做的系统*
