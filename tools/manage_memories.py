import json
import os
from datetime import datetime
from rich.console import Console
from typing import Optional, List, Dict, Any

class MemoryManager:
    def __init__(self):
        self.memory_dir = "memories"
        
        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir)

        self.memory_file = os.path.join(self.memory_dir, "memories.json")
        self._ensure_memory_file()
    
    def _ensure_memory_file(self):
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _load_memories(self) -> List[Dict[str, Any]]:
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_memories(self, memories: List[Dict[str, Any]]):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
    
    def create_memory(self, content: str, date: Optional[str] = None, time: Optional[str] = None) -> Dict[str, Any]:
        if not content or not content.strip():
            return {
                "success": False,
                "error": "Content cannot be empty"
            }

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        if not time:
            time = datetime.now().strftime("%H:%M")

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid date format: '{date}'. Use YYYY-MM-DD"
            }

        try:
            datetime.strptime(time, "%H:%M")
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid time format: '{time}'. Use HH:MM"
            }
        
        memories = self._load_memories()

        max_id = max([m.get("id", 0) for m in memories]) if memories else 0
        
        memory = {
            "id": max_id + 1,
            "date": date,
            "time": time,
            "content": content.strip(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        memories.append(memory)
        self._save_memories(memories)
        
        return {
            "success": True,
            "message": f"Memory created successfully (ID: {memory['id']})",
            "memory": memory
        }
    
    def read_memories(self, memory_id: Optional[int] = None, date: Optional[str] = None, 
                      keyword: Optional[str] = None) -> Dict[str, Any]:
        memories = self._load_memories()
        
        if not memories:
            return {
                "success": True,
                "message": "No memories found",
                "memories": []
            }

        if memory_id is not None:
            m = self.get_memory_by_id(memory_id)
            if m:
                return {
                    "success": True,
                    "message": f"Found memory ID {memory_id}",
                    "memories": [m]
                }
            return {
                "success": True,
                "message": f"No memory found with ID {memory_id}",
                "memories": []
            }

        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid date format: '{date}'. Use YYYY-MM-DD"
                }
            memories = [m for m in memories if m.get("date") == date]

        if keyword and keyword.strip():
            keyword_lower = keyword.strip().lower()
            memories = [m for m in memories if keyword_lower in m.get("content", "").lower()]
        
        if not memories:
            return {
                "success": True,
                "message": "No matching memories found",
                "memories": []
            }
        
        return {
            "success": True,
            "message": f"Found {len(memories)} memory(ies)",
            "memories": memories
        }
    
    def update_memory(self, memory_id: int, content: str) -> Dict[str, Any]:
        if not content or not content.strip():
            return {
                "success": False,
                "error": "Content cannot be empty"
            }
        
        memories = self._load_memories()
        
        for memory in memories:
            if memory.get("id") == memory_id:
                memory["content"] = content.strip()
                memory["updated_at"] = datetime.now().isoformat()
                self._save_memories(memories)
                return {
                    "success": True,
                    "message": f"Memory {memory_id} updated successfully",
                    "memory": memory
                }
        
        return {
            "success": False,
            "error": f"Memory with ID {memory_id} not found"
        }
    
    def delete_memory(self, memory_id: int) -> Dict[str, Any]:
        memories = self._load_memories()
        
        for i, memory in enumerate(memories):
            if memory.get("id") == memory_id:
                deleted_memory = memories.pop(i)
                self._save_memories(memories)
                return {
                    "success": True,
                    "message": f"Memory {memory_id} deleted successfully",
                    "memory": deleted_memory
                }
        
        return {
            "success": False,
            "error": f"Memory with ID {memory_id} not found"
        }
    
    def clear_all_memories(self) -> Dict[str, Any]:
        memories = self._load_memories()
        count = len(memories)

        self._save_memories([])

        return {
            "success": True,
            "message": f"All memories cleared successfully ({count} memories)",
            "deleted_count": count
        }
    
    def list_memories(self, limit: int = 20) -> Dict[str, Any]:
        memories = self._load_memories()
        limit = max(1, min(limit, 200))
        
        if not memories:
            return {
                "success": True,
                "message": "No memories found",
                "memories": [],
                "total": 0
            }

        memories_sorted = sorted(memories, key=lambda x: x.get("created_at", ""), reverse=True)

        if len(memories_sorted) > limit:
            memories_sorted = memories_sorted[:limit]
        
        summary = []
        for m in memories_sorted:
            summary.append({
                "id": m.get("id"),
                "date": m.get("date", ""),
                "time": m.get("time", ""),
                "content_preview": m.get("content", "")[:50] + ("..." if len(m.get("content", "")) > 50 else ""),
                "created_at": m.get("created_at")
            })
        
        return {
            "success": True,
            "message": f"Found {len(summary)} memories (total: {len(memories)})",
            "memories": summary,
            "total": len(memories)
        }
    
    def get_memory_by_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        memories = self._load_memories()
        for m in memories:
            if m.get("id") == memory_id:
                return m
        return None

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
        console.print("[bold cyan]║           📝 MEMORY OPERATION - PARAMETERS                  ║[/bold cyan]")
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