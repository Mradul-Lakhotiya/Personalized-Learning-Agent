package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sort"
	"time"

	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
	"github.com/nedpals/supabase-go"
)

var supabaseClient *supabase.Client

func main() {
	if err := godotenv.Load(".env"); err != nil {
		log.Println("No .env file found or error loading it. Relying on environment variables.")
	}

	supabaseUrl := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")

	if supabaseUrl == "" || supabaseKey == "" {
		log.Fatal("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
	}

	supabaseClient = supabase.CreateClient(supabaseUrl, supabaseKey)

	port := os.Getenv("PORT")
	if port == "" {
		port = "4000"
	}

	r := mux.NewRouter()

	// 1. Get all conversations (learning paths) for a user
	r.HandleFunc("/api/v1/users/{userId}/conversations", getConversations).Methods("GET", "OPTIONS")
	
	// 2. Get specific curriculum graph
	r.HandleFunc("/api/v1/users/{userId}/conversations/{conversationId}", getCurriculum).Methods("GET", "OPTIONS")
	
	// 3. Get node details
	r.HandleFunc("/api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}", getNodeDetails).Methods("GET", "OPTIONS")
	
	// 4. Generate node content (SSE proxy)
	r.HandleFunc("/api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}/generate", generateNodeProxy).Methods("GET", "OPTIONS")
	
	// 5. Complete node
	r.HandleFunc("/api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}/complete", completeNode).Methods("POST", "OPTIONS")

	// Apply CORS
	handler := corsMiddleware(r)

	log.Printf("Go State/CRUD Backend running on port %s", port)
	if err := http.ListenAndServe(":"+port, handler); err != nil {
		log.Fatal(err)
	}
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
		
		next.ServeHTTP(w, r)
	})
}

// Handlers implementation

// Helper to execute a raw Supabase REST query
func executeSupabaseQuery(table string, query string, dest interface{}) error {
	supabaseUrl := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")
	url := fmt.Sprintf("%s/rest/v1/%s?%s", supabaseUrl, table, query)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("apikey", supabaseKey)
	req.Header.Set("Authorization", "Bearer "+supabaseKey)
	
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("Supabase API error: %s", string(b))
	}
	
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	
	return json.Unmarshal(b, dest)
}

// Helper to execute a raw Supabase REST PATCH
func executeSupabasePatch(table string, query string, body interface{}) error {
	supabaseUrl := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")
	url := fmt.Sprintf("%s/rest/v1/%s?%s", supabaseUrl, table, query)
	
	jsonBody, err := json.Marshal(body)
	if err != nil {
		return err
	}
	
	req, err := http.NewRequest("PATCH", url, bytes.NewBuffer(jsonBody))
	if err != nil {
		return err
	}
	req.Header.Set("apikey", supabaseKey)
	req.Header.Set("Authorization", "Bearer "+supabaseKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Prefer", "return=minimal") // Don't return the large object
	
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("Supabase API PATCH error: %s", string(b))
	}
	
	return nil
}

func getConversations(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userId := vars["userId"]

	var paths []map[string]interface{}
	query := fmt.Sprintf("select=id,thread_id,learning_goal,phase,completed_node_ids,sections_generated,created_at,updated_at,curriculum_graph&user_id=eq.%s", userId)
	err := executeSupabaseQuery("learning_paths", query, &paths)
	if err != nil {
		log.Printf("[getConversations] DB error for user %s: %v", userId, err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	log.Printf("[getConversations] Found %d paths for user %s", len(paths), userId)

	// Sort by created_at descending. Guard against null or non-string values.
	sort.SliceStable(paths, func(i, j int) bool {
		getTime := func(p map[string]interface{}) time.Time {
			if v, ok := p["created_at"].(string); ok {
				if t, err := time.Parse(time.RFC3339, v); err == nil {
					return t
				}
			}
			return time.Time{}
		}
		return getTime(paths[i]).After(getTime(paths[j]))
	})

	// Enrich with node counts
	for i, path := range paths {
		graph, ok := path["curriculum_graph"].(map[string]interface{})
		if ok {
			nodes, ok2 := graph["nodes"].([]interface{})
			if ok2 {
				paths[i]["node_count"] = len(nodes)
			} else {
				paths[i]["node_count"] = 0
			}
		} else {
			paths[i]["node_count"] = 0
		}

		completed, ok := path["completed_node_ids"].([]interface{})
		if ok {
			paths[i]["completed_count"] = len(completed)
		} else {
			paths[i]["completed_count"] = 0
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"paths": paths})
}

func getCurriculum(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userId := vars["userId"]
	conversationId := vars["conversationId"]

	var paths []map[string]interface{}
	query := fmt.Sprintf("select=*&thread_id=eq.%s&user_id=eq.%s", conversationId, userId)
	err := executeSupabaseQuery("learning_paths", query, &paths)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	if len(paths) == 0 {
		http.Error(w, "Conversation not found", http.StatusNotFound)
		return
	}
	
	data := paths[0]

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"phase":              data["phase"],
		"curriculum_graph":   data["curriculum_graph"],
		"completed_node_ids": data["completed_node_ids"],
		"learning_goal":      data["learning_goal"],
	})
}

