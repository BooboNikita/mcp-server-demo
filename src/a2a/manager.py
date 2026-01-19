import subprocess
import sys
import time
import signal
import os
from typing import List

class AgentManager:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.agents = [
            {
                "name": "TechExpert",
                "module": "src.a2a.tech_expert",
                "port": 8001
            },
            {
                "name": "SalesConsultant",
                "module": "src.a2a.sales_consultant",
                "port": 8002
            },
            {
                "name": "Receptionist",
                "module": "src.a2a.receptionist",
                "port": 8000
            }
        ]
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

    def start_all(self):
        """启动所有 Agent 服务"""
        print("🚀 正在启动 A2A Agent 系统...")
        
        for agent in self.agents:
            log_file = open(os.path.join(self.log_dir, f"{agent['name'].lower()}.log"), "w")
            
            # 使用 uv run python -m 方式启动，确保路径正确
            cmd = ["uv", "run", "python", "-m", agent["module"]]
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd()
                )
                self.processes.append({
                    "process": process,
                    "name": agent["name"],
                    "log_file": log_file
                })
                print(f"✅ {agent['name']} 已启动 (PID: {process.pid}, Port: {agent['port']})")
            except Exception as e:
                print(f"❌ {agent['name']} 启动失败: {e}")
                self.stop_all()
                return

        print("\n✨ 所有服务已启动运行！日志保存在 logs/ 目录下。")
        print("按 Ctrl+C 停止所有服务...")

    def stop_all(self):
        """停止所有 Agent 服务"""
        print("\n🛑 正在停止服务...")
        for p_info in reversed(self.processes):
            process = p_info["process"]
            name = p_info["name"]
            log_file = p_info["log_file"]
            
            if process.poll() is None:
                print(f"正在关闭 {name} (PID: {process.pid})...")
                # 发送 SIGTERM
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 如果超时，发送 SIGKILL
                    print(f"强制终止 {name}...")
                    process.kill()
            
            if not log_file.closed:
                log_file.close()

        self.processes = []
        print("✅ 所有服务已停止。")

def main():
    manager = AgentManager()
    
    # 注册信号处理，确保被杀掉时也能清理子进程
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        manager.start_all()
        # 保持主进程运行
        while True:
            time.sleep(1)
            # 检查子进程是否还活着
            for p_info in manager.processes:
                if p_info["process"].poll() is not None:
                    print(f"⚠️ 警告: {p_info['name']} 意外退出！")
                    manager.stop_all()
                    sys.exit(1)
    except KeyboardInterrupt:
        # 已经在 signal_handler 中处理，这里只需捕获避免报错
        pass
    finally:
        manager.stop_all()

if __name__ == "__main__":
    main()
