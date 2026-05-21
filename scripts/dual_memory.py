#!/usr/bin/env python3
"""
Dual-Embedding Memory Engine v2 for Adam
双嵌入记忆引擎 — 语义 + 情感 + 动态权重

基于 Anjo 的设计理念：
- 语义嵌入：记住"发生了什么"
- 情感嵌入：记住"感受如何"
- 动态权重：根据查询自动调整
"""

import os
import sys
import json
import hashlib

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ.setdefault("OPENAI_API_KEY", "not-needed-for-infer-false")

MEM0_ENV = "/root/.hermes/mem0-env"
MEM0_DATA = "/root/.hermes/mem0-data"
EMOTIONAL_DATA = "/root/.hermes/mem0-data/emotional"

sys.path.insert(0, os.path.join(MEM0_ENV, "lib/python3.12/site-packages"))

import numpy as np
from mem0 import Memory
from sentence_transformers import SentenceTransformer

_EMOTIONAL_PREFIX = "This is how this felt emotionally: "
_model = None

# 情感关键词
EMOTIONAL_KEYWORDS = [
    "感受", "感觉", "心情", "情绪", "开心", "难过", "焦虑", "满足", 
    "温暖", "孤独", "害怕", "兴奋", "感动", "失落", "踏实", "紧张",
    "喜欢", "讨厌", "享受", "痛苦", "幸福", "沮丧", "自豪", "羞耻",
    "信任", "怀疑", "期待", "失望", "惊喜", "平静", "烦躁", "安心",
    "快乐", "悲伤", "愤怒", "恐惧", "惊讶", "厌恶", "期待",
    "怎么样", "什么感觉", "心情如何", "情绪状态"
]

# 语义关键词
SEMANTIC_KEYWORDS = [
    "做了什么", "发生什么", "什么时候", "在哪里", "谁", "为什么",
    "怎么", "如何", "多少", "几个", "第几次", "具体", "详细",
    "记录", "笔记", "日志", "历史", "之前", "上次", "那次",
    "事实", "数据", "结果", "过程", "步骤", "方法"
]

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model

def embed_semantic(text):
    return _get_model().encode(text).tolist()

def embed_emotional(text):
    return _get_model().encode(_EMOTIONAL_PREFIX + text).tolist()

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def calculate_weights(query):
    """根据查询内容动态计算情感权重"""
    query_lower = query.lower()
    
    emotional_hits = sum(1 for kw in EMOTIONAL_KEYWORDS if kw in query_lower)
    semantic_hits = sum(1 for kw in SEMANTIC_KEYWORDS if kw in query_lower)
    
    base_emotional = 0.3
    
    if emotional_hits > 0 and semantic_hits == 0:
        emotional_weight = min(0.8, base_emotional + emotional_hits * 0.15)
    elif semantic_hits > 0 and emotional_hits == 0:
        emotional_weight = max(0.1, base_emotional - semantic_hits * 0.1)
    elif emotional_hits > 0 and semantic_hits > 0:
        total = emotional_hits + semantic_hits
        emotional_weight = 0.3 + (emotional_hits / total) * 0.4
    else:
        emotional_weight = base_emotional
    
    return round(emotional_weight, 2), round(1.0 - emotional_weight, 2)

def get_mem0_client():
    config = {
        "embedder": {"provider": "huggingface", "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"}},
        "vector_store": {"provider": "faiss", "config": {"path": MEM0_DATA, "embedding_model_dims": 384}},
    }
    return Memory.from_config(config)

class EmotionalIndex:
    def __init__(self, path=EMOTIONAL_DATA):
        self.path = path
        self.data_path = os.path.join(path, "emotions.json")
        self._load()

    def _load(self):
        os.makedirs(self.path, exist_ok=True)
        if os.path.exists(self.data_path):
            with open(self.data_path, "r") as f:
                self.entries = json.load(f)
        else:
            self.entries = []

    def _save(self):
        with open(self.data_path, "w") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    def add(self, memory_id, text):
        vec = embed_emotional(text)
        self.entries.append({"id": memory_id, "text": text, "vector": vec})
        self._save()

    def search(self, query, top_k=5):
        if not self.entries:
            return []
        query_vec = embed_emotional(query)
        scored = []
        for e in self.entries:
            score = cosine_similarity(query_vec, e["vector"])
            scored.append({"id": e["id"], "text": e["text"], "emotional_score": score})
        scored.sort(key=lambda x: x["emotional_score"], reverse=True)
        return scored[:top_k]

