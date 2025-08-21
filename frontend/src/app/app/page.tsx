// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"use client";
import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { AuthProvider, useAuth } from '../../components/AuthProvider';
import { makeAuthenticatedRequest } from '../../lib/auth';
import Link from 'next/link';
import { UnifiedResultsDisplay } from '../../components/UnifiedResultsDisplay';

// Use environment variable for API URL, fallback to localhost for local dev
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type RetrievedContext = {
  content: string;
  metadata: { [key: string]: any };
  source: string;
  score: number;
};

type RelevantTicket = {
  key: string;
  title: string;
};

type RetrievalMetadata = {
  agent: string;
  num_results: number;
  processing_time: number;
  method_type: string;
  bm25_available?: boolean;
  is_urgent?: boolean;
  methods_used?: string[];
  primary_source?: string;
  source?: string;
  content_filtered?: boolean;
};

type MultiAgentResponse = {
  query: string;
  final_answer: string;
  relevant_tickets: RelevantTicket[];
  routing_decision: string;
  routing_reasoning: string;
  retrieval_method: string;
  retrieved_contexts: RetrievedContext[];
  retrieval_metadata: RetrievalMetadata;
  user_can_wait: boolean;
  production_incident: boolean;
  messages: Array<{ content: string; type: string }>;
  timestamp: string;
  total_processing_time?: number;
};

const SAMPLE_QUESTIONS = `# Sample Questions for Cuttlefish3

This document provides sample questions that users can ask the Cuttlefish3 system, organized by use case categories. These questions are based on the actual JIRA data patterns and the use cases identified in the Cuttlefish3.md analysis.

## Technical Troubleshooting Questions

### Memory and Performance Issues
- "How do I fix OutOfMemoryError: GC overhead limit exceeded in Eclipse?"
- "What causes memory leaks when scanning multiple XML documents?"
- "How to resolve performance issues with BeanUtils.copyProperties()?"
- "What are common causes of OutOfMemoryError in JBoss Tools?"
- "How do I fix memory issues with XStream marshalling?"

### Framework-Specific Issues

#### Spring Framework
- "How do I fix ClassCastException issues with SAXParserFactory?"
- "What causes 'XStream marshalling ended with exception' errors?"
- "How to resolve ServletTestExecutionListener breaking old code?"
- "What causes BeanFactory.getBeanNamesForAnnotation() issues?"
- "How do I fix GenericTypeAwarePropertyDescriptor problems?"
- "What causes XStreamMarshaller converterRegistry field to be null?"
- "How to resolve EhCacheFactoryBean race conditions?"
- "What causes ControllerAdvice annotation not being found?"

#### HBase Issues
- "How do I fix Region Server connection issues?"
- "What causes HBase Master recovery failures?"
- "How to resolve HBase table creation errors?"
- "What causes 'Region is being opened' exceptions?"
- "How do I fix HBase compaction failures?"
- "What causes HBase split transaction errors?"`;

