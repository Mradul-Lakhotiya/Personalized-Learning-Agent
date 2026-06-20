import asyncio
import arxiv
from typing import Dict, Any
from ...LearnerState import LearnerState, SwarmWorkerResult

async def academic_worker_node(state: LearnerState) -> Dict[str, Any]:
    """
    Academic Worker: Uses arXiv API to fetch recent scholarly abstracts.
    """
    queries = state.get("swarm_queries", [])
    
    academic_query_obj = next((q for q in queries if q["engine"] == "academic"), None)
    if not academic_query_obj:
        return {"swarm_raw_results": []}
        
    query = academic_query_obj["query"]
    results = []
    
    try:
        def fetch_arxiv():
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=2,
                sort_by=arxiv.SortCriterion.Relevance
            )
            # return as list to consume the generator synchronously
            return list(client.results(search))

        # Async execution to protect the event loop
        papers = await asyncio.to_thread(fetch_arxiv)
        
        for paper in papers:
            results.append(SwarmWorkerResult(
                source_type="academic",
                raw_text=f"Abstract: {paper.summary}",
                source_url=paper.pdf_url,
                title=paper.title,
                metadata={"authors": [a.name for a in paper.authors]}
            ))
            
    except Exception as e:
        print(f"AcademicWorker failed: {e}") 
        pass 
        
    return {"swarm_raw_results": results}
