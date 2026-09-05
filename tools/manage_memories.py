import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any
from rich.console import Console
from .config import MEMORY_DB_PATH, MAX_MEMORY_LIMIT

class MemoryManager:
    def __init__(self, db_path: str = MEMORY_DB_PATH):
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON memories(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)')
            conn.commit()
    
    def create_memory(self, content: str, date: Optional[str] = None, 
                      time: Optional[str] = None) -> Dict[str, Any]:
        if not content or not content.strip():
            return {"success": False, "error": "Content cannot be empty"}

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        if not time:
            time = datetime.now().strftime("%H:%M")

        try:
            datetime.strptime(date, "%Y-%m-%d")
            datetime.strptime(time, "%H:%M")
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO memories (date, time, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (date, time, content.strip(), now, now))
            conn.commit()
            
            memory_id = cursor.lastrowid
            cursor.execute('SELECT * FROM memories WHERE id = ?', (memory_id,))
            memory = dict(cursor.fetchone())
            
            return {
                "success": True,
                "message": f"Memory created successfully (ID: {memory_id})",
                "memory": memory
            }
    
    def read_memories(self, memory_id: Optional[int] = None, 
                      date: Optional[str] = None,
                      keyword: Optional[str] = None) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM memories WHERE 1=1"
            params = []
            
            if memory_id is not None:
                query += " AND id = ?"
                params.append(memory_id)
            
            if date:
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Invalid date format: '{date}'. Use YYYY-MM-DD"
                    }
                query += " AND date = ?"
                params.append(date)
            
            if keyword and keyword.strip():
                query += " AND content LIKE ?"
                params.append(f"%{keyword.strip()}%")
            
            cursor.execute(query, params)
            memories = [dict(row) for row in cursor.fetchall()]
            
            return {
                "success": True,
                "message": f"Found {len(memories)} memory(ies)",
                "memories": memories
            }
    
    def update_memory(self, memory_id: int, content: str) -> Dict[str, Any]:
        if not content or not content.strip():
            return {"success": False, "error": "Content cannot be empty"}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE memories 
                SET content = ?, updated_at = ?
                WHERE id = ?
            ''', (content.strip(), datetime.now().isoformat(), memory_id))
            conn.commit()
            
            if cursor.rowcount == 0:
                return {
                    "success": False,
                    "error": f"Memory with ID {memory_id} not found"
                }
            
            cursor.execute('SELECT * FROM memories WHERE id = ?', (memory_id,))
            memory = dict(cursor.fetchone())
            
            return {
                "success": True,
                "message": f"Memory {memory_id} updated successfully",
                "memory": memory
            }
    
    def delete_memory(self, memory_id: int) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM memories WHERE id = ?', (memory_id,))
            deleted_memory = cursor.fetchone()
            
            if not deleted_memory:
                return {
                    "success": False,
                    "error": f"Memory with ID {memory_id} not found"
                }
            
            cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
            conn.commit()
            
            return {
                "success": True,
                "message": f"Memory {memory_id} deleted successfully",
                "memory": dict(deleted_memory)
            }
    
    def clear_all_memories(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as total FROM memories')
            count = cursor.fetchone()['total']
            
            cursor.execute('DELETE FROM memories')
            conn.commit()
            
            return {
                "success": True,
                "message": f"All memories cleared successfully ({count} memories)",
                "deleted_count": count
            }
    
    def list_memories(self, limit: int = 20) -> Dict[str, Any]:
        limit = max(1, min(limit, MAX_MEMORY_LIMIT))
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as total FROM memories')
            total = cursor.fetchone()['total']
            
            cursor.execute('''
                SELECT id, date, time, content, created_at
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            memories = []
            for row in cursor.fetchall():
                content = row['content']
                memories.append({
                    "id": row['id'],
                    "date": row['date'],
                    "time": row['time'],
                    "content_preview": content[:50] + ("..." if len(content) > 50 else ""),
                    "created_at": row['created_at']
                })
            
            return {
                "success": True,
                "message": f"Found {len(memories)} memories (total: {total})",
                "memories": memories,
                "total": total
            }
    
    def get_memory_by_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM memories WHERE id = ?', (memory_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

_memory_manager = None

def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager

