import hashlib
import logging
import os
import re
import shutil
import uuid
from typing import Any, Dict, List, Optional, cast

import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.core.chroma import get_property_collection
from app.core.config import settings
from app.core.llm import llm_client
from app.models import sql_models

logger = logging.getLogger(__name__)


def extract_metadata(file_path: str) -> dict:
    """
    Extracts property details from the PDF using more flexible Regex.
    Should match "State: X", "State - X", "State X", case insensitive.
    """
    try:
        reader = PdfReader(file_path)
        text_parts: List[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if isinstance(page_text, str):
                text_parts.append(str(page_text))
        text = str("\n").join(text_parts)

        text_stripped = text.strip()
        if not text_stripped:
            logger.warning(
                "pypdf: PDF text seems empty. It might be an image-based PDF."
            )
        elif len(text_stripped) < 50:
            logger.warning("pypdf: PDF text is very short.")
    except Exception as e:
        logger.warning(f"pypdf failed: {e}. Trying pdfplumber fallback...")
        # Fallback: try pdfplumber which handles more corrupted PDFs
        try:
            import pdfplumber

            text_parts: List[str] = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if isinstance(page_text, str):
                        text_parts.append(str(page_text))
            text = str("\n").join(text_parts)
            text_stripped = text.strip()
            if not text_stripped:
                raise ValueError("pdfplumber also extracted no text.")
            logger.info(f"pdfplumber fallback succeeded: {len(text)} chars extracted.")
        except ImportError:
            raise ValueError(
                f"Failed to extract text from PDF: {str(e)}. Install pdfplumber for fallback: pip install pdfplumber"
            )
        except Exception as e2:
            logger.warning(f"pdfplumber failed: {e2}. Trying Tesseract OCR fallback...")
            try:
                images = convert_from_path(file_path)
                text_parts: List[str] = []
                for img in images:
                    page_text = pytesseract.image_to_string(img)
                    if page_text:
                        text_parts.append(str(page_text))
                text = "\n".join(text_parts)
                text_stripped = text.strip()
                if not text_stripped:
                    raise ValueError("OCR also extracted no text.")
                logger.info(
                    f"Tesseract OCR fallback succeeded: {len(text)} chars extracted."
                )
            except Exception as e3:
                raise ValueError(
                    f"Failed to extract text from PDF with pypdf, pdfplumber, and Tesseract OCR: {str(e3)}"
                )

    # Helper for regex: Allow space, colon, hyphen, or newlines as separators in complex tables
    def find_val(label_pattern, extra_flags=re.IGNORECASE):
        # Pattern: Label followed by optional separators, then the value until newline or end, OR spanning across a table cell
        # This handles cases like "Village Name \n Dharori..."
        pattern = rf"(?:{label_pattern})[\s:\-\|]*([^\n]*?(?:(?!\n(?:[A-Z][a-z]+ |Seller|Buyer|Market Value)).)*)"

        # Try a more specific structure for this type of docket first where value is explicitly after the label
        strict_pattern = rf"(?:{label_pattern})[\s:\-\|]+([^\n|]+)"
        match = re.search(strict_pattern, text, extra_flags)

        if not match:
            # Fallback to broader match that might cross a newline in a bad pypdf parse
            match = re.search(pattern, text, extra_flags)

        val = (
            match.group(1).strip()
            if match and match.lastindex == 1 and match.group(1)
            else "Unknown"
        )

        # Cleanup specific prefixes often found in these docs
        for prefix in [
            "Name:",
            "Mr.",
            "Mrs.",
            "S/O",
            "D/O",
            "W/O",
            "Name :",
            "Mr ",
            "Mrs ",
            "Mrs.Name:",
        ]:
            if (
                isinstance(val, str)
                and isinstance(prefix, str)
                and val.lower().startswith(prefix.lower())
            ):
                # Avoid slicing: val = val[len(prefix):].strip()
                prefix_len = len(prefix)
                clean_chars: List[str] = []
                v_idx = 0
                for v_char in val:
                    if v_idx >= prefix_len:
                        clean_chars.append(str(v_char))
                    v_idx += 1
                val = "".join(clean_chars).strip()

        # One more pass to be safe
        for prefix in ["Name:", "Name :"]:
            if (
                isinstance(val, str)
                and isinstance(prefix, str)
                and val.lower().startswith(prefix.lower())
            ):
                # Avoid slicing
                prefix_len = len(prefix)
                clean_chars: List[str] = []
                v_idx = 0
                for v_char in val:
                    if v_idx >= prefix_len:
                        clean_chars.append(str(v_char))
                    v_idx += 1
                val = "".join(clean_chars).strip()

        # Truncate if it captured too much table noise
        if isinstance(val, str) and len(val) > 200:
            tr_chars: List[str] = []
            tr_cnt = 0
            for tr_c in val:
                if tr_cnt >= 200:
                    break
                tr_chars.append(str(tr_c))
                tr_cnt += 1
            val = "".join(tr_chars)

        return val.title() if val != "Unknown" else "Unknown"

    extracted = {
        "text_content": text,
        "state": find_val(r"(?:State|Province)"),
        "district": find_val(r"(?:District|Zilla)"),
        "tehsil": find_val(r"(?:Tehsil|Taluka|Mandal|Sub-District)"),
        # The village name in the image has comma separated values "Dharori - ... , Kumharsain, Shimla"
        "village": find_val(r"(?:Village Name|Village|Mouza|Town|Revenue Village)"),
        "plot_no": find_val(
            r"(?:Other Description of the(?: Property)?.*?Khewat Number|Plot|Plot No|Plot Number|Gut No|Gat No|Survey No|Khewat No|Khewat Number|Khatauni Number|Khatauni No|Khewat)\.?"
        ),
        "house_no": find_val(r"(?:House|House No|Flat No|Apartment)\.?"),
        "seller_name": find_val(
            r"(?:Seller(?:.*?Name:)?|Transferor|Vendor|First Party)(?: Name)?",
            re.IGNORECASE | re.DOTALL,
        ),
        "buyer_name": find_val(
            r"(?:Buyer(?:.*?Name:)?|Transferee|Purchaser|Second Party)(?: Name)?",
            re.IGNORECASE | re.DOTALL,
        ),
        "seller_aadhaar": find_val(
            r"Seller Aadhaar(?: Number)?|Aadhaar(?: No)?\.? (?:of Seller)?"
        ),
        "seller_pan": find_val(r"Seller PAN(?: Number)?|PAN(?: No)?\.? (?:of Seller)?"),
        "buyer_aadhaar": find_val(
            r"Buyer Aadhaar(?: Number)?|Aadhaar(?: No)?\.? (?:of Buyer)?"
        ),
        "buyer_pan": find_val(r"Buyer PAN(?: Number)?|PAN(?: No)?\.? (?:of Buyer)?"),
        "registration_date": find_val(
            r"Document Registration Date(?: :-)?|Registration Date(?: :-)?"
        ),
    }

    # POST-PROCESSING CLEANUP
    for k, v in extracted.items():
        if k != "text_content" and isinstance(v, str) and v != "Unknown":
            v_lower = v.lower()
            if v_lower.startswith("of "):
                # Avoid slicing v[3:]
                off_chars: List[str] = []
                off_idx_val = 0
                for oc in v:
                    if off_idx_val >= 3:
                        off_chars.append(str(oc))
                    off_idx_val += 1
                extracted[k] = "".join(off_chars).strip()
            elif v_lower.startswith("the "):
                # Avoid slicing v[4:]
                the_chars: List[str] = []
                the_idx_val = 0
                for tc in v:
                    if the_idx_val >= 4:
                        the_chars.append(str(tc))
                    the_idx_val += 1
                extracted[k] = "".join(the_chars).strip()

    # DECISION: When to call LLM?
    # 1. Critical fields are "Unknown"
    # 2. Critical fields look suspicious (too long, e.g. captured a whole sentence)
    critical_missing = (
        extracted["village"] == "Unknown"
        or extracted["district"] == "Unknown"
        or extracted["plot_no"] == "Unknown"
    )

    suspicious_length = False
    for key in ["village", "district", "plot_no"]:
        if len(extracted[key]) > 50:  # Likely captured garbage
            suspicious_length = True
            break

    if critical_missing or suspicious_length:
        logger.info(
            f"Weak extraction. Missing: {critical_missing}, Suspicious: {suspicious_length}. Text len: {len(text)}. Invoking LLM..."
        )
        try:
            llm_extracted = llm_client.extract_metadata(text)
            # Update extracted with non-empty values from LLM
            for k, v in llm_extracted.items():
                if v and str(v).lower() != "unknown" and str(v).strip():
                    extracted[k] = v
        except Exception as llm_e:
            logger.warning(f"LLM Extraction failed: {llm_e}")

    return extracted


def process_document(file, db: Session):
    try:
        # 1. Save File
        if not os.path.exists(settings.DOCUMENT_STORAGE_PATH):
            os.makedirs(settings.DOCUMENT_STORAGE_PATH)

        file_content = file.file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        file_size = len(file_content)

        # Check duplicate in SQL by hash first
        existing_doc = (
            db.query(sql_models.Document)
            .filter(sql_models.Document.file_hash == file_hash)
            .first()
        )

        # Secondary check: same filename already processed
        if not existing_doc and getattr(file, "filename", None):
            existing_doc = (
                db.query(sql_models.Document)
                .filter(sql_models.Document.file_path.contains(file.filename))
                .first()
            )

        if existing_doc:
            return {
                "status": "skipped",
                "message": "Document already exists or same filename was uploaded.",
                "document_id": existing_doc.id,
            }

        # Sanitize filename to prevent path traversal attacks (e.g., "../../etc/passwd")
        raw_filename = getattr(file, "filename", "doc.pdf") or "doc.pdf"
        safe_filename = os.path.basename(raw_filename)  # Strip directory components
        if not safe_filename:
            safe_filename = "doc.pdf"
        file_path = os.path.join(
            settings.DOCUMENT_STORAGE_PATH, f"{file_hash}_{safe_filename}"
        )
        with open(file_path, "wb") as f:
            f.write(file_content)

        # 2. Extract Text & Metadata
        extracted = extract_metadata(file_path)
        text_content = extracted["text_content"]

        # 3. Save to Postgres

        # NORMALIZE strings for lookup to detect "Wakad" vs "wakad"
        # Ideally, we should lower() everything, but Title Case is good for presentation.
        # We already .title() in extract_metadata.

        from app.utils.text_utils import normalize_property_details

        # GUARD: Ensure mandatory fields are not None (SQL constraint)
        for key in ["state", "district", "tehsil", "village", "plot_no"]:
            if not extracted.get(key):
                extracted[key] = "Unknown"

        # VALIDATION: Reject if too many Unknowns (prevents garbage / duplicates of "Unknown" property)
        known_count = 0
        for k in ["village", "plot_no", "district", "state"]:
            if extracted.get(k) and extracted[k] != "Unknown":
                known_count += 1

        if known_count < 2:
            # Instead of rejecting entirely, do a PARTIAL INGESTION:
            # Save the document record + raw text to ChromaDB so it's searchable via RAG
            logger.warning(
                f"Weak extraction for {getattr(file, 'filename', 'unknown')} (only {known_count}/4 fields). Doing partial ingestion."
            )

            # Create document record
            new_doc = sql_models.Document(file_path=file_path, file_hash=file_hash)
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)

            # Store raw text in ChromaDB even without structured metadata
            if text_content and text_content.strip():
                try:
                    collection = get_property_collection()
                    chroma_id = f"doc_{file_hash}"
                    metadata = {
                        "document_id": new_doc.id,
                        "property_id": -1,
                        "district": extracted.get("district", "Unknown"),
                        "village": extracted.get("village", "Unknown"),
                        "plot_no": extracted.get("plot_no", "Unknown"),
                        "seller": extracted.get("seller_name", "Unknown"),
                        "buyer": extracted.get("buyer_name", "Unknown"),
                        "partial_ingestion": "true",
                    }
                    collection.upsert(
                        documents=[text_content], metadatas=[metadata], ids=[chroma_id]
                    )
                except Exception as chroma_err:
                    logger.error(f"ChromaDB partial storage failed: {chroma_err}")

            return {
                "status": "partial",
                "message": f"Stored document text for search, but could not extract full property details (only {known_count}/4 fields found). Try re-uploading a clearer copy.",
                "document_id": new_doc.id,
            }

        logger.info(
            f"Extracted metadata for {getattr(file, 'filename', 'unknown')}: village={extracted.get('village')}, district={extracted.get('district')}, plot={extracted.get('plot_no')}"
        )

        # Normalize Plot No for comparison
        raw_plot_no = extracted["plot_no"]
        norm_plot_no = normalize_property_details(raw_plot_no)

        # 1. Exact Match Attempt
        prop = (
            db.query(sql_models.Property)
            .filter_by(
                state=extracted["state"],
                district=extracted["district"],
                tehsil=extracted["tehsil"],
                village=extracted["village"],
                plot_no=extracted["plot_no"],
            )
            .first()
        )

        # 2. Relaxed Exact Match (normalized comparison instead of fuzzy library)
        if not prop:
            candidates = (
                db.query(sql_models.Property)
                .filter_by(
                    state=extracted["state"],
                    district=extracted["district"],
                    tehsil=extracted["tehsil"],
                    village=extracted["village"],
                )
                .all()
            )

            for candidate in candidates:
                if normalize_property_details(candidate.plot_no) == norm_plot_no:
                    prop = candidate
                    logger.info(
                        f"Normalized exact match found! '{raw_plot_no}' -> '{prop.plot_no}'"
                    )
                    break

        if not prop:
            prop = sql_models.Property(
                state=extracted["state"],
                district=extracted["district"],
                tehsil=extracted["tehsil"],
                village=extracted["village"],
                plot_no=extracted[
                    "plot_no"
                ],  # Storing the raw one from this doc, next time it will match fuzzy
                house_no=extracted["house_no"],
            )
            db.add(prop)
            db.flush()  # Get ID without committing

        # Create or Get People with Aadhaar/PAN Priority
        def get_or_create_person(
            name: str, aadhaar: str = None, pan: str = None, db: Session = None
        ) -> sql_models.Person:
            person = None

            # 1. Unique ID Match (The most reliable)
            if aadhaar and aadhaar != "Unknown":
                person = (
                    db.query(sql_models.Person)
                    .filter_by(aadhaar_number=aadhaar)
                    .first()
                )
            if not person and pan and pan != "Unknown":
                person = db.query(sql_models.Person).filter_by(pan_number=pan).first()

            # 2. Name Match (Only if IDs aren't available or didn't match anything)
            if not person:
                # Exact Name Match
                person = (
                    db.query(sql_models.Person)
                    .filter(sql_models.Person.name.ilike(name))
                    .first()
                )

            if not person:
                # Fuzzy Name Match
                all_people = db.query(sql_models.Person).all()
                if all_people:
                    names = [p.name for p in all_people]
                    best_match = process.extractOne(name, names, scorer=fuzz.WRatio)
                    if best_match and best_match[1] > 90:
                        matched_name = str(best_match[0])
                        person = (
                            db.query(sql_models.Person)
                            .filter_by(name=matched_name)
                            .first()
                        )
                        logger.info(
                            f"Fuzzy match found for Person: '{name}' -> '{matched_name}'"
                        )

            if not person:
                # Create new person if none of the above found anyone
                person = sql_models.Person(
                    name=name,
                    aadhaar_number=aadhaar if aadhaar != "Unknown" else None,
                    pan_number=pan if pan != "Unknown" else None,
                )
                db.add(person)
                db.flush()
            else:
                # Update existing person's IDs if they were null but are now found
                if aadhaar and aadhaar != "Unknown" and not person.aadhaar_number:
                    person.aadhaar_number = aadhaar
                if pan and pan != "Unknown" and not person.pan_number:
                    person.pan_number = pan
                db.flush()

            return person

        seller = get_or_create_person(
            extracted["seller_name"],
            extracted.get("seller_aadhaar"),
            extracted.get("seller_pan"),
            db,
        )
        buyer = get_or_create_person(
            extracted["buyer_name"],
            extracted.get("buyer_aadhaar"),
            extracted.get("buyer_pan"),
            db,
        )

        # Create Document record
        new_doc = sql_models.Document(file_path=file_path, file_hash=file_hash)
        db.add(new_doc)
        db.flush()

        # Create Transaction record
        registration_date = extracted.get("registration_date")
        from datetime import datetime

        parsed_date = datetime.utcnow().date()
        if registration_date and registration_date != "Unknown":
            try:
                from dateutil import parser

                parsed_date = parser.parse(registration_date, fuzzy=True).date()
            except Exception:
                pass

        transaction = sql_models.Transaction(
            property_id=prop.id,
            seller_id=seller.id,
            buyer_id=buyer.id,
            document_id=new_doc.id,
            registration_date=parsed_date,
        )
        db.add(transaction)
        db.flush()

        # 4. Store in ChromaDB (Do this BEFORE final commit)
        if text_content and text_content.strip():
            collection = get_property_collection()
            chroma_id = f"doc_{file_hash}"

            metadata = {
                "document_id": new_doc.id,
                "property_id": prop.id,
                "district": extracted["district"],
                "village": extracted["village"],
                "plot_no": extracted["plot_no"],
                "seller": seller.name,
                "buyer": buyer.name,
            }

            collection.upsert(
                documents=[text_content], metadatas=[metadata], ids=[chroma_id]
            )
        else:
            raise ValueError("No text content extracted from document.")

        # 5. Final Commit
        db.commit()

    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        db.rollback()  # Rollback Postgres
        # Cleanup file if we failed at any point
        if "file_path" in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up failed upload at {file_path}")
            except Exception as clean_err:
                logger.warning(f"Failed to cleanup {file_path}: {clean_err}")

        return {"status": "error", "message": str(e)}

    return {
        "status": "success",
        "document_id": new_doc.id,
        "file_hash": file_hash,
        "property_id": prop.id,
        "extracted_data": extracted,
    }
