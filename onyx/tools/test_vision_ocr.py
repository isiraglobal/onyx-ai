import os
import io
from pypdf import PdfReader
import Vision
import Quartz
from Cocoa import NSURL

def ocr_image_bytes(img_bytes):
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
        return f"Error: {error}"
        
    results = req.results()
    text_lines = []
    for obs in results:
        top_cand = obs.topCandidates_(1)
        if top_cand:
            text_lines.append(top_cand[0].string())
    return "\n".join(text_lines)

# Test on page 10 of High Ticket Closing
reader = PdfReader("/Users/lakshitsinghvi/Documents/Onyx/Training Data/high ticket closing black book 2nd edition .pdf")
for page_num in [5, 10, 15]:
    page = reader.pages[page_num]
    print(f"\n--- PAGE {page_num + 1} ---")
    for img_name, img_obj in page.images.items():
        ocr_result = ocr_image_bytes(img_obj.data)
        if ocr_result.strip():
            print(f"[{img_name}]:\n{ocr_result[:400]}...\n")
