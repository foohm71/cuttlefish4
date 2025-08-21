// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cuttlefish4 - Multi-Agent RAG System",
  description: "Intelligent JIRA ticket retrieval using multi-agent RAG system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}