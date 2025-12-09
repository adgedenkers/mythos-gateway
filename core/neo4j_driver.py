from neo4j import GraphDatabase
from core.config import settings

# Create a single global driver instance
driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASS)
)

def close_driver():
    """Close the Neo4j driver (for shutdown cleanup)."""
    if driver is not None:
        driver.close()
