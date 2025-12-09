from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.neo4j_driver import driver

router = APIRouter()

class CypherQuery(BaseModel):
    query: str

@router.post("/cypher")
def run_cypher(query: CypherQuery):
    try:
        with driver.session() as session:
            result = session.run(query.query)
            return {"data": [record.data() for record in result]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Optional: Uncomment to require an API token in header
# from fastapi import Header
# @router.post("/cypher")
# def run_cypher(query: CypherQuery, x_token: str = Header(...)):
#     if x_token != "your-secret-token":
#         raise HTTPException(status_code=401, detail="Invalid token")
#     ...
