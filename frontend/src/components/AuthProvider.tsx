// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import Cookies from 'js-cookie';
import { 
  User, 
  UserUsage, 
  AuthResponse, 
  authenticateWithGoogle, 
  getCurrentUser, 
  getUserUsage 
} from '../lib/auth';
import { 
  initializeGoogleAuth, 
  parseGoogleCredential,
  signOutGoogle 
} from '../lib/google-auth';

interface AuthContextType {
  user: User | null;
  usage: UserUsage | null;
  token: string | null;
  loading: boolean;
  login: (googleToken: string) => Promise<void>;
  logout: () => void;
  refreshUsage: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [usage, setUsage] = useState<UserUsage | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize Google Auth and check for existing session
  useEffect(() => {
    const initAuth = async () => {
      try {
        // Initialize Google OAuth
        await initializeGoogleAuth();
        
        // Set up global callback for Google Sign-In
        window.handleGoogleSignIn = async (response: any) => {
          try {
            console.log('Google sign-in response received:', response);
            console.log('Credential length:', response.credential?.length);
            await login(response.credential);
            console.log('Login completed successfully');
          } catch (error) {
            console.error('Google sign-in failed:', error);
            console.error('Error details:', error);
            alert(`Login failed: ${error instanceof Error ? error.message : String(error)}`);
            setLoading(false); // Ensure loading stops on error
          }
        };
        
        // Check for existing token
        const existingToken = Cookies.get('auth_token');
        if (existingToken) {
          try {
            const userData = await getCurrentUser(existingToken);
            const usageData = await getUserUsage(existingToken);
            setUser(userData);
            setUsage(usageData);
            setToken(existingToken);
          } catch (error) {
            // Token is invalid, remove it
            Cookies.remove('auth_token');
          }
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (googleToken: string) => {
    try {
      console.log('Starting login process...');
      console.log('Google token received, length:', googleToken?.length);
      setLoading(true);
      
      console.log('Calling authenticateWithGoogle...');
      const authResponse: AuthResponse = await authenticateWithGoogle(googleToken);
      console.log('Auth response received:', authResponse);
      console.log('User email:', authResponse.user?.email);
      
      setUser(authResponse.user);
      setUsage(authResponse.usage);
      setToken(authResponse.access_token);
      
      // Store JWT token in secure cookie
      const isProduction = window.location.protocol === 'https:';
      Cookies.set('auth_token', authResponse.access_token, { 
        secure: isProduction, // Secure in production (HTTPS)
        sameSite: 'lax',
        expires: 1 // 1 day
      });
      
      console.log('Login process completed');
      
      // Redirect to success page
      window.location.href = '/auth-success';
      
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      console.log('Setting loading to false');
      setLoading(false);
    }
  };

  const logout = () => {
    // Remove token
    Cookies.remove('auth_token');
    
    // Clear state
    setUser(null);
    setUsage(null);
    setToken(null);
    
    // Sign out from Google
    signOutGoogle();
  };

  const refreshUsage = async () => {
    if (!token) return;
    
    try {
      const usageData = await getUserUsage(token);
      setUsage(usageData);
    } catch (error) {
      console.error('Failed to refresh usage:', error);
    }
  };

  const contextValue: AuthContextType = {
    user,
    usage,
    token,
    loading,
    login,
    logout,
    refreshUsage
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}