"""Test database connection."""

import asyncio
import aiomysql


async def test_connection():
    """Test MySQL database connection."""
    print("Testing database connection...")
    
    try:
        # 尝试连接数据库
        conn = await aiomysql.connect(
            host="localhost",
            port=3306,
            db="app_platform",
            user="root",
            password="123456"
        )
        print("✓ 数据库连接成功！")
        
        # 测试查询
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # 查询数据库版本
            await cursor.execute("SELECT VERSION()")
            version = await cursor.fetchone()
            print(f"✓ MySQL 版本: {version}")
            
            # 查询 app_module 表
            await cursor.execute("SELECT * FROM app_module LIMIT 5")
            modules = await cursor.fetchall()
            print(f"✓ app_module 表记录数: {len(modules)}")
            if modules:
                print(f"  示例数据: {modules[0]}")
        
        conn.close()
        print("\n✓ 所有测试通过！")
        return True
        
    except Exception as e:
        print(f"✗ 连接失败: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    exit(0 if result else 1)
