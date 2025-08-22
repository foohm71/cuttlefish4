// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

/**
 * Google OAuth integration for Cuttlefish4 frontend.
 * Handles Google Sign-In and token management.
 */

declare global {
  interface Window {
    google: any;
    handleGoogleSignIn: (response: any) => void;
  }
}

export interface GoogleUser {
  email: string;
  name: string;
  picture: string;
  sub: string;
}

/**
 * Initialize Google OAuth
 */
export function initializeGoogleAuth(): Promise<void> {
  return new Promise((resolve, reject) => {
    // Load Google Identity Services script
    if (document.getElementById('google-identity-script')) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-identity-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    
    script.onload = () => {
      // Initialize Google Identity Services
      const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
      console.log('Google Client ID:', clientId);
      
      if (!clientId) {
        reject(new Error('NEXT_PUBLIC_GOOGLE_CLIENT_ID not found'));
        return;
      }
      
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: window.handleGoogleSignIn,
          auto_select: false,
          cancel_on_tap_outside: true,
          use_fedcm_for_prompt: false,
          itp_support: false
        });
        console.log('Google OAuth initialized successfully');
        console.log('Callback function defined:', typeof window.handleGoogleSignIn);
        resolve();
      } else {
        reject(new Error('Google Identity Services failed to load'));
      }
    };
    
    script.onerror = () => reject(new Error('Failed to load Google Identity Services'));
    document.head.appendChild(script);
  });
}

/**
 * Show Google Sign-In popup
 */
export function showGoogleSignIn(): void {
  if (window.google) {
    window.google.accounts.id.prompt();
  }
}

/**
 * Render Google Sign-In button
 */
export function renderGoogleSignInButton(elementId: string): void {
  if (window.google) {
    window.google.accounts.id.renderButton(
      document.getElementById(elementId),
      {
        theme: 'outline',
        size: 'large',
        type: 'standard',
        shape: 'rectangular',
        text: 'signin_with',
        logo_alignment: 'left'
      }
    );
  }
}

/**
 * Parse Google credential response
 */
export function parseGoogleCredential(credential: string): GoogleUser {
  try {
    // Decode JWT payload (note: this is not cryptographically verified on frontend)
    const base64Url = credential.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    
    return JSON.parse(jsonPayload);
  } catch (error) {
    throw new Error('Failed to parse Google credential');
  }
}

/**
 * Sign out from Google
 */
export function signOutGoogle(): void {
  if (window.google) {
    window.google.accounts.id.disableAutoSelect();
  }
}