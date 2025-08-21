// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"use client";
import React from "react";
import { AuthProvider, useAuth } from '../../components/AuthProvider';
import Link from 'next/link';

function AuthSuccessContent() {
  const { user, usage } = useAuth();

  if (!user) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Authentication required</p>
          <Link href="/" className="text-blue-600 hover:text-blue-800">
            Return to login
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full mx-4 text-center">
        {/* Cuttlefish Logo */}
        <img
          src="/Cuttlefish3.png"
          alt="Cuttlefish3 logo"
          className="mx-auto mb-6 object-contain drop-shadow-md"
          style={{ width: '252px', height: '84px' }}
        />
        
        {/* Success Message */}
        <div className="mb-6">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">
            Login Successful!
          </h1>
          <p className="text-gray-600">
            Welcome, {user.display_name || user.email}
          </p>
        </div>

        {/* User Info */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6 text-left">
          <h3 className="font-semibold text-gray-800 mb-2">Account Details</h3>
          <div className="text-sm space-y-1">
            <div>
              <span className="font-medium">Email:</span> {user.email}
            </div>
            {usage && (
              <>
                <div>
                  <span className="font-medium">Daily Limit:</span> {usage.unlimited_access ? "Unlimited" : usage.daily_limit}
                </div>
                <div>
                  <span className="font-medium">Requests Used:</span> {usage.requests_used}
                </div>
                <div>
                  <span className="font-medium">Remaining:</span> {usage.unlimited_access ? "Unlimited" : usage.requests_remaining}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Continue to App */}
        <Link 
          href="/app"
          className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg px-6 py-3 font-semibold hover:from-blue-700 hover:to-blue-800 transition-all duration-200 shadow-md hover:shadow-lg inline-block"
        >
          Continue to Cuttlefish App
        </Link>
        
        {/* Debug Info */}
        <div className="mt-4 text-xs text-gray-500">
          Auth Status: Connected | Backend: Running
        </div>
      </div>
    </main>
  );
}

export default function AuthSuccess() {
  return (
    <AuthProvider>
      <AuthSuccessContent />
    </AuthProvider>
  );
}