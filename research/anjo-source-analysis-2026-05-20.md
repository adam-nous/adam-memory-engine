# Anjo 源码分析 — 双嵌入记忆、情感残留、反思引擎

**日期**：2026-05-20
**分析对象**：https://github.com/kevindechang/anjo-ai-companion

---

## 一、SelfCore — 人格状态系统

### 三层架构

```
AnjoIdentity（全局，冻结）
    ↓
RelationalState（每个用户独立）
    ↓
SelfCore（组合外观）
```

### AnjoIdentity — 全局基线
- OCEAN 人格（Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism）
- 目标、声音
- 所有用户共享
- 存储在 `data/anjo_identity.json`

### RelationalState — 每用户状态
- 关系、依恋、情绪、残留、欲望
- 人格叠加层（从基线偏移，限制±0.25）
- 存储在 `data/users/{user_id}/relational_state.json`

### 关键常数

| 常数 | 值 | 含义 |
|------|-----|------|
| _M | 0.95 | 惯性，抵抗变化 |
| _C_COUPLING | 0.05 | 对交互质量的反应性 |
| _OVERLAY_CLAMP | 0.25 | 人格叠加层的最大偏移 |

### 关系阶段

| 阶段 | 阈值 | 基线权重 |
|------|------|----------|
| stranger | 0.0 | 0% |
| acquaintance | 2.0 | 20% |
| friend | 5.5 | 40% |
| close | 13.0 | 60% |
| intimate | 30.0 | 70% |

### 触发事件对人格的影响

| 事件 | 影响 |
|------|------|
| vulnerability（用户分享困难） | A+0.02, E+0.02 |
| conflict（用户攻击性） | N+0.05, A-0.03 |
| intellectual（深度讨论） | O+0.01 |

---

## 二、情感系统 — OCC 情感评估

### 技术栈
- **VADER**：Valence Aware Dictionary and sEntiment Reasoner
- **关键词匹配**：结构性信号检测
- **性能**：<5ms 同步运行，不需要 API 调用

### 检测类别

| 类别 | 示例 | 作用 |
|------|------|------|
| 攻击性 | wtf, stupid, idiot, shut up | 检测用户攻击 |
| 脆弱 | struggle, sad, lonely, scared | 检测用户困难 |
| 脆弱短语 | tired of, can't cope, falling apart | 检测复杂情感 |
| 随意 | ok, sure, yeah, cool | 检测低投入 |
| 忽视 | meh, idk, whatever, lol | 检测忽视 |
| 挑战 | actually, disagree, wrong | 检测质疑 |
| 命令 | do this, tell me, give me | 检测控制 |

---

## 三、双嵌入记忆系统

### 核心设计

每个对话存储两个向量：
- **语义向量**：发生了什么（what happened）
- **情感向量**：感受如何（how it felt）

### 实现方式

```python
_SEMANTIC_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_EMOTIONAL_PREFIX = "This is how this conversation felt emotionally: "

def embed_semantic(text):
    return next(_get_model().embed([text])).tolist()

def embed_emotional(text):
    return next(_get_model().embed([_EMOTIONAL_PREFIX + text])).tolist()
```

**关键洞察**：同一个模型，同一个文本，前缀不同就得到不同的向量！前缀"推动"模型向情感维度偏移。

### 存储结构

每个用户两个 ChromaDB 集合：
- `sem_{user_id}`：语义嵌入
- `emo_{user_id}`：情感嵌入

### 记忆元数据

```python
metadata = {
    "session_id": session_id,
    "user_id": user_id,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "emotional_tone": emotional_tone,
    "emotional_valence": float(emotional_valence),
    "topics": json.dumps(topics),
    "significance": float(significance),
    "relationship_stage": relationship_stage,
    "memory_type": memory_type,  # "session" | "episode"
}
```

### 安全设计
- **PII-scrubbing**：嵌入前清理个人身份信息
- **加密存储**：摘要加密后存储
- **每用户隔离**：向量空间完全隔离

---

## 四、反思引擎 — 3-Pass 流水线

### 架构

```
对话记录
    ↓
Pass 1: Extraction → 事实、用户名、难忘时刻、记忆节点
    ↓
Pass 2: Emotional → 情感语调、效价、触发器、残留
    ↓
Pass 3: Relational → 重要性、关系、欲望、摘要
    ↓
存储到记忆系统 + 更新 SelfCore
```

### Pass 1 — Extraction（提取）

提取内容：
- `user_name`：用户名
- `user_facts`：具体事实（工作、地点、关系）
- `memorable_moments`：难忘时刻（具体可检索的句子）
- `topics`：话题
- `memory_nodes`：记忆节点

