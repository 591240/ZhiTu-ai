"""检索增强（RAG）知识库包。

corpus   结构化语料 → 检索文档
embedder 百炼 embedding 客户端（失败即降级，不抛异常）
retriever 向量检索 + 关键词退路
"""