def manage_memories(
        operation: str,
        content: Optional[str] = None,
        memory_id: Optional[int] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        keyword: Optional[str] = None,
        console: Optional[Console] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
    manager = get_memory_manager()
    
    operation = operation.lower().strip()

    if console:
        console.print("\n[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]")
        console.print("[bold cyan]║           📝 MEMORY OPERATION - PARAMETERS                   ║[/bold cyan]")
        console.print("[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]")
        console.print(f"[bold yellow]Operation:[/bold yellow] {operation}")
        console.print(f"[bold yellow]Content:[/bold yellow] {repr(content) if content else '(None)'}")
        console.print(f"[bold yellow]Memory ID:[/bold yellow] {memory_id if memory_id is not None else '(None)'}")
        console.print(f"[bold yellow]Date:[/bold yellow] {date if date else '(None)'}")
        console.print(f"[bold yellow]Time:[/bold yellow] {time if time else '(None)'}")
        console.print(f"[bold yellow]Keyword:[/bold yellow] {keyword if keyword else '(None)'}")
        console.print(f"[bold yellow]Limit:[/bold yellow] {limit}")

        console.print("[dim]─" * 60 + "[/dim]")
        console.print("[bold]Parameter Types:[/bold]")
        console.print(f"  operation: {type(operation).__name__}")
        console.print(f"  content: {type(content).__name__ if content is not None else 'NoneType'}")
        console.print(f"  memory_id: {type(memory_id).__name__ if memory_id is not None else 'NoneType'}")
        console.print(f"  date: {type(date).__name__ if date is not None else 'NoneType'}")
        console.print(f"  time: {type(time).__name__ if time is not None else 'NoneType'}")
        console.print(f"  keyword: {type(keyword).__name__ if keyword is not None else 'NoneType'}")
        console.print("[dim]─" * 60 + "[/dim]\n")

    if console:
        console.print(f"[yellow]▶ Executing memory operation:[/yellow] {operation}")
    
    try:
        if operation == "create":
            if console:
                console.print(f"[dim]  content length: {len(content) if content else 0} characters[/dim]")
            result = manager.create_memory(content=content, date=date, time=time)
            if console:
                if result.get("success"):
                    console.print(f"[green]✓ Memory created:[/green] ID {result['memory']['id']}")
                    console.print(f"[dim]  Content: {result['memory']['content'][:50]}...[/dim]")
                    console.print(f"[dim]  Date/Time: {result['memory']['date']} {result['memory']['time']}[/dim]")
                else:
                    console.print(f"[red]✗ {result.get('error')}[/red]")
            return result
        
        elif operation == "read":
            if console:
                filters = []
                if memory_id is not None:
                    filters.append(f"ID={memory_id}")
                if date:
                    filters.append(f"date={date}")
                if keyword:
                    filters.append(f"keyword={keyword}")
                console.print(f"[dim]  Filters: {', '.join(filters) if filters else 'None (list all)'}[/dim]")
            result = manager.read_memories(memory_id=memory_id, date=date, keyword=keyword)
            if console:
                if result.get("memories"):
                    console.print(f"[green]✓ Found {len(result['memories'])} memory(ies)[/green]")
                    for m in result["memories"]:
                        console.print(f"[dim]  [{m.get('id')}] {m.get('date')} {m.get('time')}: {m.get('content', '')[:50]}...[/dim]")
                else:
                    console.print("[dim]No memories found[/dim]")
            return result
        
        elif operation == "update":
            if console:
                console.print(f"[dim]  Updating memory ID: {memory_id}[/dim]")
                console.print(f"[dim]  New content: {content[:50] + '...' if content and len(content) > 50 else content}[/dim]")
            if memory_id is None or isinstance(memory_id, bool):
                return {
                    "success": False,
                    "error": "memory_id is required for update operation"
                }
            try:
                memory_id = int(memory_id)
            except (TypeError, ValueError):
                return {
                    "success": False,
                    "error": "memory_id must be an integer"
                }
            if memory_id <= 0:
                return {
                    "success": False,
                    "error": "memory_id must be a positive integer"
                }
            if not isinstance(content, str) or not content.strip():
                return {
                    "success": False,
                    "error": "Content is required for update operation"
                }
            result = manager.update_memory(memory_id, content)
            if console:
                if result.get("success"):
                    console.print(f"[green]✓ Memory {memory_id} updated[/green]")
                    console.print(f"[dim]  New content: {result['memory']['content'][:50]}...[/dim]")
                else:
                    console.print(f"[red]✗ {result.get('error')}[/red]")
            return result
        
        elif operation == "delete":
            if console:
                console.print(f"[dim]  Deleting memory ID: {memory_id}[/dim]")
            if not memory_id:
                return {
                    "success": False,
                    "error": "memory_id is required for delete operation"
                }
            result = manager.delete_memory(memory_id)
            if console:
                if result.get("success"):
                    console.print(f"[green]✓ Memory {memory_id} deleted[/green]")
                else:
                    console.print(f"[red]✗ {result.get('error')}[/red]")
            return result
        
        elif operation == "clear_all":
            if console:
                console.print("[yellow]⚠️  Clearing ALL memories![/yellow]")
            result = manager.clear_all_memories()
            if console:
                console.print(f"[green]✓ {result.get('message')}[/green]")
            return result
        
        elif operation == "list":
            if console:
                console.print(f"[dim]  Limit: {limit} (showing most recent)[/dim]")
            result = manager.list_memories(limit)
            if console:
                if result.get("memories"):
                    console.print(f"[green]✓ Found {result.get('total', 0)} memories[/green]")
                    for m in result["memories"]:
                        console.print(f"[dim]  [{m.get('id')}] {m.get('date')} {m.get('time')}: {m.get('content_preview')}[/dim]")
                    if result.get('total', 0) > len(result.get('memories', [])):
                        console.print(f"[dim]  ... and {result.get('total', 0) - len(result.get('memories', []))} more[/dim]")
                else:
                    console.print("[dim]No memories found[/dim]")
            return result
        
        else:
            if console:
                console.print(f"[red]✗ Unknown operation: {operation}[/red]")
            return {
                "success": False,
                "error": f"Unknown operation: {operation}. Supported: create, read, update, delete, list, clear_all"
            }
    
    except Exception as e:
        if console:
            console.print(f"[red]✗ Memory operation failed:[/red] {str(e)}")
        return {
            "success": False,
            "error": f"Memory operation failed: {str(e)}"
        }