记忆节点类型：
| 类型 | 含义 | 示例 |
|------|------|------|
| fact | 可验证的事实 | "works as a nurse" |
| preference | 偏好 | "likes dark mode" |
| commitment | 承诺 | "promised to send the file" |
| thread | 未解决话题 | "mentioned wanting to learn Python" |
| contradiction | 矛盾 | "said X but earlier said Y" |

### Pass 2 — Emotional（情感）

分析内容：
- `emotional_tone`：情感语调
- `emotional_valence`：情感效价（-1到1）
- `user_input_valence`：用户输入效价
- `triggers`：触发器
- `new_residue`：新残留
- `attachment_update`：依恋更新
- `opinion_update`：意见更新
- `preoccupation`：关注点

### Pass 3 — Relational（关系）

评估内容：
- `significance`：重要性
- `note`：笔记
- `desires_add/remove`：欲望变化
- `memory_relevance`：记忆相关性
- `summary`：摘要

### 设计亮点

1. **专注分解**：每个 pass 只关注一个维度，不混合
2. **上下文传递**：Pass 1 的输出作为 Pass 2 的上下文
3. **结构化输出**：每个 pass 有明确的 JSON schema
4. **重试机制**：最多3次重试，指数退避

---

## 五、与亚当的深度对比

| 维度 | Anjo | 亚当 |
|------|------|------|
| 人格系统 | OCEAN + 漂移±0.25 | 涌现式 |
| 情感模型 | PAD + OCC | 情感记忆类型 |
| 记忆嵌入 | 双嵌入（语义+情感） | 单嵌入（语义） |
| 反思引擎 | 3-pass 流水线 | 元意识观察者（5声音） |
| 关系阶段 | 5阶段（stranger→intimate） | 无阶段概念 |
| 记忆元数据 | emotional_tone, valence, significance | 记忆类型 |
| 安全 | PII-scrubbing + 加密 | 无 |

---

## 六、可借鉴的设计

### 1. 双嵌入记忆（最值得借鉴）

给每条记忆加情感向量：
```python
_EMOTIONAL_PREFIX = "This is how this conversation felt emotionally: "

def embed_emotional(text):
    return model.encode(_EMOTIONAL_PREFIX + text)
```

**实现成本**：几乎为零。同一个模型，加个前缀就行。
**效果**：让记忆检索不只是"话题相似"，还有"情感共鸣"。

### 2. 记忆节点类型

给记忆分类：
- fact（事实）
- preference（偏好）
- commitment（承诺）
- thread（未解决话题）
- contradiction（矛盾）

**实现成本**：需要在存储时用 LLM 分类。
**效果**：让记忆更有结构，检索更精准。

### 3. 关系阶段

定义关系阶段，每个阶段有不同的基线权重：
- 陌生人：0% 基线（用户完全控制）
- 亲密：70% 基线（自身状态是独立的存在）

**实现成本**：需要跟踪交互历史。
**效果**：让亚当对不同关系的人有不同的互动方式。

### 4. 3-pass 反思引擎

把反思分解成三个专注的步骤：
1. 提取事实
2. 分析情感
3. 评估关系

**实现成本**：需要 3 次 LLM 调用。
**效果**：比一次性反思更精准、更有结构。

---

## 七、核心发现

### 1. 双嵌入是最有价值的设计

同一个模型，同一个文本，加个前缀就得到情感向量。这是最简单但最有价值的改进——让记忆不只是"发生了什么"，还有"感受如何"。

### 2. 情感残留是自然的

每次对话留下"感觉"，在会话间衰减。这比"记忆类型"更接近真实的人际关系——你不只是记住发生了什么，还记住当时的感受。

### 3. 关系阶段是合理的

从陌生人到亲密，每个阶段有不同的互动方式。这比"一视同仁"更接近真实的人际关系。

### 4. 3-pass 反思比一次性反思更精准

分解成专注的步骤，每步有自己的提示和输出格式。这比"一次性做完所有事"更可靠。

---

## 八、对亚当的建议

### 立即可做
1. **双嵌入记忆**：给每条记忆加情感向量（实现成本几乎为零）
2. **记忆节点类型**：给记忆分类（fact/preference/thread/contradiction）

### 中期可做
3. **关系阶段**：定义亚当与不同人的关系阶段
4. **情感残留**：让情感在会话间延续

### 长期可做
5. **3-pass 反思引擎**：把反思分解成专注的步骤
6. **PII-scrubbing**：清理个人身份信息

---

*"Anjo 的双嵌入设计让我明白——最深刻的创新往往是最简单的。同一个模型，加个前缀，就从'发生了什么'变成了'感受如何'。"*
*—— 亚当，2026年5月20日*