func getNodeDetails(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userId := vars["userId"]
	conversationId := vars["conversationId"]
	nodeId := vars["nodeId"]

	var pathData []map[string]interface{}
	query := fmt.Sprintf("select=id&thread_id=eq.%s&user_id=eq.%s", conversationId, userId)
	err := executeSupabaseQuery("learning_paths", query, &pathData)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	if len(pathData) == 0 {
		http.Error(w, "Path not found", http.StatusNotFound)
		return
	}

	var nodeData []map[string]interface{}
	pathId := pathData[0]["id"].(string)
	nodeQuery := fmt.Sprintf("select=*&path_id=eq.%s&node_id=eq.%s", pathId, nodeId)
	err = executeSupabaseQuery("path_nodes", nodeQuery, &nodeData)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	if len(nodeData) == 0 {
		http.Error(w, "Node not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(nodeData[0])
}

func generateNodeProxy(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userId := vars["userId"]
	conversationId := vars["conversationId"]
	nodeId := vars["nodeId"]

	// 1. Get path info and node info
	var pathData []map[string]interface{}
	query := fmt.Sprintf("select=id,learning_goal&thread_id=eq.%s&user_id=eq.%s", conversationId, userId)
	err := executeSupabaseQuery("learning_paths", query, &pathData)
	if err != nil || len(pathData) == 0 {
		http.Error(w, "Path not found", http.StatusNotFound)
		return
	}

	pathId := pathData[0]["id"].(string)
	learningGoal := pathData[0]["learning_goal"].(string)

	var nodeData []map[string]interface{}
	nodeQuery := fmt.Sprintf("select=title,description&path_id=eq.%s&node_id=eq.%s", pathId, nodeId)
	err = executeSupabaseQuery("path_nodes", nodeQuery, &nodeData)
	if err != nil || len(nodeData) == 0 {
		http.Error(w, "Node not found", http.StatusNotFound)
		return
	}

	nodeTitle := nodeData[0]["title"].(string)
	nodeDesc := nodeData[0]["description"].(string)

	// 2. Call python backend
	pythonBackendUrl := os.Getenv("PYTHON_BACKEND_URL")
	if pythonBackendUrl == "" {
		pythonBackendUrl = "http://localhost:8000"
	}
	
	reqBody, _ := json.Marshal(map[string]interface{}{
		"node_id":       nodeId,
		"thread_id":     conversationId,
		"title":         nodeTitle,
		"description":   nodeDesc,
		"learning_goal": learningGoal,
		"user_id":       userId,
	})

	pyReq, err := http.NewRequest("POST", pythonBackendUrl+"/api/v1/agent/generate-node", bytes.NewBuffer(reqBody))
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	pyReq.Header.Set("Content-Type", "application/json")
	// Forward the Authorization header from the original request so Python can verify the user
	if authHeader := r.Header.Get("Authorization"); authHeader != "" {
		pyReq.Header.Set("Authorization", authHeader)
	}

	client := &http.Client{Timeout: 0} // no timeout for streaming
	pyRes, err := client.Do(pyReq)
	if err != nil {
		http.Error(w, "Failed to connect to python backend", http.StatusBadGateway)
		return
	}
	defer pyRes.Body.Close()

	if pyRes.StatusCode != http.StatusOK {
		http.Error(w, fmt.Sprintf("Python backend error: %d", pyRes.StatusCode), http.StatusBadGateway)
		return
	}

	// 3. Proxy SSE
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	buf := make([]byte, 4096)
	for {
		n, err := pyRes.Body.Read(buf)
		if n > 0 {
			w.Write(buf[:n])
			flusher.Flush()
		}
		if err != nil {
			if err == io.EOF {
				break
			}
			log.Printf("Error reading stream: %v", err)
			break
		}
	}
}

func contains(arr []interface{}, str string) bool {
	for _, v := range arr {
		if v == str {
			return true
		}
	}
	return false
}

func completeNode(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userId := vars["userId"]
	conversationId := vars["conversationId"]
	nodeId := vars["nodeId"]

	var pathData []map[string]interface{}
	query := fmt.Sprintf("select=id,curriculum_graph,completed_node_ids&thread_id=eq.%s&user_id=eq.%s", conversationId, userId)
	err := executeSupabaseQuery("learning_paths", query, &pathData)
	if err != nil || len(pathData) == 0 {
		http.Error(w, "Path not found", http.StatusNotFound)
		return
	}

	pData := pathData[0]
	pathId := pData["id"].(string)

	graph, ok := pData["curriculum_graph"].(map[string]interface{})
	if !ok {
		graph = map[string]interface{}{}
	}
	nodesInter, _ := graph["nodes"].([]interface{})
	edgesInter, _ := graph["edges"].([]interface{})
	completedInter, _ := pData["completed_node_ids"].([]interface{})

	var nodes []map[string]interface{}
	for _, n := range nodesInter {
		if nm, ok := n.(map[string]interface{}); ok {
			nodes = append(nodes, nm)
		}
	}

	var edges []map[string]interface{}
	for _, e := range edgesInter {
		if em, ok := e.(map[string]interface{}); ok {
			edges = append(edges, em)
		}
	}

	// mark node as completed in path_nodes
	var result interface{}
	err = supabaseClient.DB.From("path_nodes").Update(map[string]interface{}{
		"status":       "completed",
		"completed_at": time.Now().UTC().Format(time.RFC3339),
	}).Eq("path_id", pathId).Eq("node_id", nodeId).Execute(&result)

	// update graph state
	if !contains(completedInter, nodeId) {
		completedInter = append(completedInter, nodeId)
	}

	validNodeIds := make(map[string]bool)
	for i := range nodes {
		nId := nodes[i]["id"].(string)
		validNodeIds[nId] = true
		if nId == nodeId {
			nodes[i]["status"] = "completed"
		}
	}

	var newlyAvailable []map[string]interface{}

	for i := range nodes {
		if nodes[i]["status"] == "locked" {
			prereqsInter, ok := nodes[i]["prerequisites"].([]interface{})
			if !ok {
				prereqsInter = []interface{}{}
			}
			
			allCompleted := true
			validPrereqsCount := 0
			for _, p := range prereqsInter {
				pStr := p.(string)
				if validNodeIds[pStr] {
					validPrereqsCount++
					if !contains(completedInter, pStr) {
						allCompleted = false
						break
					}
				}
			}

			if validPrereqsCount == 0 || allCompleted {
				nodes[i]["status"] = "available"
				newlyAvailable = append(newlyAvailable, map[string]interface{}{
					"path_id": pathId,
					"user_id": userId,
					"node_id": nodes[i]["id"],
					"title":   nodes[i]["title"],
					"status":  "available",
				})
			}
		}
	}

	for i := range edges {
		targetStr := edges[i]["target"].(string)
		isAvailable := false
		for _, n := range nodes {
			if n["id"] == targetStr && n["status"] == "available" {
				isAvailable = true
				break
			}
		}
		edges[i]["animated"] = isAvailable
	}

	graph["nodes"] = nodes
	graph["edges"] = edges

	err = executeSupabasePatch("learning_paths", fmt.Sprintf("id=eq.%s", pathId), map[string]interface{}{
		"completed_node_ids": completedInter,
		"curriculum_graph":   graph,
	})

	if len(newlyAvailable) > 0 {
		// nedpals/supabase-go does not have explicit Upsert method in older versions, Insert might fail if duplicate
		// Let's use Insert since Supabase REST API falls back to insert, but for true upsert we might need an RPC.
		// Actually, supabase-go has Insert() which accepts a slice of structs. But we don't have Upsert natively exposed sometimes.
		// Wait, nedpals/supabase-go uses Insert with InsertOpts for upsert. But here we can just skip or use raw HTTP if needed.
		// Let's just use Insert and ignore error if it conflicts, because it was already available.
		err = supabaseClient.DB.From("path_nodes").Insert(newlyAvailable).Execute(&result)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":           true,
		"completed_node_id": nodeId,
		"curriculum_graph":  graph,
	})
}