function CuttlefishAppContent() {
  const { user, usage, token, logout, refreshUsage } = useAuth();
  const [activeTab, setActiveTab] = useState<"query" | "reference">("query");
  const [query, setQuery] = useState("");
  const [userCanWait, setUserCanWait] = useState(true);
  const [productionIncident, setProductionIncident] = useState(false);
  const [result, setResult] = useState<MultiAgentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect to auth if not logged in
  if (!user) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Authentication required</p>
          <Link href="/" className="text-blue-600 hover:text-blue-800">
            Please login first
          </Link>
        </div>
      </main>
    );
  }

  const handleSubmit = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const res = await makeAuthenticatedRequest('/multiagent-rag', token!, {
        method: "POST",
        body: JSON.stringify({ 
          query: query.trim(),
          user_can_wait: userCanWait,
          production_incident: productionIncident
        }),
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || err.error || "Request failed");
      }
      
      const data = await res.json();
      
      // Response is already in the correct MultiAgentResponse format
      setResult(data);
      await refreshUsage();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Request failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleSubmit();
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header with User Info */}
        <div className="text-center mb-8">
          <img
            src="/Cuttlefish4.png"
            alt="Cuttlefish4 logo"
            className="mx-auto mb-6 object-contain drop-shadow-md"
            style={{ width: '504px', height: '168px' }}
          />
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Cuttlefish 4
          </h1>
          <p className="text-xl text-gray-600 mb-4">
            Multi-Agent RAG System for JIRA Tickets & Real-Time Web Search
          </p>
          
          {/* User Status Bar */}
          <div className="bg-white rounded-lg shadow-sm p-4 max-w-2xl mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-sm">
                <span className="font-medium text-gray-700">User:</span> {user.display_name || user.email}
              </div>
              {usage && (
                <div className="text-sm">
                  <span className="font-medium text-gray-700">Requests:</span> 
                  <span className={usage.unlimited_access ? "text-green-600" : "text-blue-600"}>
                    {usage.unlimited_access ? " Unlimited" : ` ${usage.requests_used}/${usage.daily_limit}`}
                  </span>
                </div>
              )}
            </div>
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab("query")}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                  activeTab === "query"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                Query
              </button>
              <button
                onClick={() => setActiveTab("reference")}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                  activeTab === "reference"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                Reference Queries
              </button>
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        <div className="max-w-4xl mx-auto">
          {activeTab === "query" ? (
            <div className="bg-white rounded-xl shadow-lg p-8">
              {/* Toggle Switches */}
              <div className="mb-8 flex flex-wrap gap-6">
                <div className="flex items-center space-x-3">
                  <span className="text-sm font-medium text-gray-700">
                    Not Urgent
                  </span>
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={userCanWait}
                      onChange={(e) => setUserCanWait(e.target.checked)}
                    />
                    <span className="slider"></span>
                  </label>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="text-sm font-medium text-gray-700">
                    Production Issue
                  </span>
                  <label className="toggle toggle-urgent">
                    <input
                      type="checkbox"
                      checked={productionIncident}
                      onChange={(e) => setProductionIncident(e.target.checked)}
                    />
                    <span className="slider"></span>
                  </label>
                </div>
              </div>

              {/* Query Input */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Query
                </label>
                <textarea
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 min-h-[120px] focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 resize-vertical text-gray-900"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Enter your query here (JIRA tickets, service status, or general questions)... (Cmd/Ctrl + Enter to submit)"
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Tip: Use Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux) to submit
                </p>
              </div>

              {/* Submit Button */}
              <button
                className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg px-6 py-3 font-semibold hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg"
                onClick={handleSubmit}
                disabled={loading || !query.trim()}
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Processing...
                  </div>
                ) : (
                  "Search & Analyze"
                )}
              </button>

              {/* Error Display */}
              {error && (
                <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">Error</h3>
                      <div className="mt-1 text-sm text-red-700">{error}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Results Display */}
              {result && (
                <div className="mt-8 space-y-6">
                  {/* Answer Section */}
                  <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-green-800 mb-3">
                      Answer
                    </h3>
                    <div className="text-gray-800 whitespace-pre-line leading-relaxed">
                      {result.final_answer}
                    </div>
                  </div>

                  {/* Unified Results Display */}
                  <UnifiedResultsDisplay 
                    retrievedContexts={result.retrieved_contexts || []}
                    relevantTickets={result.relevant_tickets || []}
                  />

                  {/* Metadata Section */}
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-gray-800 mb-4">
                      Query Metadata
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-600">Routing Decision:</span>
                        <span className="ml-2 text-gray-800">{result.routing_decision}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-600">Retrieval Method:</span>
                        <span className="ml-2 text-gray-800">{result.retrieval_method}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-600">Processing Time:</span>
                        <span className="ml-2 text-gray-800">{result.total_processing_time?.toFixed(2)}s</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-600">Results Found:</span>
                        <span className="ml-2 text-gray-800">{result.retrieval_metadata.num_results}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-600">User Can Wait:</span>
                        <span className="ml-2 text-gray-800">{result.user_can_wait ? "Yes" : "No"}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-600">Production Incident:</span>
                        <span className="ml-2 text-gray-800">{result.production_incident ? "Yes" : "No"}</span>
                      </div>
                    </div>
                    
                    {/* Routing Reasoning */}
                    {result.routing_reasoning && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <span className="font-medium text-gray-600">Routing Reasoning:</span>
                        <div className="mt-2 text-sm text-gray-700 italic">
                          {result.routing_reasoning}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-8 py-6">
                <h2 className="text-2xl font-bold text-white">Reference Queries</h2>
                <p className="text-blue-100 mt-1">Sample questions organized by category to help you get started</p>
              </div>
              <div className="p-8">
                <div className="prose prose-lg max-w-none prose-headings:text-gray-800 prose-h1:text-3xl prose-h1:font-bold prose-h1:mb-6 prose-h1:pb-3 prose-h1:border-b prose-h1:border-gray-200 prose-h2:text-2xl prose-h2:font-semibold prose-h2:mt-8 prose-h2:mb-4 prose-h2:text-blue-800 prose-h3:text-xl prose-h3:font-medium prose-h3:mt-6 prose-h3:mb-3 prose-h3:text-blue-700 prose-h4:text-lg prose-h4:font-medium prose-h4:mt-4 prose-h4:mb-2 prose-h4:text-blue-600 prose-p:text-gray-700 prose-p:leading-relaxed prose-ul:space-y-1 prose-li:text-gray-700 prose-strong:text-gray-800 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono">
                  <ReactMarkdown
                    components={{
                      h1: ({ children }) => (
                        <h1 className="text-3xl font-bold mb-6 pb-3 border-b border-gray-200 text-gray-800">
                          {children}
                        </h1>
                      ),
                      h2: ({ children }) => (
                        <h2 className="text-2xl font-semibold mt-8 mb-4 text-blue-800 border-l-4 border-blue-500 pl-4">
                          {children}
                        </h2>
                      ),
                      h3: ({ children }) => (
                        <h3 className="text-xl font-medium mt-6 mb-3 text-blue-700">
                          {children}
                        </h3>
                      ),
                      h4: ({ children }) => (
                        <h4 className="text-lg font-medium mt-4 mb-2 text-blue-600">
                          {children}
                        </h4>
                      ),
                      ul: ({ children }) => (
                        <ul className="space-y-2 ml-4">
                          {children}
                        </ul>
                      ),
                      li: ({ children }) => (
                        <li className="text-gray-700 flex items-start">
                          <span className="text-blue-500 mr-2 mt-1.5 flex-shrink-0">•</span>
                          <span className="hover:text-blue-800 transition-colors cursor-pointer">
                            {children}
                          </span>
                        </li>
                      ),
                      p: ({ children }) => (
                        <p className="text-gray-700 leading-relaxed mb-4">
                          {children}
                        </p>
                      ),
                      code: ({ children }) => (
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800">
                          {children}
                        </code>
                      ),
                    }}
                  >
                    {SAMPLE_QUESTIONS}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

export default function CuttlefishApp() {
  return (
    <AuthProvider>
      <CuttlefishAppContent />
    </AuthProvider>
  );
}