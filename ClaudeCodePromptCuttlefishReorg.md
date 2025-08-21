# Objective

Reorganize Cuttlefish3 to address issues faced. They are:

1. Convert the files in `references/qdrant` QDrant code to their equivalent Suprabase format in `suprabase` folder. It should support both vector search and keyword search. There should be 2 instances with the same schema - one for 'bugs' and another for 'pcr' (release tickets)
2. Move from a Python Notebook (references/Cuttlefish3_Complete.ipynb) into properly structured code with tests
   - each Agent has its own `.py` file 
   - all the RAG retrieval functions used by the RAG agent is in a single `.py` file 
     - the BM25 retriever should use the keyword search feature of Suprabase and the other retrievers use cosine similarity (pgvector)
   - we have a single `.py` file for all the `tools` used by the Agents. Each RAG retrieval function maps to a tool
   - structure the code in sub folders: (a) `rag` for RAG retrievers (b) `tools` for tools (c) `agents` for Agents  
3. We are to convert the API from Flask to FastAPI format with the same endpoints
4. Extract all the dependencies into a `requirements.txt` file
5. All the new code are to be in the `app` folder
