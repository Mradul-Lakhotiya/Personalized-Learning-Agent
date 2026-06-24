// Package handlers implements HTTP handlers for conversation (learning path) endpoints.
package handlers

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sort"
	"time"

	"github.com/gorilla/mux"
	"go-backend/db"
)

// GetConversations lists all learning paths for a user, sorted newest first.
// Enriches each path with computed node_count and completed_count fields.
func GetConversations(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userID := vars["userId"]

	var paths []map[string]interface{}
	query := fmt.Sprintf(
		"select=id,thread_id,learning_goal,phase,completed_node_ids,sections_generated,created_at,updated_at,curriculum_graph&user_id=eq.%s",
		userID,
	)
	if err := db.Query("learning_paths", query, &paths); err != nil {
		log.Printf("[GetConversations] DB error for user %s: %v", userID, err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	log.Printf("[GetConversations] Found %d paths for user %s", len(paths), userID)

	// Sort by created_at descending
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

// GetCurriculum returns the full curriculum graph for a single conversation.
func GetCurriculum(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userID := vars["userId"]
	conversationID := vars["conversationId"]

	var paths []map[string]interface{}
	query := fmt.Sprintf("select=*&thread_id=eq.%s&user_id=eq.%s", conversationID, userID)
	if err := db.Query("learning_paths", query, &paths); err != nil {
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
