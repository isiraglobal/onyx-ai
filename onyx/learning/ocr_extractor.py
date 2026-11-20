"""High-performance document and image OCR extraction using Apple Vision."""

import io
import json
import os
from pathlib import Path
import time
from typing import Dict, List, Tuple, Any
from pypdf import PdfReader
import Vision
import Quartz


def ocr_image_bytes(img_bytes: bytes) -> str:
    """Run Apple Vision text recognition on raw image bytes."""
    if not img_bytes:
        return ""
    data_provider = Quartz.CGDataProviderCreateWithData(None, img_bytes, len(img_bytes), None)
    if not data_provider:
        return ""
    cg_image = Quartz.CGImageCreateWithJPEGDataProvider(data_provider, None, True, Quartz.kCGRenderingIntentDefault)
    if not cg_image:
        cg_image = Quartz.CGImageCreateWithPNGDataProvider(data_provider, None, True, Quartz.kCGRenderingIntentDefault)
    if not cg_image:
        return ""

    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(True)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
    success, error = handler.performRequests_error_([req], None)
    if not success:
        return ""

    results = req.results()
    if not results:
        return ""

    lines = []
    for obs in results:
        cands = obs.topCandidates_(1)
        if cands:
            lines.append(cands[0].string())
    return "\n".join(lines)


def process_book_100m(pdf_path: str, output_file: str) -> Dict[str, Any]:
    """Extract all text and image annotations from Your First 100 Million."""
    print(f"--> Processing: {os.path.basename(pdf_path)}")
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    extracted_pages = []
    total_chars = 0
    start_time = time.time()

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        page_text = (page.extract_text() or "").strip()

        # If page text is very short or page has key images, check image text
        image_texts = []
        if len(page_text) < 100 or "illustration" in page_text.lower():
            for img_name, img_obj in page.images.items():
                # Avoid tiny icons
                if len(img_obj.data) > 15000:
                    ocr_t = ocr_image_bytes(img_obj.data)
                    if ocr_t.strip():
                        image_texts.append(f"[IMAGE TEXT]: {ocr_t.strip()}")

        combined = page_text
        if image_texts:
            combined += "\n" + "\n".join(image_texts)

        if combined.strip():
            extracted_pages.append(f"=== PAGE {page_num} ===\n{combined.strip()}\n")
            total_chars += len(combined)

        if page_num % 50 == 0 or page_num == total_pages:
            print(f"  [100M] Processed page {page_num}/{total_pages} ({round((page_num/total_pages)*100, 1)}%)")

    full_content = "\n".join(extracted_pages)
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(full_content, encoding="utf-8")

    elapsed = round(time.time() - start_time, 2)
    return {
        "title": "Your First 100 Million",
        "author": "Quantum Leap Advantage",
        "pages": total_pages,
        "extracted_pages": len(extracted_pages),
        "total_chars": total_chars,
        "elapsed_seconds": elapsed,
        "output_file": output_file,
    }


def process_book_htc(pdf_path: str, output_file: str) -> Dict[str, Any]:
    """Extract all pages from High Ticket Closing Black Book via Apple Vision OCR."""
    print(f"--> Processing: {os.path.basename(pdf_path)}")
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    extracted_pages = []
    total_chars = 0
    start_time = time.time()

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        page_ocr_lines = []

        # Each page is scanned as an image
        for img_name, img_obj in page.images.items():
            if len(img_obj.data) > 20000:  # Full page scan
                t = ocr_image_bytes(img_obj.data)
                # Filter out raw CamScanner header/footer line
                clean_lines = [l for l in t.split("\n") if "Scanned by CamScanner" not in l and l.strip() != "CamScanner"]
                if clean_lines:
                    page_ocr_lines.append("\n".join(clean_lines))

        ocr_content = "\n".join(page_ocr_lines).strip()
        if ocr_content:
            extracted_pages.append(f"=== PAGE {page_num} ===\n{ocr_content}\n")
            total_chars += len(ocr_content)

        if page_num % 25 == 0 or page_num == total_pages:
            print(f"  [HTC] OCR processed page {page_num}/{total_pages} ({round((page_num/total_pages)*100, 1)}%) - Chars: {total_chars}")

    full_content = "\n".join(extracted_pages)
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(full_content, encoding="utf-8")

    elapsed = round(time.time() - start_time, 2)
    return {
        "title": "High Ticket Closing Black Book",
        "author": "Dan Lok",
        "pages": total_pages,
        "extracted_pages": len(extracted_pages),
        "total_chars": total_chars,
        "elapsed_seconds": elapsed,
        "output_file": output_file,
    }


if __name__ == "__main__":
    b1 = "/Users/lakshitsinghvi/Documents/Onyx/Training Data/Your First 100 Million 2nd Edtion.pdf"
    b2 = "/Users/lakshitsinghvi/Documents/Onyx/Training Data/high ticket closing black book 2nd edition .pdf"
    
    out1 = "data/learning/extracted_books/your_first_100_million.txt"
    out2 = "data/learning/extracted_books/high_ticket_closing.txt"

    res1 = process_book_100m(b1, out1)
    res2 = process_book_htc(b2, out2)

    summary = {"books": [res1, res2], "timestamp": time.time()}
    Path("data/learning/extracted_books/extraction_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n✓ Both books successfully extracted and OCR'd!")
    print(json.dumps(summary, indent=2))
