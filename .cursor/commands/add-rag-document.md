# Add RAG Knowledge Document

## Purpose
Adds a new document to the RAG (Retrieval-Augmented Generation) knowledge base so agents can reference it when making decisions.

## Usage
`/add-rag-document [file-path] [category]`

Example: `/add-rag-document manuals/hvac-manual.pdf climate`

## Instructions for Agent

When this command is invoked:

1. **Validate Document**:
   - Check if file exists and is readable
   - Verify file type is supported (PDF, TXT, MD, DOCX)
   - Check file size is reasonable (<50MB)

2. **Prepare Document Metadata**:
   - Extract title from filename or content
   - Assign category (climate, security, lighting, energy, general)
   - Add timestamp and source information

3. **Process Document**:
   - For PDFs: Extract text content
   - For text files: Read directly
   - Split into appropriate chunks (500-1000 tokens)
   - Maintain context between chunks

4. **Add to Knowledge Base**:
   - Use the RAG manager to ingest document
   - Generate embeddings using nomic-embed-text
   - Store in ChromaDB vector database
   - Update document index

5. **Verify Ingestion**:
   - Query the knowledge base for test content
   - Confirm document is retrievable
   - Check embedding quality

6. **Update Documentation**:
   - Log the addition in knowledge base inventory
   - Note which agents will benefit from this document

## Expected Outcome
- Document successfully added to RAG knowledge base
- Confirmation message with document ID
- Retrieval test shows document is queryable
- Agents can now reference this information

## Technical Details

The RAG system uses:
- **Embeddings**: nomic-embed-text model
- **Vector DB**: ChromaDB (local)
- **Chunk size**: 500-1000 tokens with overlap
- **Retrieval**: Top-k semantic search (k=5)

## Example Use Cases

1. **HVAC Manual**: Add manufacturer specifications
2. **House Rules**: "Don't run dishwasher if Clean sign is flipped"
3. **Device Guides**: Smart device documentation
4. **Energy Policies**: Time-of-use rate schedules
5. **Security Protocols**: When to notify, when to act
