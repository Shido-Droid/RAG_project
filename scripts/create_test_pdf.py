import sys
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
except ImportError:
    print("Error: reportlab is not installed.")
    print("Please install it using: pip install reportlab")
    sys.exit(1)

def create_test_pdf(filename="test_rag_doc.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Add Outline (Bookmark)
    c.bookmarkPage("page1")
    c.addOutlineEntry("1. Introduction", "page1", level=0)

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "RAG System Test Document")
    
    # Content
    c.setFont("Helvetica", 12)
    text = [
        "This is a test PDF generated for the RAG system.",
        "It contains sample text to verify the upload and text extraction features.",
        "",
        "1. Upload Functionality: The file should be accepted by the server.",
        "2. Text Extraction: The system should be able to read this text.",
        "3. Summarization: The AI should be able to summarize these points.",
        "",
        "If you are reading this in the RAG response, the test is successful.",
        "The system is functioning as expected.",
        "",
        "(Note: This document is in English to ensure font compatibility during generation.)"
    ]
    
    y = height - 100
    for line in text:
        c.drawString(50, y, line)
        y -= 20
    
    # Page 2
    c.showPage()
    c.bookmarkPage("page2")
    c.addOutlineEntry("2. Details", "page2", level=0)
    
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "Section 2: Details")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, "This is the second page, belonging to the 'Details' section.")
        
    c.save()
    print(f"Successfully created: {filename}")

if __name__ == "__main__":
    create_test_pdf()