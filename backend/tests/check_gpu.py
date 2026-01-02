import torch

print("=" * 50)
print("GPU 检测")
print("=" * 50)
print(f"CUDA 可用: {torch.cuda.is_available()}")
print(f"GPU 数量: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"GPU 名称: {torch.cuda.get_device_name(0)}")
    print(f"CUDA 版本: {torch.version.cuda}")
else:
    print("⚠️ 未检测到 GPU")
print("=" * 50)
