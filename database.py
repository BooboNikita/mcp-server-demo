"""Example showing lifespan support for startup/shutdown with strong typing."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
import aiomysql

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession


# Mock database class for example
class Database:
    """Mock database class for example."""

    def __init__(self, host: str = "localhost", port: int = 3306, 
                 database: str = "mydb", user: str = "root", password: str = ""):
        """Initialize database connection parameters."""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    @classmethod
    async def connect(cls, host: str = "localhost", port: int = 3306,
                     database: str = "app_platform", user: str = "root", password: str = "") -> "Database":
        """Connect to database with connection info."""
        db = cls(host=host, port=port, database=database, user=user, password=password)
        # 使用 aiomysql 连接 MySQL 数据库
        try:
            db.connection = await aiomysql.connect(
                host=host, port=port, db=database, user=user, password=password
            )
            print(f"Connected to {user}@{host}:{port}/{database}")
        except Exception as e:
            print(f"Connection failed: {e}")
        return db

    async def disconnect(self) -> None:
        """Disconnect from database."""
        if self.connection:
            self.connection.close()
            await self.connection.wait_closed()
        print("Disconnected from database")

    async def query_app_module(self) -> list:
        """Query app_module table."""
        print("Querying app_module table...", self.connection)
        if not self.connection:
            return []
        
        print("Executing query...")
        
        async with self.connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM app_module")
            result = await cursor.fetchall()
            print("Query executed successfully.", result)
            return result

    def query(self) -> str:
        """Execute a query."""
        return f"Query result from {self.database}@{self.host}"


@dataclass
class AppContext:
    """Application context with typed dependencies."""

    db: Database


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context."""
    # Initialize on startup with database connection info
    db = await Database.connect(
        host="localhost",
        port=3306,
        database="app_platform",
        user="root",
        password="123456"
    )
    try:
        yield AppContext(db=db)
    finally:
        # Cleanup on shutdown
        await db.disconnect()


# Pass lifespan to server
mcp = FastMCP("My App", lifespan=app_lifespan)


# Access type-safe lifespan context in tools
@mcp.tool()
def query_db(ctx: Context[ServerSession, AppContext]) -> str:
    """Tool that uses initialized resources."""
    db = ctx.request_context.lifespan_context.db
    return db.query()

@mcp.tool()
async def get_app_modules(ctx: Context[ServerSession, AppContext]) -> list:
    """Get all modules from app_module table."""
    db = ctx.request_context.lifespan_context.db
    modules = await db.query_app_module()
    return modules

if __name__ == "__main__":
    mcp.run(transport="streamable-http")