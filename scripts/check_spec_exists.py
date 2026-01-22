import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from rag_app.db import document_exists, get_all_documents

spec_file = "SPECIFICATION.md"
exists = document_exists(spec_file)

print(f"Document '{spec_file}' exists in DB: {exists}")

if exists:
    print("Found in index.")
else:
    print("Not found in index.")
    
# List all sources just in case
print("\n=== All Sources ===")
docs = get_all_documents()
for d in docs:
    print(f"- {d.get('source')} ({d.get('title')})")
