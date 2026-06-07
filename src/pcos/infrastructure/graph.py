import uuid
import json
import networkx as nx
from typing import List, Dict, Any, Optional
from pcos.infrastructure.database import Database
from loguru import logger

class GraphStore:
    """SQLite-backed knowledge graph with in-memory NetworkX for traversal."""
    
    def __init__(self):
        self.db = Database()
        self._graph = None
        self._load_graph()
    
    def _load_graph(self):
        """Load all nodes and edges into NetworkX graph."""
        self._graph = nx.MultiDiGraph()
        # Load nodes
        with self.db._lock:
            cursor = self.db.conn.execute("SELECT id, type, name, properties, confidence FROM graph_nodes")
            nodes = cursor.fetchall()
            
        for row in nodes:
            self._graph.add_node(row['id'], 
                                 type=row['type'], 
                                 name=row['name'],
                                 properties=json.loads(row['properties']),
                                 confidence=row['confidence'])
        # Load edges
        with self.db._lock:
            cursor = self.db.conn.execute("SELECT id, source_id, target_id, relation, weight, confidence FROM graph_edges")
            edges = cursor.fetchall()
            
        for row in edges:
            self._graph.add_edge(row['source_id'], row['target_id'],
                                 key=row['id'],
                                 relation=row['relation'],
                                 weight=row['weight'],
                                 confidence=row['confidence'])
        logger.info(f"Loaded graph: {self._graph.number_of_nodes()} nodes, {self._graph.number_of_edges()} edges")
    
    def add_node(self, node_type: str, name: str, properties: dict = None, confidence: float = 1.0, source: str = "manual") -> str:
        """Add a node to both SQLite and NetworkX."""
        node_id = str(uuid.uuid4())
        props_json = json.dumps(properties or {})
        with self.db._lock:
            self.db.conn.execute(
                "INSERT INTO graph_nodes (id, type, name, properties, confidence, source) VALUES (?,?,?,?,?,?)",
                (node_id, node_type, name, props_json, confidence, source)
            )
            self.db.conn.commit()
        # Update in-memory graph
        self._graph.add_node(node_id, type=node_type, name=name, properties=properties or {}, confidence=confidence)
        return node_id
    
    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0, confidence: float = 1.0, source: str = "manual") -> str:
        edge_id = str(uuid.uuid4())
        with self.db._lock:
            self.db.conn.execute(
                "INSERT INTO graph_edges (id, source_id, target_id, relation, weight, confidence, source) VALUES (?,?,?,?,?,?,?)",
                (edge_id, source_id, target_id, relation, weight, confidence, source)
            )
            self.db.conn.commit()
        self._graph.add_edge(source_id, target_id, key=edge_id, relation=relation, weight=weight, confidence=confidence)
        return edge_id
    
    def get_neighbors(self, node_id: str, relation: str = None) -> List[Dict]:
        """Get neighboring nodes, optionally filtered by relation."""
        if node_id not in self._graph:
            return []
        neighbors = []
        for neighbor in self._graph.neighbors(node_id):
            edge_data = self._graph.get_edge_data(node_id, neighbor)
            for edge_id, attrs in edge_data.items():
                if relation is None or attrs.get('relation') == relation:
                    neighbors.append({
                        'node_id': neighbor,
                        'node_name': self._graph.nodes[neighbor].get('name'),
                        'node_type': self._graph.nodes[neighbor].get('type'),
                        'relation': attrs.get('relation'),
                        'weight': attrs.get('weight'),
                        'confidence': attrs.get('confidence')
                    })
        return neighbors
    
    def find_path(self, source_id: str, target_id: str) -> List[str]:
        """Find shortest path between two nodes by ID."""
        try:
            path = nx.shortest_path(self._graph, source=source_id, target=target_id)
            return path
        except nx.NetworkXNoPath:
            return []
    
    def search_nodes(self, query: str, node_type: str = None, limit: int = 10) -> List[Dict]:
        """Search nodes by name substring."""
        sql = "SELECT id, type, name, properties, confidence FROM graph_nodes WHERE name LIKE ?"
        params = [f"%{query}%"]
        if node_type:
            sql += " AND type = ?"
            params.append(node_type)
        sql += " LIMIT ?"
        params.append(limit)
        with self.db._lock:
            cursor = self.db.conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        with self.db._lock:
            cursor = self.db.conn.execute("SELECT * FROM graph_nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def refresh(self):
        """Reload graph from database (e.g., after external changes)."""
        self._load_graph()
