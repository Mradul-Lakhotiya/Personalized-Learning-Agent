package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
	supabase "github.com/nedpals/supabase-go"

	"go-backend/handlers"
	"go-backend/middleware"
)

func main() {
	if err := godotenv.Load(".env"); err != nil {
		log.Println("No .env file found — relying on environment variables.")
	}

	supabaseURL := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")
	if supabaseURL == "" || supabaseKey == "" {
		log.Fatal("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
	}

	// Share a single Supabase client across handlers that need the Go SDK
	handlers.SupabaseClient = supabase.CreateClient(supabaseURL, supabaseKey)

	port := os.Getenv("PORT")
	if port == "" {
		port = "4000"
	}

	r := mux.NewRouter()

	// All user-scoped routes require auth — the middleware verifies the JWT
	// and ensures the authenticated user matches the {userId} path param.
	api := r.PathPrefix("/api/v1/users/{userId}").Subrouter()
	api.Use(middleware.AuthRequired)

	// Conversations (learning paths)
	api.HandleFunc("/conversations", handlers.GetConversations).Methods("GET", "OPTIONS")
	api.HandleFunc("/conversations/{conversationId}", handlers.GetCurriculum).Methods("GET", "OPTIONS")

	// Nodes
	api.HandleFunc("/conversations/{conversationId}/nodes/{nodeId}", handlers.GetNodeDetails).Methods("GET", "OPTIONS")
	api.HandleFunc("/conversations/{conversationId}/nodes/{nodeId}/generate", handlers.GenerateNodeProxy).Methods("GET", "OPTIONS")
	api.HandleFunc("/conversations/{conversationId}/nodes/{nodeId}/complete", handlers.CompleteNode).Methods("POST", "OPTIONS")

	// Apply CORS globally (must wrap the whole router)
	handler := middleware.CORS(r)

	log.Printf("Go State/CRUD Backend running on :%s", port)
	if err := http.ListenAndServe(":"+port, handler); err != nil {
		log.Fatal(err)
	}
}
