import logging
from typing import Dict, List, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class Neo4jGraphStore:
    """
    Optional mirror store for Neo4j (behind compose profile 'graph').
    Hot path NEVER calls this store directly.
    Synchronizes nodes and edges via MERGE statements for analytical and cross-equipment queries.
    """

    def __init__(self):
        self._driver = None

    async def get_driver(self):
        if not settings.ENABLE_NEO4J:
            return None
        if self._driver is None:
            try:
                from neo4j import AsyncGraphDatabase
                self._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
            except Exception as e:
                logger.warning(f"Neo4j driver initialization skipped: {e}")
                return None
        return self._driver

    async def sync_from_dict(self, graph_dict: Dict[str, Any]) -> bool:
        """Mirror snapshot into Neo4j with unique constraints."""
        driver = await self.get_driver()
        if not driver:
            return False

        try:
            async with driver.session() as session:
                # 1. Create constraint if not present
                await session.run("CREATE CONSTRAINT node_id_uniq IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE")

                # 2. Batch merge nodes
                nodes = graph_dict.get("nodes", [])
                node_query = """
                UNWIND $nodes AS n
                MERGE (node:Node {id: n.id})
                SET node += n, node:Resource
                """
                await session.run(node_query, nodes=nodes)

                # 3. Batch merge edges
                edges = graph_dict.get("edges", [])
                edge_query = """
                UNWIND $edges AS e
                MATCH (s:Node {id: e.source})
                MATCH (t:Node {id: e.target})
                MERGE (s)-[r:RELATION {type: e.edge_type}]->(t)
                SET r += e
                """
                await session.run(edge_query, edges=edges)

            logger.info("Neo4j mirror synced successfully.")
            return True
        except Exception as e:
            logger.warning(f"Neo4j sync failed: {e}")
            return False

    async def close(self):
        if self._driver:
            await self._driver.close()


neo4j_store = Neo4jGraphStore()
