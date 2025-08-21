// Copyright (c) 2025 Heemeng Foo
// SPDX-License-Identifier: BUSL-1.1
// See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

import React from 'react';

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

interface UnifiedResultsDisplayProps {
  retrievedContexts: RetrievedContext[];
  relevantTickets?: RelevantTicket[]; // Made optional since it's redundant
}

// Helper function to detect result type
const getResultType = (context: RetrievedContext) => {
  if (context.source?.includes('web') || context.source?.includes('tavily')) {
    return 'web';
  }
  if (context.source === 'bugs' || context.source === 'pcr') {
    return 'jira';
  }
  return 'unknown';
};

// Helper function to get source icon
const getSourceIcon = (type: string) => {
  switch (type) {
    case 'web':
      return (
        <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM4.332 8.027a6.012 6.012 0 011.912-2.706C6.512 5.73 6.974 6 7.5 6A1.5 1.5 0 019 7.5V8a2 2 0 004 0 2 2 0 011.523-1.943A5.977 5.977 0 0116 10c0 .34-.028.675-.083 1H15a2 2 0 00-2 2v2.197A5.973 5.973 0 0110 16v-2a2 2 0 00-2-2 2 2 0 01-2-2 2 2 0 00-1.668-1.973z" clipRule="evenodd" />
        </svg>
      );
    case 'jira':
      return (
        <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm2 6a2 2 0 104 0 2 2 0 00-4 0zm6 0a2 2 0 104 0 2 2 0 00-4 0z" clipRule="evenodd" />
        </svg>
      );
    default:
      return (
        <svg className="w-4 h-4 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
      );
  }
};

// Helper function to get source label and badge color
const getSourceInfo = (type: string) => {
  switch (type) {
    case 'web':
      return { label: 'Web Search', bgColor: 'bg-blue-100', textColor: 'text-blue-800', borderColor: 'border-blue-200' };
    case 'jira':
      return { label: 'JIRA Ticket', bgColor: 'bg-green-100', textColor: 'text-green-800', borderColor: 'border-green-200' };
    default:
      return { label: 'Unknown', bgColor: 'bg-gray-100', textColor: 'text-gray-800', borderColor: 'border-gray-200' };
  }
};

// Component for displaying individual context result
const ContextResult: React.FC<{ context: RetrievedContext; index: number }> = ({ context, index }) => {
  const resultType = getResultType(context);
  const sourceInfo = getSourceInfo(resultType);
  const icon = getSourceIcon(resultType);

  return (
    <div className={`border ${sourceInfo.borderColor} rounded-lg p-4 hover:shadow-md transition-shadow duration-200`}>
      {/* Header with source info */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {icon}
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${sourceInfo.bgColor} ${sourceInfo.textColor}`}>
            {sourceInfo.label}
          </span>
          {context.score && (
            <span className="text-xs text-gray-500">
              Score: {(context.score * 100).toFixed(1)}%
            </span>
          )}
        </div>
        <span className="text-xs text-gray-400">#{index + 1}</span>
      </div>

      {/* Title (for web results) */}
      {resultType === 'web' && context.metadata?.title && (
        <h4 className="font-semibold text-gray-900 mb-2 line-clamp-2">
          {context.metadata.title}
        </h4>
      )}

      {/* Content */}
      <div className="text-sm text-gray-700 mb-3">
        <div className="line-clamp-4 whitespace-pre-line">
          {context.content.length > 300 
            ? `${context.content.substring(0, 300)}...` 
            : context.content}
        </div>
      </div>

      {/* Footer with source-specific info */}
      <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-100">
        {resultType === 'web' ? (
          <>
            <div className="flex items-center space-x-4">
              {context.metadata?.url && (
                <a
                  href={context.metadata.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 flex items-center space-x-1"
                >
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                    <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                  </svg>
                  <span className="truncate max-w-xs">
                    {new URL(context.metadata.url).hostname}
                  </span>
                </a>
              )}
              {context.metadata?.timestamp && (
                <span>
                  {new Date(context.metadata.timestamp).toLocaleString()}
                </span>
              )}
            </div>
            <span className="text-gray-400">
              {context.metadata?.source || 'Web'}
            </span>
          </>
        ) : (
          <>
            <div className="flex items-center space-x-4">
              {context.metadata?.key && (
                <span className="font-medium text-gray-700">
                  {context.metadata.key}
                </span>
              )}
              {context.metadata?.title && (
                <span className="truncate max-w-xs">
                  {context.metadata.title}
                </span>
              )}
            </div>
            <span className="text-gray-400">
              {context.source}
            </span>
          </>
        )}
      </div>
    </div>
  );
};

// Main component
export const UnifiedResultsDisplay: React.FC<UnifiedResultsDisplayProps> = ({
  retrievedContexts,
  relevantTickets
}) => {
  // Sort results by score in descending order (highest score first)
  const sortedContexts = [...retrievedContexts].sort((a, b) => {
    const scoreA = a.score || 0;
    const scoreB = b.score || 0;
    return scoreB - scoreA;
  });

  // Count different result types
  const webResults = sortedContexts.filter(ctx => getResultType(ctx) === 'web');
  const jiraResults = sortedContexts.filter(ctx => getResultType(ctx) === 'jira');
  const hasResults = sortedContexts.length > 0;

  if (!hasResults) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Results Summary */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">
          Search Results Summary
        </h3>
        <div className="flex flex-wrap gap-4 text-sm">
          {webResults.length > 0 && (
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-gray-700">
                {webResults.length} Web Result{webResults.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}
          {jiraResults.length > 0 && (
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-gray-700">
                {jiraResults.length} JIRA Result{jiraResults.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Retrieved Contexts */}
      {sortedContexts.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800">
              Retrieved Results ({sortedContexts.length})
              <span className="text-sm font-normal text-gray-500 ml-2">
                (sorted by relevance)
              </span>
            </h3>
          </div>
          <div className="p-6 space-y-4">
            {sortedContexts.map((context, index) => (
              <ContextResult 
                key={index} 
                context={context} 
                index={index}
              />
            ))}
          </div>
        </div>
      )}

    </div>
  );
};