from datetime import datetime
from app.agents.state import AgentState
from app.infrastructure.qdrant import qdrant_rag
from app.infrastructure.neo4j import neo4j_client

class RetrievalAgent:
    def run(self, state: AgentState) -> dict:
        """
        Retrieves relevant documents using Hybrid RAG and maps relationships from Knowledge Graph.
        """
        current_step_idx = state["current_step"]
        step = state["plan"][current_step_idx]
        task_desc = step["task"]
        org_id = state.get("org_id", 1)
        department = state.get("department", "general")

        # 1. Query Qdrant Hybrid Search (Dense + Keyword + RRF)
        # Apply permission and multi-tenancy filter
        filter_dict = {
            "org_id": org_id,
            "department": department
        }
        
        raw_hits = qdrant_rag.search_hybrid(task_desc, limit=10, filter_dict=filter_dict)
        
        # 2. Re-rank results using CrossEncoder
        reranked_hits = qdrant_rag.rerank_results(task_desc, raw_hits, limit=5)
        
        # Format document context
        doc_contexts = []
        for hit in reranked_hits:
            filename = hit["metadata"].get("filename", "Unknown file")
            score = hit.get("rerank_score", hit.get("score", 0.0))
            doc_contexts.append(
                f"Source: {filename} (Re-rank Score: {score:.4f})\nContent: {hit['content']}\n"
            )
            
        document_context_str = "\n---\n".join(doc_contexts)

        # 3. Query Neo4j Knowledge Graph for related entities (like Projects, Employees, Tasks)
        # We can extract entities from the query (like 'Project Alpha' or 'Alpha')
        # Simple extraction based on capitalized words or substrings
        extracted_entities = []
        words = task_desc.split()
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 2:
                # check if double word entity
                if i + 1 < len(words) and words[i+1][0].isupper():
                    extracted_entities.append(f"{word} {words[i+1]}")
                else:
                    extracted_entities.append(word)

        kg_contexts = []
        for entity in set(extracted_entities):
            relations = neo4j_client.get_related_entities(entity, org_id=org_id, depth=1)
            for rel in relations:
                kg_contexts.append(
                    f"Entity '{rel['source']}' is connected via '{rel['relationship']}' to '{rel['target']}' ({rel['target_type']})"
                )

        kg_context_str = "\n".join(kg_contexts)

        # Combine results
        combined_result = f"=== HYBRID RAG VECTOR SEARCH ===\n{document_context_str or 'No vector search results found.'}\n\n=== KNOWLEDGE GRAPH RELATIONSHIPS ===\n{kg_context_str or 'No graph relationships found for query entities.'}"

        # Update step state
        updated_plan = list(state["plan"])
        updated_plan[current_step_idx]["status"] = "completed"
        updated_plan[current_step_idx]["result"] = f"Retrieved {len(reranked_hits)} document chunks and {len(kg_contexts)} relationships."

        # Merge new context with existing context
        context = dict(state.get("context", {}))
        context["retrieved_documents"] = reranked_hits
        context["kg_relationships"] = kg_contexts
        context["text_context"] = context.get("text_context", "") + "\n\n" + combined_result

        log_entry = {
            "agent": "retrieval",
            "message": f"Successfully retrieved {len(reranked_hits)} vector documents and {len(kg_contexts)} graph relations.",
            "timestamp": str(datetime.utcnow())
        }

        return {
            "plan": updated_plan,
            "context": context,
            "current_step": current_step_idx + 1,
            "agent_logs": [log_entry]
        }
