// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
  },
  images: {
    domains: ['lh3.googleusercontent.com'], // For Google profile pictures
  },
};

module.exports = nextConfig;