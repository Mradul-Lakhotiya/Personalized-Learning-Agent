// Package db provides low-level Supabase REST helpers for the Go backend.
// All handlers use these helpers instead of calling Supabase APIs directly.
package db

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
)

// Query executes a GET request against the Supabase REST API.
// table is the table name; query is a URL-encoded query string (e.g. "select=*&id=eq.123").
// dest is the pointer to unmarshal the JSON response into.
func Query(table string, query string, dest interface{}) error {
	supabaseURL := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")
	url := fmt.Sprintf("%s/rest/v1/%s?%s", supabaseURL, table, query)

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
		return fmt.Errorf("supabase GET error on %s: %s", table, string(b))
	}

	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, dest)
}

// Patch executes a PATCH request against the Supabase REST API.
// table is the table name; query filters the rows to update; body is marshalled to JSON.
func Patch(table string, query string, body interface{}) error {
	supabaseURL := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")
	url := fmt.Sprintf("%s/rest/v1/%s?%s", supabaseURL, table, query)

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
	req.Header.Set("Prefer", "return=minimal") // avoid fetching the updated row

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("supabase PATCH error on %s: %s", table, string(b))
	}
	return nil
}

// Contains reports whether str appears in arr.
func Contains(arr []interface{}, str string) bool {
	for _, v := range arr {
		if v == str {
			return true
		}
	}
	return false
}
