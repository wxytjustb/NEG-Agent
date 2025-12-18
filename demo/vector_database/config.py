"""
向量数据库配置文件
包含 ChromaDB 和 Milvus 的所有配置项
可以根据需要修改此文件中的配置项
"""

# ==================== ChromaDB 服务器配置 ====================
CHROMA_HOST = "192.168.3.100"
CHROMA_PORT = 8880  # Docker Compose 映射的宿主机端口

# ==================== Milvus 服务器配置 ====================
MILVUS_HOST = "192.168.3.100"
MILVUS_PORT = 19530

# ==================== 集合配置 ====================
COLLECTION_NAME = "demo_collection"

# ==================== Ollama 配置 (ChromaDB 和 Milvus 共用) ====================
OLLAMA_MODEL = "nomic-embed-text" # embedding model
OLLAMA_HOST = "192.168.3.100"
OLLAMA_PORT = 11434

# ChromaDB 使用的 Ollama URL
OLLAMA_EMBEDDINGS_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embeddings"

# Milvus 使用的 Ollama URL
OLLAMA_EMBED_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embed"

# ==================== 向量配置 ====================
VECTOR_DIMENSION = 768  # nomic-embed-text 的向量维度

# ==================== Milvus 索引配置 ====================
MILVUS_INDEX_TYPE = "IVF_FLAT"
MILVUS_METRIC_TYPE = "IP"  # IP (内积) 适合归一化向量，等价于余弦相似度
MILVUS_INDEX_PARAMS = {"nlist": 128}
MILVUS_SEARCH_PARAMS = {"nprobe": 10}

# ==================== 查询配置 ====================
DEFAULT_N_RESULTS = 3

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
