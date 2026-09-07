"""
Export API route: export triples in RDF Turtle, JSON-LD, or raw JSON format.
"""

import json
from typing import Literal
from fastapi import APIRouter, Query, Response
from driftgraph.config import config
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.builder import KnowledgeGraphBuilder

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("")
async def export_graph(format: Literal["json", "ttl", "jsonld"] = Query("json")):
    """Export the knowledge graph in the requested serialization format."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    nodes = await storage.get_all_nodes()
    edges = await storage.get_all_edges()
    builder = KnowledgeGraphBuilder()

    if format == "ttl":
        ttl_content = builder.to_rdf_turtle(nodes, edges)
        return Response(content=ttl_content, media_type="text/turtle", headers={"Content-Disposition": "attachment; filename=driftgraph.ttl"})

    elif format == "jsonld":
        # Simplified JSON-LD representation
        jsonld_doc = {
            "@context": {
                "name": "http://schema.org/name",
                "description": "http://schema.org/description",
                "dg": "http://driftgraph.org/"
            },
            "@graph": [
                {"@id": f"dg:{n.id}", "name": n.name, "type": n.type, "description": n.description}
                for n in nodes
            ]
        }
        return Response(content=json.dumps(jsonld_doc, indent=2), media_type="application/ld+json", headers={"Content-Disposition": "attachment; filename=driftgraph.jsonld"})

    else:
        elements = builder.to_cytoscape_elements(nodes, edges)
        return Response(content=json.dumps(elements, indent=2), media_type="application/json", headers={"Content-Disposition": "attachment; filename=driftgraph.json"})