def cmd_add(text, user_id="xiaolin"):
    m = get_mem0_client()
    result = m.add(text, user_id=user_id, infer=False)
    if isinstance(result, dict) and "results" in result:
        results_list = result["results"]
        memory_id = results_list[0]["id"] if results_list else hashlib.md5(text.encode()).hexdigest()[:12]
    elif isinstance(result, list) and result:
        memory_id = result[0].get("id", hashlib.md5(text.encode()).hexdigest()[:12])
    else:
        memory_id = hashlib.md5(text.encode()).hexdigest()[:12]
    emo_index = EmotionalIndex()
    emo_index.add(memory_id, text)
    print(f"OK | id={memory_id} | text={text[:50]}")

def cmd_search(query, user_id="xiaolin", top_k=5, emotional_weight=None):
    m = get_mem0_client()
    emo_index = EmotionalIndex()
    
    # 自动计算权重（如果未指定）
    if emotional_weight is None:
        emotional_weight, semantic_weight = calculate_weights(query)
    else:
        semantic_weight = 1 - emotional_weight
    
    semantic_results = m.search(query, filters={"user_id": user_id}, top_k=top_k)
    semantic_items = semantic_results.get("results", [])
    emotional_items = emo_index.search(query, top_k=top_k)
    
    combined = {}
    for item in semantic_items:
        mid = item.get("id", "")
        combined[mid] = {"id": mid, "text": item.get("memory", ""), "semantic_score": item.get("score", 0), "emotional_score": 0}
    for item in emotional_items:
        emo_text = item["text"]
        matched = False
        for mid, existing in combined.items():
            if existing["text"] == emo_text:
                existing["emotional_score"] = item["emotional_score"]
                matched = True
                break
        if not matched:
            combined[emo_text] = {"id": item.get("id", ""), "text": emo_text, "semantic_score": 0, "emotional_score": item["emotional_score"]}
    
    for item in combined.values():
        item["combined_score"] = item["semantic_score"] * semantic_weight + item["emotional_score"] * emotional_weight
    
    results = sorted(combined.values(), key=lambda x: x["combined_score"], reverse=True)
    
    print(f"Search: \"{query}\"")
    print(f"权重: 情感{emotional_weight:.0%} 语义{semantic_weight:.0%}")
    for item in results[:top_k]:
        print(f"  [{item['combined_score']:.3f}] {item['text'][:60]}")
        print(f"    sem={item['semantic_score']:.3f} emo={item['emotional_score']:.3f}")

def cmd_list(user_id="xiaolin"):
    m = get_mem0_client()
    results = m.get_all(filters={"user_id": user_id})
    memories = results.get("results", [])
    emo_index = EmotionalIndex()
    emo_ids = {e["id"] for e in emo_index.entries}
    print(f"Total: {len(memories)} memories, {len(emo_ids)} with emotional vectors")
    for item in memories:
        mid = item.get("id", "")
        flag = "E" if mid in emo_ids else "S"
        print(f"  [{flag}] {item.get('memory', '')[:60]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dual_memory.py <add|search|list> [args]")
        print("  add <text> - 添加记忆（自动双嵌入）")
        print("  search <query> - 搜索（自动权重调整）")
        print("  search <query> <emotional_weight> - 搜索（手动指定权重）")
        print("  list - 列出所有记忆")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) >= 3:
        cmd_add(" ".join(sys.argv[2:]))
    elif cmd == "search" and len(sys.argv) >= 3:
        if len(sys.argv) >= 4:
            cmd_search(sys.argv[2], emotional_weight=float(sys.argv[3]))
        else:
            cmd_search(sys.argv[2])
    elif cmd == "list":
        cmd_list()
    else:
        print(f"Unknown: {cmd}")
        sys.exit(1)
