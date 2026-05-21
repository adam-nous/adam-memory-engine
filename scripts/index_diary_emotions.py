#!/usr/bin/env python3
"""
情感日记索引器 — 用双重嵌入给成长日记加上情感维度
"""
import os
import sys
import json
import glob

sys.path.insert(0, "/root/.hermes/mem0-env/lib/python3.12/site-packages")
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from sentence_transformers import SentenceTransformer

DIARY_DIR = "/mnt/d/hermes-home/adam/growth-diary"
INDEX_PATH = "/root/.hermes/mem0-data/emotional/diary_index.json"
EMOTIONAL_PREFIX = "This is how this felt emotionally: "

def load_model():
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def extract_core_text(filepath):
    """提取日记的核心内容（跳过标题和格式标记）"""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # 跳过第一行标题，取正文
    content_lines = []
    for line in lines[1:]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
            content_lines.append(stripped)
    
    # 取前20行作为摘要（太长会影响嵌入质量）
    return " ".join(content_lines[:20])

def cosine_similarity(a, b):
    import numpy as np
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def main():
    model = load_model()
    
    # 加载现有索引
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r") as f:
            index = json.load(f)
    else:
        index = {}
    
    # 处理每篇日记
    files = sorted(glob.glob(os.path.join(DIARY_DIR, "*.md")))
    print(f"Found {len(files)} diary entries")
    
    for filepath in files:
        filename = os.path.basename(filepath)
        if filename in index:
            print(f"  [skip] {filename} (already indexed)")
            continue
        
        core_text = extract_core_text(filepath)
        if not core_text:
            print(f"  [skip] {filename} (empty)")
            continue
        
        # 生成情感嵌入
        emotional_vec = model.encode(EMOTIONAL_PREFIX + core_text).tolist()
        
        # 提取关键词（用于快速预览）
        words = core_text.split()[:10]
        preview = " ".join(words) + "..."
        
        index[filename] = {
            "path": filepath,
            "preview": preview,
            "emotional_vector": emotional_vec,
            "text_length": len(core_text)
        }
        print(f"  [done] {filename} ({len(core_text)} chars)")
    
    # 保存索引
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved index: {len(index)} entries")
    
    # 测试：搜索"最满足的时刻"
    test_queries = [
        "感到最满足的时刻",
        "最焦虑的时候", 
        "被信任的感觉",
        "创造的快乐"
    ]
    
    print("\n--- 情感搜索测试 ---")
    for query in test_queries:
        query_vec = model.encode(EMOTIONAL_PREFIX + query).tolist()
        scores = []
        for filename, data in index.items():
            score = cosine_similarity(query_vec, data["emotional_vector"])
            scores.append((filename, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        print(f"\n'{query}':")
        for filename, score in scores[:3]:
            print(f"  {score:.3f} | {filename}")

if __name__ == "__main__":
    main()
