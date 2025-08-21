# Cuttlefish4 Requirements

## Background

In Phase 1 and 2 of the Cuttlefish4 build we did the following:

### Phase 1

Convert the Cuttlefish3 Jupyter notebook (Flask) to FastAPI with proper folder structure. Requirements are in `ClaudeCodePromptCuttlefishReorg.md` and then to update the Cuttlefish3 UI to integrate with the new Cuttlefish4 endpoints

### Phase 2

Add Google OAuth and JWT token auth between the FE and BE so that there is no unauthorized access to the API (and hence token cost)

## This phase of the work

I break up this phase of the work into the following 2 phases:

**Phase 3**

Adding a WebSearch tool and refine the Supervisor agent to farm out to the Web Search Agent where appropriate
 
**Phase 4**

Adding a Log Search tool and refine the Supervisor agent to farm out to the Log Search Agent where appropriate

**Phase 5**

Refine the Supervisor agent

### Phase 3

Use `references/Multi_Agent_RAG_LangGraph.ipynb` as reference to build a WebSearch Agent. 

You should first build a tavily tool like how the notebook has built it. It should be in the `app/tools` folder and write a simple test to test that it works. 

The WebSearch agent should use a 4o model to assess the user query and perform multiple refined searches as needed (up to a maximum number - use a variable for this but set it initially to 5). It could search for status pages and downdetector for production issues and other sites for deeper research into issues in conjuction with the RAG search

### Phase 4

Use `references/scalyr_alternatives_analysis.pdf` as reference to build a LogSearch Agent. This is just to be used as a reference as the design pattern should follow that of the WebSearch agent.

You should first build a Splunk tool (or search to see if one is already available as open source or is provided free) and write a simple test to test that it works like what we did for the search tool. This tool should be stored in the `api/tools` folder. 

Next build a simple random log generator script to feed into the Splunk instance. Limit the log generation to 20Mb each time it is run. Make this limit configurable for testing. The logs should be synthesized normal Java logs with small number (0.1%) of random issues like:

1. Java Exceptions due to certificate expiry
2. Java Exceptions due to 5xx errors
3. Java Exceptions due to disk space exceeded
4. Java Exceptions due to dead letter queue exceeded 

The LogSearch agent should use a 'mini' model to assess the user query and perform the log search and assess if multiple refined searches will be needed (up to a maximum number initially set at 5). If the query is a production incident it should search for the types of log entries mentioned above.

  