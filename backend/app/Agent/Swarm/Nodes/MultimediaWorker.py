import os
import asyncio
from typing import Dict, Any
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from ...LearnerState import LearnerState, SwarmWorkerResult

async def multimedia_worker_node(state: LearnerState) -> Dict[str, Any]:
    """
    Multimedia Worker: Searches YouTube for relevant videos and extracts their transcripts.
    """
    queries = state.get("swarm_queries", [])
    
    video_query_obj = next((q for q in queries if q["engine"] == "video"), None)
    if not video_query_obj:
        return {"swarm_raw_results": []}
        
    query = video_query_obj["query"]
    results = []
    
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("MultimediaWorker failed: YOUTUBE_API_KEY not found.")
        return {"swarm_raw_results": []}
    
    try:
        def fetch_youtube_data():
            # 1. Search for video
            youtube = build('youtube', 'v3', developerKey=api_key)
            request = youtube.search().list(
                part="snippet",
                maxResults=1,
                q=query,
                type="video",
                videoCaption="closedCaption" # Prefer videos with captions
            )
            response = request.execute()
            
            if not response.get("items"):
                return None
                
            video = response["items"][0]
            video_id = video["id"]["videoId"]
            title = video["snippet"]["title"]
            
            # 2. Fetch transcript (bypasses official API quota)
            # Instantiate the API and fetch English transcript
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)
            
            # Find the english transcript and fetch it
            transcript_data = transcript_list.find_transcript(['en', 'en-US', 'en-GB']).fetch()
            
            # Concatenate first 50 lines to keep it manageable
            # Handle both dict and object return types from youtube_transcript_api
            text_lines = []
            for t in transcript_data[:50]:
                if isinstance(t, dict):
                    text_lines.append(t.get('text', ''))
                else:
                    text_lines.append(getattr(t, 'text', str(t)))
            transcript_text = " ".join(text_lines)
            
            return {
                "video_id": video_id,
                "title": title,
                "text": transcript_text
            }

        # Async execution to protect the event loop
        yt_data = await asyncio.to_thread(fetch_youtube_data)
        
        if yt_data:
            results.append(SwarmWorkerResult(
                source_type="video",
                raw_text=f"Video Transcript Excerpt: {yt_data['text']}",
                source_url=f"https://www.youtube.com/watch?v={yt_data['video_id']}",
                title=yt_data['title'],
                metadata={"video_id": yt_data['video_id']}
            ))
            
    except Exception as e:
        print(f"MultimediaWorker failed: {e}") 
        pass 
        
    return {"swarm_raw_results": results}
