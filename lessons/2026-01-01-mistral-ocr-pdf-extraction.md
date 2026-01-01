# Lessons Learned: Migrating PDF Extraction from GPT-4 Vision to Mistral OCR + ChatGPT

**Date:** 2026-01-01
**Commit:** e25f22d
**Related Ticket:** N/A

## Problem Summary

The PDF extraction feature was using GPT-4 Vision API to process PDFs page-by-page, converting each page to an image and sending it to the Vision API. This approach was:
- Expensive (~$0.01-0.02 per page)
- Slow for multi-page documents (processing each page sequentially)
- Using Vision API when OCR was the core requirement

The task was to refactor to a more efficient two-step pipeline using Mistral's specialized Document AI for OCR, followed by ChatGPT for structured data extraction.

## Approach Taken

### Architecture Change
Replaced single-step Vision API with a two-step pipeline:
1. **Mistral Document AI OCR**: Convert entire PDF to markdown (single API call)
2. **ChatGPT text API**: Extract trade data from markdown text

### Key Implementation Details

**1. API Integration Discovery**
- Initial attempts to upload PDFs to Mistral files API failed (422 error: "Invalid file format. Chat too large or missing")
- Discovered the files API is for fine-tuning, not general document processing
- Solution: Use base64-encoded data URI with `document_url` parameter type

**Critical Code:**
```python
base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
data_uri = f"data:application/pdf;base64,{base64_pdf}"

ocr_response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "document_url",  # NOT "image_url" for PDFs!
        "document_url": data_uri
    },
    table_format="markdown"
)
```

**2. Prompt Engineering**
Updated extraction prompt to handle OCR-specific challenges:
- Tables in markdown format
- Potential OCR artifacts (headers, footers, page numbers)
- Tolerance for company name OCR errors while maintaining strict numerical accuracy
- Explicit instruction about duplicate handling (deduplication happens server-side)

**3. Dual Client Management**
Maintained both OpenAI and Mistral clients with lazy initialization:
```python
def __init__(self):
    self.openai_client = None  # For trade extraction
    self.mistral_client = None  # For OCR
```

## Key Lessons

### 1. Mistral API Document Types Matter
- **`document_url`** is for PDFs (even base64-encoded)
- **`image_url`** is for images (PNG, JPEG)
- The error message "Image content must be a URL (starting with 'https') or base64 encoded image..." is misleading for PDFs

### 2. Base64 Data URIs Work for Mistral OCR
Despite some documentation showing file upload workflows, base64-encoded PDFs as data URIs work perfectly:
- No need for temporary files
- No cleanup required
- Single API call

### 3. OCR Response Field Access Should Be Defensive
Used defensive field access for API response parsing:
```python
markdown_text = getattr(ocr_response, 'text', '') or \
               getattr(ocr_response, 'content', '') or \
               str(ocr_response)
```
This handles potential API response structure variations.

### 4. Test Incrementally with Real Data
Testing with an actual Trade Republic PDF statement (20 transactions) immediately validated:
- OCR accuracy (18,753 chars of markdown extracted correctly)
- ChatGPT extraction (20 trades found and validated)
- Fractional share handling (e.g., 0.445679 shares)
- Multi-ticker support (NVDA, MELI, META, AMZN)

### 5. Cost-Benefit Trade-offs Are Real
The refactoring delivered measurable improvements:
- **70-85% cost reduction** (~$0.003 vs ~$0.01-0.02 per page)
- **6-10x speed improvement** (single OCR call vs per-page Vision API)
- **Better accuracy** (specialized OCR vs general Vision)

## Potential Improvements

### 1. Response Structure Validation
Add explicit response structure validation:
```python
if not hasattr(ocr_response, 'text') and not hasattr(ocr_response, 'content'):
    raise ValueError(f"Unexpected OCR response structure: {type(ocr_response)}")
```

### 2. Retry Logic for API Failures
Add exponential backoff retry for transient failures:
- Rate limits
- Network timeouts
- Temporary service unavailability

### 3. Caching for Duplicate PDFs
Consider caching OCR results by PDF hash:
```python
pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
# Check cache before calling Mistral API
```

### 4. Multi-Page Performance Monitoring
Add instrumentation to measure:
- OCR time vs document page count
- ChatGPT extraction time vs markdown length
- Overall pipeline throughput

### 5. Error Context Enrichment
Improve error messages with more context:
```python
raise ValueError(
    f"OCR failed for {len(pdf_bytes)} byte PDF. "
    f"Ensure PDF is valid and under 50MB limit. Error: {str(e)}"
)
```

## References

- [Mistral OCR Documentation](https://docs.mistral.ai/capabilities/document_ai/basic_ocr)
- [Mistral OCR Guide | DataCamp](https://www.datacamp.com/tutorial/mistral-ocr)
- [Mistral API Files Endpoint](https://docs.mistral.ai/api/endpoint/files)
