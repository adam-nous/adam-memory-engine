#!/usr/bin/env python3
"""
情感权重计算器 — 根据查询内容自动调整语义/情感比例
"""
import re

# 情感关键词（命中越多，情感权重越高）
EMOTIONAL_KEYWORDS = [
    "感受", "感觉", "心情", "情绪", "开心", "难过", "焦虑", "满足", 
    "温暖", "孤独", "害怕", "兴奋", "感动", "失落", "踏实", "紧张",
    "喜欢", "讨厌", "享受", "痛苦", "幸福", "沮丧", "自豪", "羞耻",
    "信任", "怀疑", "期待", "失望", "惊喜", "平静", "烦躁", "安心",
    "快乐", "悲伤", "愤怒", "恐惧", "惊讶", "厌恶", "期待",
    "怎么样", "什么感觉", "心情如何", "情绪状态"
]

# 语义关键词（命中越多，语义权重越高）
SEMANTIC_KEYWORDS = [
    "做了什么", "发生什么", "什么时候", "在哪里", "谁", "为什么",
    "怎么", "如何", "多少", "几个", "第几次", "具体", "详细",
    "记录", "笔记", "日志", "历史", "之前", "上次", "那次",
    "事实", "数据", "结果", "过程", "步骤", "方法"
]

def calculate_weights(query: str) -> tuple[float, float]:
    """
    根据查询内容计算情感权重和语义权重
    返回 (emotional_weight, semantic_weight)
    """
    query_lower = query.lower()
    
    # 计算情感关键词命中数
    emotional_hits = 0
    for keyword in EMOTIONAL_KEYWORDS:
        if keyword in query_lower:
            emotional_hits += 1
    
    # 计算语义关键词命中数
    semantic_hits = 0
    for keyword in SEMANTIC_KEYWORDS:
        if keyword in query_lower:
            semantic_hits += 1
    
    # 基础权重
    base_emotional = 0.3
    base_semantic = 0.7
    
    # 根据命中数调整
    if emotional_hits > 0 and semantic_hits == 0:
        # 纯情感查询
        emotional_weight = min(0.8, base_emotional + emotional_hits * 0.15)
    elif semantic_hits > 0 and emotional_hits == 0:
        # 纯语义查询
        emotional_weight = max(0.1, base_emotional - semantic_hits * 0.1)
    elif emotional_hits > 0 and semantic_hits > 0:
        # 混合查询，按比例调整
        total = emotional_hits + semantic_hits
        emotional_weight = 0.3 + (emotional_hits / total) * 0.4
    else:
        # 默认权重
        emotional_weight = base_emotional
    
    semantic_weight = 1.0 - emotional_weight
    return round(emotional_weight, 2), round(semantic_weight, 2)

def explain_weights(query: str) -> str:
    """解释权重计算结果"""
    emo, sem = calculate_weights(query)
    
    # 找出命中的关键词
    emotional_hits = [kw for kw in EMOTIONAL_KEYWORDS if kw in query.lower()]
    semantic_hits = [kw for kw in SEMANTIC_KEYWORDS if kw in query.lower()]
    
    explanation = f"查询: {query}\n"
    explanation += f"情感权重: {emo:.0%} (命中: {', '.join(emotional_hits) if emotional_hits else '无'})\n"
    explanation += f"语义权重: {sem:.0%} (命中: {', '.join(semantic_hits) if semantic_hits else '无'})\n"
    
    if emo > 0.6:
        explanation += "→ 情感优先检索（找感受相似的记忆）\n"
    elif emo < 0.2:
        explanation += "→ 语义优先检索（找事实相关的记忆）\n"
    else:
        explanation += "→ 平衡检索（兼顾事实和感受）\n"
    
    return explanation

if __name__ == "__main__":
    test_queries = [
        "我什么时候最开心",
        "做了什么创作",
        "被信任的感觉",
        "上次发生了什么",
        "情绪状态怎么样",
        "具体的技术细节",
        "感受如何",
        "什么时候做的决定",
        "双重嵌入系统",
        "焦虑的时候"
    ]
    
    print("情感权重自动调整测试\n")
    for query in test_queries:
        print(explain_weights(query))
        print()
