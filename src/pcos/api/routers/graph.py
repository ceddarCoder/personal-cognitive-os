import asyncio
from fastapi import APIRouter
from pcos.infrastructure.database import Database

router = APIRouter()
db = Database()

@router.get("/nodes")
async def get_graph_nodes(limit: int = 200):
    def _query():
        cursor = db.conn.execute(
            "SELECT id, type, name, properties, confidence FROM graph_nodes LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    nodes = await asyncio.to_thread(_query)
    return {"nodes": nodes}

@router.get("/edges")
async def get_graph_edges(limit: int = 500):
    def _query():
        cursor = db.conn.execute(
            "SELECT source_id, target_id, relation, weight, confidence FROM graph_edges LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    edges = await asyncio.to_thread(_query)
    return {"edges": edges}

@router.get("/node/{node_id}")
async def get_node_details(node_id: str):
    def _query():
        # Get node
        cursor = db.conn.execute("SELECT * FROM graph_nodes WHERE id = ?", (node_id,))
        node = dict(cursor.fetchone()) if cursor.fetchone() else None
        if not node:
            return None
        # Get connected edges
        cursor = db.conn.execute(
            "SELECT * FROM graph_edges WHERE source_id = ? OR target_id = ?",
            (node_id, node_id)
        )
        edges = [dict(row) for row in cursor.fetchall()]
        return {"node": node, "edges": edges}
    result = await asyncio.to_thread(_query)
    if not result:
        return {"error": "Node not found"}
    return result

@router.get("/related/{node_id}")
async def get_related_nodes(node_id: str, depth: int = 2):
    """Get nodes related to the given node up to a certain depth."""
    # Simple implementation – get direct neighbors first
    def _query():
        cursor = db.conn.execute("""
            SELECT DISTINCT 
                CASE WHEN source_id = ? THEN target_id ELSE source_id END as related_id
            FROM graph_edges 
            WHERE source_id = ? OR target_id = ?
        """, (node_id, node_id, node_id))
        neighbors = [dict(row) for row in cursor.fetchall()]
        return neighbors
    neighbors = await asyncio.to_thread(_query)
    return {"source": node_id, "related": neighbors}