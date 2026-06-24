# Personalized Learning Agent

An AI-powered, highly personalized learning platform that dynamically generates, structures, and orchestrates custom learning paths for any given topic. Using a swarm of specialized AI agents, the system generates adaptive curriculums, evaluates user knowledge, and dynamically fetches multimedia and practical resources.

## 🏗️ Architecture Overview

The system is built on a distributed microservice architecture:

### 1. Frontend (React + Vite)
- **Tech Stack**: React, Vite, TailwindCSS, ReactFlow
- **Role**: Provides a dynamic, interactive UI where users can view their learning paths as a progressive node graph, interact with learning materials, and mark nodes as completed.

### 2. State & CRUD Backend (Go)
- **Tech Stack**: Go, Gorilla Mux
- **Role**: Acts as the primary API gateway for the frontend. Handles all direct interactions with the Supabase database, manages user path history, and enforces rules for unlocking new nodes in the curriculum graph as previous ones are completed.

### 3. AI Generation Backend (Python)
- **Tech Stack**: Python, FastAPI, LangChain, LangGraph
- **Role**: The core intelligence engine. Uses a multi-agent Swarm Architecture (Synthesizer, Academic Worker, Practical Worker, Multimedia Worker) to dynamically search the web, generate curriculum graphs, and produce structured learning materials powered by the **Groq** LLM API and **Pinecone** for Vector RAG ingestion.

### 4. Managed Services
- **Database / Auth**: Supabase (PostgreSQL)
- **Vector Store**: Pinecone
- **LLM Inference**: Groq (`llama-3.3-70b-versatile`)

---

## 🚀 Getting Started Locally

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+)
- [Go](https://golang.org/dl/) (v1.21+)
- [Python](https://www.python.org/downloads/) (v3.11+)

### 1. Database Setup
Run the SQL migration scripts located in `supabase/migrations/` in your Supabase SQL editor to create the `learning_paths` and `path_nodes` tables.

### 2. Python Backend Setup
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```
Create a `.env` file in `backend/` with:
```env
GROQ_API_KEY=your_groq_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_HOST=your_pinecone_host
PINECONE_INDEX=your_pinecone_index
```
Run the server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Go Backend Setup
```bash
cd go-backend
go mod tidy
```
Create a `.env` file in `go-backend/` with:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
PYTHON_BACKEND_URL=http://localhost:8000
```
Run the server:
```bash
go run main.go
```

### 4. Frontend Setup
```bash
cd frontend
npm install
```
Create a `.env` file in `frontend/` with:
```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_BASE_URL=http://localhost:4000
VITE_AI_API_BASE_URL=http://localhost:8000
```
Run the frontend:
```bash
npm run dev
```

---

## 🌐 Deployment

The repository includes configuration to automatically deploy the backends to **Render** and the frontend to **Vercel**.

1. **Deploy Backends to Render**:
   - Connect the repo to Render and choose "Blueprint".
   - Render will read the `render.yaml` file and automatically provision both the Go and Python backends.
   - Inject the environment variables from your local `.env` files.

2. **Deploy Frontend to Vercel**:
   - Connect the repo to Vercel.
   - Set the Root Directory to `frontend`.
   - Update `VITE_API_BASE_URL` and `VITE_AI_API_BASE_URL` to point to your live Render URLs.
