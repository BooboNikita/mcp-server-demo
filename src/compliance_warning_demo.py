import os
import sys

# 自动将当前目录加入 sys.path，防止在 Cherry Studio 中出现导入错误
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from compliance_warning.server import ensure_seeded, mcp


if __name__ == "__main__":
    ensure_seeded()
    mcp.run(transport="stdio")

