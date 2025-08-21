// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from './AuthProvider';
import { renderGoogleSignInButton } from '../lib/google-auth';

export default function LoginForm() {
  const { user, usage, loading, logout } = useAuth();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    // Render Google Sign-In button when component mounts and user is not logged in
    if (mounted && !user && !loading) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        renderGoogleSignInButton('google-signin-button');
      }, 100);
    }
  }, [mounted, user, loading]);

  if (!mounted) {
    return null; // Prevent hydration mismatch
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading...</span>
      </div>
    );
  }

  if (user) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {user.profile_picture && (
              <img
                src={user.profile_picture}
                alt="Profile"
                className="w-10 h-10 rounded-full"
                onError={(e) => {
                  // Hide image if it fails to load
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            )}
            <div>
              <h3 className="font-semibold text-gray-800">
                {user.display_name || user.email}
              </h3>
              <p className="text-sm text-gray-600">{user.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Sign Out
          </button>
        </div>
        
        {/* Usage Information */}
        {usage && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Today's Usage:</span>
              <span className="font-medium text-gray-800">
                {usage.unlimited_access ? (
                  <span className="text-green-600">Unlimited</span>
                ) : (
                  `${usage.requests_used} / ${usage.daily_limit} requests`
                )}
              </span>
            </div>
            
            {!usage.unlimited_access && (
              <div className="mt-2">
                <div className="bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${
                      usage.requests_used / usage.daily_limit > 0.8
                        ? 'bg-red-500'
                        : usage.requests_used / usage.daily_limit > 0.6
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                    }`}
                    style={{
                      width: `${Math.min((usage.requests_used / usage.daily_limit) * 100, 100)}%`
                    }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {usage.requests_remaining} requests remaining
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-8 mb-6 text-center">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        Sign In Required
      </h2>
      <p className="text-gray-600 mb-6">
        Please sign in with your Google account to access the Cuttlefish4 Multi-Agent RAG system.
      </p>
      
      {/* Google Sign-In Button Container */}
      <div className="flex justify-center">
        <div id="google-signin-button"></div>
      </div>
      
      <p className="text-xs text-gray-500 mt-4">
        By signing in, you agree to our terms of service and privacy policy.
      </p>
    </div>
  );
}