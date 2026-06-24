// Package middleware provides HTTP middleware for the Go backend.
package middleware

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"github.com/gorilla/mux"
)

// SupabaseUser is a minimal representation of the Supabase auth user response.
type SupabaseUser struct {
	ID string `json:"id"`
}

// verifySupabaseToken calls the Supabase Auth API to verify a JWT and returns
// the authenticated user's UUID. Uses the same SUPABASE_SERVICE_KEY as the
// Python backend so no extra secrets are needed.
func verifySupabaseToken(token string) (string, error) {
	supabaseURL := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")

	if supabaseURL == "" || supabaseKey == "" {
		return "", fmt.Errorf("SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
	}

	url := supabaseURL + "/auth/v1/user"
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("apikey", supabaseKey)
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return "", fmt.Errorf("invalid or expired token (status %d)", resp.StatusCode)
	}
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("supabase auth error: %s", string(b))
	}

	var userResp SupabaseUser
	if err := json.NewDecoder(resp.Body).Decode(&userResp); err != nil {
		return "", fmt.Errorf("failed to decode supabase user response: %w", err)
	}
	if userResp.ID == "" {
		return "", fmt.Errorf("no user ID in supabase response")
	}
	return userResp.ID, nil
}

// AuthRequired is middleware that:
//  1. Reads the Authorization: Bearer <token> header.
//  2. Calls Supabase to verify the token.
//  3. Compares the authenticated user's UUID against the {userId} path param.
//     If they don't match, returns 403 Forbidden.
//
// This prevents a logged-in user from accessing another user's data by
// simply substituting a different userId in the URL.
func AuthRequired(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Skip pre-flight
		if r.Method == "OPTIONS" {
			next.ServeHTTP(w, r)
			return
		}

		authHeader := r.Header.Get("Authorization")
		if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
			http.Error(w, `{"error":"missing Authorization header"}`, http.StatusUnauthorized)
			return
		}
		token := strings.TrimPrefix(authHeader, "Bearer ")

		authenticatedUID, err := verifySupabaseToken(token)
		if err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"authentication failed: %s"}`, err.Error()), http.StatusUnauthorized)
			return
		}

		// Validate that the authed user matches the userId in the URL path
		vars := mux.Vars(r)
		if pathUID, ok := vars["userId"]; ok && pathUID != authenticatedUID {
			http.Error(w, `{"error":"forbidden: userId mismatch"}`, http.StatusForbidden)
			return
		}

		next.ServeHTTP(w, r)
	})
}
