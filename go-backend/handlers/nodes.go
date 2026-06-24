// Package handlers implements HTTP handlers for node endpoints.
package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gorilla/mux"
	"go-backend/db"

	supabase "github.com/nedpals/supabase-go"
)

// supabaseClient is initialised once at startup by main.go and shared across handlers.
var SupabaseClient *supabase.Client

// GetNodeDetails returns full details (including cached resources) for a single node.
func GetNodeDetails(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userID := vars["userId"]
	conversationID := vars["conversationId"]
	nodeID := vars["nodeId"]

	// Resolve path UUID from thread_id
	var pathData []map[string]interface{}
	q := fmt.Sprintf("select=id&thread_id=eq.%s&user_id=eq.%s", conversationID, userID)
	if err := db.Query("learning_paths", q, &pathData); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	if len(pathData) == 0 {
		http.Error(w, "Path not found", http.StatusNotFound)
		return
	}

	pathID := pathData[0]["id"].(string)
	var nodeData []map[string]interface{}
	nodeQuery := fmt.Sprintf("select=*&path_id=eq.%s&node_id=eq.%s", pathID, nodeID)
	if err := db.Query("path_nodes", nodeQuery, &nodeData); err != nil {
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

// GenerateNodeProxy proxies the SSE content-generation stream from the Python backend.
// It resolves node metadata first so the Python backend receives full context.
func GenerateNodeProxy(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userID := vars["userId"]
	conversationID := vars["conversationId"]
	nodeID := vars["nodeId"]

	// 1. Resolve path + node metadata
	var pathData []map[string]interface{}
	q := fmt.Sprintf("select=id,learning_goal&thread_id=eq.%s&user_id=eq.%s", conversationID, userID)
	if err := db.Query("learning_paths", q, &pathData); err != nil || len(pathData) == 0 {
		http.Error(w, "Path not found", http.StatusNotFound)
		return
	}
	pathID := pathData[0]["id"].(string)
	learningGoal := pathData[0]["learning_goal"].(string)

	var nodeData []map[string]interface{}
	nodeQuery := fmt.Sprintf("select=title,description&path_id=eq.%s&node_id=eq.%s", pathID, nodeID)
	if err := db.Query("path_nodes", nodeQuery, &nodeData); err != nil || len(nodeData) == 0 {
		http.Error(w, "Node not found", http.StatusNotFound)
		return
	}
	nodeTitle := nodeData[0]["title"].(string)
	nodeDesc := nodeData[0]["description"].(string)

	// 2. Forward to Python backend with full context
	pythonURL := os.Getenv("PYTHON_BACKEND_URL")
	if pythonURL == "" {
		pythonURL = "http://localhost:8000"
	}

	reqBody, _ := json.Marshal(map[string]interface{}{
		"node_id":       nodeID,
		"thread_id":     conversationID,
		"title":         nodeTitle,
		"description":   nodeDesc,
		"learning_goal": learningGoal,
		"user_id":       userID,
	})

	pyReq, err := http.NewRequest("POST", pythonURL+"/api/v1/agent/generate-node", bytes.NewBuffer(reqBody))
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	pyReq.Header.Set("Content-Type", "application/json")
	// Forward auth header so Python can verify the user
	if authHeader := r.Header.Get("Authorization"); authHeader != "" {
		pyReq.Header.Set("Authorization", authHeader)
	}

	client := &http.Client{Timeout: 0} // no timeout for SSE streams
	pyRes, err := client.Do(pyReq)
	if err != nil {
		http.Error(w, "Failed to connect to Python backend", http.StatusBadGateway)
		return
	}
	defer pyRes.Body.Close()

	if pyRes.StatusCode != http.StatusOK {
		http.Error(w, fmt.Sprintf("Python backend error: %d", pyRes.StatusCode), http.StatusBadGateway)
		return
	}

	// 3. Proxy the SSE stream
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
			log.Printf("[GenerateNodeProxy] Stream read error: %v", err)
			break
		}
	}
}

// CompleteNode marks a node as completed, recomputes which nodes become available,
// and persists both the updated path_nodes rows and curriculum_graph to Supabase.
func CompleteNode(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userID := vars["userId"]
	conversationID := vars["conversationId"]
	nodeID := vars["nodeId"]

	var pathData []map[string]interface{}
	q := fmt.Sprintf(
		"select=id,curriculum_graph,completed_node_ids&thread_id=eq.%s&user_id=eq.%s",
		conversationID, userID,
	)
	if err := db.Query("learning_paths", q, &pathData); err != nil || len(pathData) == 0 {
		http.Error(w, "Path not found", http.StatusNotFound)
		return
	}

	pData := pathData[0]
	pathID := pData["id"].(string)

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

	// Mark node as completed in path_nodes
	var result interface{}
	SupabaseClient.DB.From("path_nodes").Update(map[string]interface{}{
		"status":       "completed",
		"completed_at": time.Now().UTC().Format(time.RFC3339),
	}).Eq("path_id", pathID).Eq("node_id", nodeID).Execute(&result)

	// Add to completed set
	if !db.Contains(completedInter, nodeID) {
		completedInter = append(completedInter, nodeID)
	}

	// Update statuses in the graph
	validNodeIDs := make(map[string]bool)
	for i := range nodes {
		nID := nodes[i]["id"].(string)
		validNodeIDs[nID] = true
		if nID == nodeID {
			nodes[i]["status"] = "completed"
		}
	}

	var newlyAvailable []map[string]interface{}
	for i := range nodes {
		if nodes[i]["status"] != "locked" {
			continue
		}
		prereqsInter, _ := nodes[i]["prerequisites"].([]interface{})
		allCompleted := true
		validCount := 0
		for _, p := range prereqsInter {
			pStr := p.(string)
			if validNodeIDs[pStr] {
				validCount++
				if !db.Contains(completedInter, pStr) {
					allCompleted = false
					break
				}
			}
		}
		if validCount == 0 || allCompleted {
			nodes[i]["status"] = "available"
			newlyAvailable = append(newlyAvailable, map[string]interface{}{
				"path_id": pathID,
				"user_id": userID,
				"node_id": nodes[i]["id"],
				"title":   nodes[i]["title"],
				"status":  "available",
			})
		}
	}

	// Update edge animation flags
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

	// Persist updated graph + completed list
	db.Patch("learning_paths", fmt.Sprintf("id=eq.%s", pathID), map[string]interface{}{
		"completed_node_ids": completedInter,
		"curriculum_graph":   graph,
	})

	// Insert newly available nodes into path_nodes
	if len(newlyAvailable) > 0 {
		SupabaseClient.DB.From("path_nodes").Insert(newlyAvailable).Execute(&result)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":           true,
		"completed_node_id": nodeID,
		"curriculum_graph":  graph,
	})
}
