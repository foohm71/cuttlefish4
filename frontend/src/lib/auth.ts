// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

/**
 * Authentication utilities for Cuttlefish4 frontend.
 */

export interface User {
  email: string;
  display_name?: string;
  profile_picture?: string;
  daily_limit: number;
  requests_used: number;
  unlimited_access: boolean;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface UserUsage {
  email: string;
  daily_limit: number;
  requests_used: number;
  requests_remaining: number;
  unlimited_access: boolean;
  last_reset_date: string;
  can_make_request: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  usage: UserUsage;
}

// API URL from environment
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/**
 * Authenticate with Google OAuth token
 */
export async function authenticateWithGoogle(googleToken: string): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/auth/google`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token: googleToken }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Authentication failed");
  }

  return response.json();
}

/**
 * Get current user information
 */
export async function getCurrentUser(token: string): Promise<User> {
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to get user info");
  }

  return response.json();
}

/**
 * Get user usage statistics
 */
export async function getUserUsage(token: string): Promise<UserUsage> {
  const response = await fetch(`${API_URL}/auth/usage`, {
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to get usage info");
  }

  return response.json();
}

/**
 * Make authenticated API request
 */
export async function makeAuthenticatedRequest(
  endpoint: string,
  token: string,
  options: RequestInit = {}
): Promise<Response> {
  return fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
}