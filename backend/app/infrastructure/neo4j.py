from neo4j import GraphDatabase
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        self.driver = None
        if settings.NEO4J_URI:
            try:
                self.driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                logger.info("Connected to Neo4j successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def run_query(self, query: str, parameters: dict = None) -> list[dict]:
        if not self.driver:
            logger.warning("Neo4j driver is not initialized. Skipping query.")
            return []
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def create_entity(self, label: str, name: str, properties: dict, org_id: int) -> dict:
        """
        Creates an entity node in Neo4j.
        Labels should be title-cased, e.g. Employee, Team, Project, Meeting, Customer, Product, Email, Document, Task, Repository
        """
        query = f"""
        MERGE (n:{label} {{name: $name, org_id: $org_id}})
        SET n += $properties, n.updated_at = timestamp()
        RETURN n
        """
        params = {
            "name": name,
            "org_id": org_id,
            "properties": properties
        }
        res = self.run_query(query, params)
        return res[0]["n"] if res else {}

    def create_relationship(self, source_label: str, source_name: str, rel_type: str, target_label: str, target_name: str, org_id: int, properties: dict = None) -> dict:
        """
        Creates a relationship between two nodes in Neo4j.
        """
        query = f"""
        MATCH (a:{source_label} {{name: $source_name, org_id: $org_id}})
        MATCH (b:{target_label} {{name: $target_name, org_id: $org_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $properties
        RETURN type(r) as rel
        """
        params = {
            "source_name": source_name,
            "target_name": target_name,
            "org_id": org_id,
            "properties": properties or {}
        }
        res = self.run_query(query, params)
        return res[0] if res else {}

    def get_related_entities(self, entity_name: str, org_id: int, depth: int = 1) -> list[dict]:
        """
        Returns connected entities up to a certain depth.
        """
        query = """
        MATCH (n {name: $name, org_id: $org_id})-[r*1..2]-(m)
        RETURN n.name as source, type(r[0]) as relationship, m.name as target, labels(m)[0] as target_type
        """
        if depth > 1:
            query = f"""
            MATCH (n {{name: $name, org_id: $org_id}})-[r*1..{depth}]-(m)
            RETURN n.name as source, type(r[0]) as relationship, m.name as target, labels(m)[0] as target_type
            """
        params = {
            "name": entity_name,
            "org_id": org_id
        }
        return self.run_query(query, params)

neo4j_client = Neo4jClient()
