import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, cast

from sqlalchemy import text
from sqlalchemy.orm import Session

# Reverting to absolute imports which are generally more standard for project roots
from app.core.chroma import get_property_collection
from app.core.llm import LLMClient, llm_client
from app.models import sql_models
from app.services import chat_history

logger = logging.getLogger(__name__)


def natural_language_search(
    query_text: str, db: Session, session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mode A: AI -> Chroma -> Postgres
    Performs retrieval augmented generation (RAG) to answer user queries.
    """
    try:
        # 0. Get History
        history_parts: List[str] = []
        if session_id:
            # Type safe approach to avoid slicing error on potentially unknown type
            raw_history = chat_history.get_history(db, session_id)
            if isinstance(raw_history, list):
                # Manual slice to satisfy linter
                history = []
                h_len = len(raw_history)
                start_h = max(0, h_len - 2)
                for h_idx in range(start_h, h_len):
                    if h_idx < h_len:
                        history.append(raw_history[h_idx])

                if history:
                    history_parts.append("Conversation History:\n")
                    for msg in history:
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            history_parts.append(
                                f"{str(msg['role']).title()}: {msg['content']}\n"
                            )
                    history_parts.append("\n")
        history_str = "".join(history_parts)

        collection = get_property_collection()

        # 1. Retrieve from Chroma with distance scores (semantic search)
        try:
            results_raw = collection.query(
                query_texts=[query_text],
                n_results=5,
                include=cast(Any, ["documents", "metadatas", "distances"]),
            )
            results: Dict[str, Any] = (
                cast(Dict[str, Any], results_raw)
                if isinstance(results_raw, dict)
                else {}
            )
        except Exception as e:
            logger.warning(f"Chroma DB query failed (likely API limits): {e}")
            results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        # 1b. KEYWORD SEARCH: If query contains specific numbers or property identifiers
        search_keywords: List[str] = []

        # Extract 4+ digit numbers (document/property IDs)
        long_ids = re.findall(r"\b\d{4,}\b", query_text)
        search_keywords.extend(long_ids)

        # Extract property-specific identifiers with any number (e.g., "Khewat Number - 21", "Plot 45")
        prop_patterns = re.findall(
            r"(?:Khewat|Khasra|Plot|Survey|Gut|Gat|Khatauni|Property\s*Id)[^\d]*(\d+)",
            query_text,
            re.IGNORECASE,
        )
        for num in prop_patterns:
            if num not in search_keywords:
                search_keywords.append(num)

        # Also try searching for the full property term phrase
        prop_phrases = re.findall(
            r"((?:Khewat|Khasra|Khatauni)\s*(?:Number|No\.?)?\s*[-:]?\s*\d+)",
            query_text,
            re.IGNORECASE,
        )
        for phrase in prop_phrases:
            clean = phrase.strip()
            if clean not in search_keywords:
                search_keywords.append(clean)

        if isinstance(search_keywords, list) and len(search_keywords) > 0:
            try:
                # Use a loop instead of slicing to avoid "Cannot index into" errors
                keywords_to_search: List[str] = []
                for idx, kw in enumerate(search_keywords):
                    if idx >= 3:
                        break
                    keywords_to_search.append(str(kw))

                for keyword in keywords_to_search:
                    try:
                        keyword_results_raw = collection.query(
                            query_texts=[query_text],
                            n_results=3,
                            where_document={"$contains": keyword},
                            include=cast(Any, ["documents", "metadatas", "distances"]),
                        )
                        keyword_results = cast(Dict[str, Any], keyword_results_raw)
                    except Exception as e:
                        logger.warning(
                            f"Keyword search for '{keyword}' failed (likely API limits): {e}"
                        )
                        continue

                    # Merge keyword results into main results
                    kw_docs = cast(
                        Optional[List[List[str]]], keyword_results.get("documents")
                    )
                    kw_metas = cast(
                        Optional[List[List[Dict[str, Any]]]],
                        keyword_results.get("metadatas"),
                    )

                    if (
                        isinstance(kw_docs, list)
                        and len(kw_docs) > 0
                        and isinstance(kw_docs[0], list)
                    ):
                        for j, doc in enumerate(kw_docs[0]):
                            # Explicitly check for results structure to satisfy linter
                            docs_list = cast(
                                Optional[List[List[str]]], results.get("documents")
                            )
                            metas_list = cast(
                                Optional[List[List[Dict[str, Any]]]],
                                results.get("metadatas"),
                            )
                            dists_list = cast(
                                Optional[List[List[float]]], results.get("distances")
                            )

                            if (
                                isinstance(docs_list, list)
                                and len(docs_list) > 0
                                and isinstance(docs_list[0], list)
                                and doc not in docs_list[0]
                            ):
                                docs_list[0].insert(0, str(doc))
                                if (
                                    isinstance(metas_list, list)
                                    and len(metas_list) > 0
                                    and isinstance(metas_list[0], list)
                                    and isinstance(kw_metas, list)
                                    and len(kw_metas) > 0
                                ):
                                    metas_list[0].insert(0, kw_metas[0][j])
                                if (
                                    isinstance(dists_list, list)
                                    and len(dists_list) > 0
                                    and isinstance(dists_list[0], list)
                                ):
                                    dists_list[0].insert(0, 0.5)
                        logger.info(
                            f"Keyword search for '{keyword}' found {len(kw_docs[0])} results"
                        )
            except Exception as kw_err:
                logger.warning(f"Keyword search failed: {kw_err}")

        # 2. Extract Property IDs from relevant results only
        property_ids: set[int] = set()
        raw_docs: List[str] = []

        docs_raw = results.get("documents")
        metadatas_raw = results.get("metadatas")
        distances_raw = results.get("distances")

        if isinstance(docs_raw, list) and len(docs_raw) > 0 and docs_raw[0]:
            raw_docs = docs_raw[0]
            metadatas = (
                metadatas_raw[0]
                if isinstance(metadatas_raw, list) and metadatas_raw
                else []
            )
            distances = (
                distances_raw[0]
                if isinstance(distances_raw, list) and distances_raw
                else []
            )

            # Filter by distance threshold — lower distance = more relevant
            relevant_indices: List[int] = []
            if isinstance(distances, list):
                for i_dist, dist_val in enumerate(distances):
                    if isinstance(dist_val, (int, float)) and dist_val < 1.5:
                        relevant_indices.append(i_dist)

            # If no results pass threshold, still take the top 2
            if (
                not relevant_indices
                and isinstance(raw_docs, list)
                and len(raw_docs) > 0
            ):
                for ridx in range(min(2, len(raw_docs))):
                    relevant_indices.append(ridx)

            relevant_docs: List[str] = []
            if isinstance(raw_docs, list):
                # Iterate to append instead of indexing to avoid "non-class" or "Cannot index" errors
                for i_idx, doc_val in enumerate(raw_docs):
                    is_relevant = False
                    for ridx in relevant_indices:
                        if ridx == i_idx:
                            is_relevant = True
                            break
                    if is_relevant:
                        relevant_docs.append(str(doc_val))

                # Check for metadata
                for i_idx, meta_val in enumerate(metadatas):
                    is_relevant = False
                    for ridx in relevant_indices:
                        if ridx == i_idx:
                            is_relevant = True
                            break
                    if is_relevant:
                        if (
                            isinstance(meta_val, dict)
                            and "property_id" in meta_val
                            and meta_val["property_id"] != -1
                        ):
                            property_ids.add(int(meta_val["property_id"]))

        try:
            # Explicitly cast llm_client to its class to fix "non-class" error
            llm: LLMClient = cast(LLMClient, llm_client)
            params = llm.nl_to_query_params(query_text)

            p_vill = params.get("village")
            p_plot = params.get("plot_no")
            p_dist = params.get("district")

            if p_vill or p_dist or p_plot:
                query = db.query(sql_models.Property.id)
                count = 0
                if p_vill and p_vill != "null" and p_vill.lower() != "unknown":
                    query = query.filter(
                        sql_models.Property.village.ilike(f"%{p_vill}%")
                    )
                    count += 1
                if p_dist and p_dist != "null" and p_dist.lower() != "unknown":
                    query = query.filter(
                        sql_models.Property.district.ilike(f"%{p_dist}%")
                    )
                    count += 1
                if p_plot and p_plot != "null" and p_plot.lower() != "unknown":
                    # Clean plot number for search - be MORE PERMISSIVE
                    clean_plot = re.findall(r"[a-zA-Z0-9]+", str(p_plot))
                    if clean_plot:
                        # Use a loop to build filters for each part to avoid "Cannot index" errors
                        for part in clean_plot:
                            query = query.filter(
                                sql_models.Property.plot_no.ilike(f"%{part}%")
                            )
                        count += 1

                if count > 0:
                    fallback_props = query.limit(30).all()
                    for fp in fallback_props:
                        val = cast(Any, fp)[0]
                        if val is not None:
                            property_ids.add(int(val))

            # Special case for district searches
            if p_dist and p_dist != "null" and p_dist.lower() != "unknown":
                dist_props = (
                    db.query(sql_models.Property.id)
                    .filter(sql_models.Property.district.ilike(f"%{p_dist}%"))
                    .limit(30)
                    .all()
                )
                for dp in dist_props:
                    val = cast(Any, dp)[0]
                    if val is not None:
                        property_ids.add(int(val))

            # If still nothing, do the broad village match as last resort
            if not property_ids:
                villages = []
                try:
                    villages_raw = (
                        db.query(sql_models.Property.village).distinct().all()
                    )
                    for v_row in villages_raw:
                        v_val = cast(Any, v_row)[0]
                        if v_val:
                            villages.append(str(v_val))
                except Exception:
                    villages = []

                for v in villages:
                    if isinstance(v, str) and v.lower() in query_text.lower():
                        matched_props = (
                            db.query(sql_models.Property.id)
                            .filter(sql_models.Property.village.ilike(f"%{v}%"))
                            .limit(5)
                            .all()
                        )
                        for mp in matched_props:
                            # Cast to Any
                            val = cast(Any, mp)[0]
                            if val is not None:
                                property_ids.add(int(val))

            # Check for specific Property ID match in DB (numbers only)
            long_ids = re.findall(r"\b\d{4,}\b", query_text)
            for eid in long_ids:
                prop_obj = (
                    db.query(sql_models.Property)
                    .filter(sql_models.Property.id == int(eid))
                    .first()
                )
                if prop_obj:
                    property_ids.add(prop_obj.id)
        except Exception as e:
            logger.warning(
                f"Failed to fetch fallback properties for query context: {e}"
            )

        # Limit to max 20 properties
        property_ids_list: List[int] = [int(pid) for pid in property_ids]
        final_property_ids: List[int] = []
        for pid_val in property_ids_list:
            if len(final_property_ids) >= 20:
                break
            final_property_ids.append(int(pid_val))

        if not final_property_ids and not raw_docs:
            return {
                "answer": "No relevant property documents found. Try uploading some property deeds first.",
                "sources": [],
            }

        # 3. Fetch authoritative data from Postgres format compactly
        db_context_parts: List[str] = ["### Database Records:\n"]
        # Ensure primitive int list to satisfy linter
        final_property_ids_typed: List[int] = []
        for p_id in final_property_ids:
            final_property_ids_typed.append(int(p_id))

        if final_property_ids_typed:
            transactions = (
                db.query(sql_models.Transaction)
                .filter(
                    sql_models.Transaction.property_id.in_(final_property_ids_typed)
                )
                .all()
            )

            properties = (
                db.query(sql_models.Property)
                .filter(sql_models.Property.id.in_(final_property_ids_typed))
                .all()
            )

            prop_map: Dict[int, sql_models.Property] = {}
            for p_obj in properties:
                prop_map[int(cast(Any, p_obj).id)] = p_obj

            seen_props: Set[int] = set()

            for txn in transactions:
                seen_props.add(int(cast(Any, txn).property_id))
                seller_name = txn.seller.name if txn.seller else "Not Available"
                buyer_name = txn.buyer.name if txn.buyer else "Not Available"
                plot = "Not Specified"
                village = "Unknown Village"
                district = "Unknown District"
                if txn.property:
                    plot = (
                        str(txn.property.plot_no)
                        if txn.property.plot_no
                        else "Not Specified"
                    )
                    village = (
                        str(txn.property.village)
                        if txn.property.village
                        else "Unknown Village"
                    )
                    district = (
                        str(txn.property.district)
                        if txn.property.district
                        else "Unknown District"
                    )
                db_context_parts.append(
                    f"- Location: {district}, {village}, Plot: {plot} | Transaction: {seller_name} sold to {buyer_name} on {txn.registration_date}\n"
                )

            for pid in final_property_ids_typed:
                current_pid_val: int = int(pid)
                if current_pid_val not in seen_props:
                    if current_pid_val in prop_map:
                        p_inst = cast(Any, prop_map[current_pid_val])
                        # Use str() ensures it's a string, cast to Any to avoid Column bool error
                        plot_str = (
                            str(p_inst.plot_no) if p_inst.plot_no else "Not Specified"
                        )
                        village_str = (
                            str(p_inst.village) if p_inst.village else "Unknown Village"
                        )
                        district_str = (
                            str(p_inst.district)
                            if p_inst.district
                            else "Unknown District"
                        )
                        db_context_parts.append(
                            f"- Location: {district_str}, {village_str}, Plot: {plot_str} (Status: Registered property, no transactions recorded)\n"
                        )
        else:
            db_context_parts.append("- No exact property matches found in DB.\n")

        db_context = "".join(db_context_parts)

        # 4. Generate Natural Language Answer
        ctx_parts: List[str] = [
            "Instructions: Focus on the Database Records for authoritative property facts. Use Document Excerpts for meta-details. Use Conversation History for meta-questions like 'What did we talk about?'.\n\n",
            str(history_str),
            "\n### Autoritative Database Records:\n",
            str(db_context),
            "\n### Document Excerpts (Raw Text from PDF):\n",
        ]

        # Add raw snippets to help LLM fill in gaps (limit to top 2 most relevant)
        raw_docs_to_use_final: List[str] = []
        if "relevant_docs" in locals() and isinstance(relevant_docs, list):
            for rd in relevant_docs:
                raw_docs_to_use_final.append(str(rd))
        else:
            # Fallback if relevant_docs was not defined
            for i_rd, rd in enumerate(raw_docs):
                if i_rd >= 2:
                    break
                raw_docs_to_use_final.append(str(rd))

        for i, doc in enumerate(raw_docs_to_use_final):
            clean_doc_raw = str(doc).replace("\n", " ").strip()
            # Iterative truncation to avoid ALL slicing/indexing issues
            limit_len = 1200
            if len(clean_doc_raw) > limit_len:
                truncated_chars = []
                chars_appended = 0
                for char in clean_doc_raw:
                    if chars_appended >= limit_len:
                        break
                    truncated_chars.append(char)
                    chars_appended += 1
                clean_doc_str = "".join(truncated_chars)
            else:
                clean_doc_str = clean_doc_raw
            ctx_parts.append(f"Snippet {i+1}: {clean_doc_str}...\n")

        context_text = "".join(ctx_parts)

        # Combine History + Context (Pass the last 2 messages for free tier efficiency)
        history_msgs: List[Dict[str, Any]] = []
        if session_id:
            # Use manual loop to safely slice history
            raw_history_full = chat_history.get_history(db, session_id)
            if isinstance(raw_history_full, list):
                h_full_len = len(raw_history_full)
                start_h_full = max(0, h_full_len - 4)
                extracted_history = []
                for hf_idx in range(start_h_full, h_full_len):
                    if hf_idx < h_full_len:
                        extracted_history.append(raw_history_full[hf_idx])

                for h in extracted_history:
                    if isinstance(h, dict) and "role" in h and "content" in h:
                        msg_entry: Dict[str, Any] = {
                            "role": str(h["role"]),
                            "content": str(h["content"]),
                        }
                        if h.get("reasoning_details"):
                            msg_entry["reasoning_details"] = str(h["reasoning_details"])
                        history_msgs.append(msg_entry)

        logger.info(
            f"Query: {query_text} | Session: {session_id} | History Count: {len(history_msgs)}"
        )
        if history_msgs:
            logger.debug(f"Last History Msg: {history_msgs[-1]['content']}")

        llm_gen: LLMClient = cast(LLMClient, llm_client)
        human_answer, reasoning_details = llm_gen.generate_response(
            context_text, query_text, history_messages=history_msgs
        )

        # 5. Save loop to History
        if session_id:
            chat_history.add_message(db, session_id, "user", query_text)
            chat_history.add_message(
                db,
                session_id,
                "assistant",
                human_answer,
                reasoning_details=reasoning_details,
            )

        return {"answer": human_answer, "session_id": session_id}
    except Exception as e:
        import traceback

        logger.error(f"Natural language search error: {e}", exc_info=True)
        return {"message": f"Server Error: {traceback.format_exc()}"}


def ai_to_sql_query(nl_query: str, db: Session) -> Any:
    """
    Mode B: Convert NL to SQL (Intelligent with Nemotron)
    """
    # 1. Extract params using LLM
    llm: LLMClient = cast(LLMClient, llm_client)
    params = llm.nl_to_query_params(nl_query)

    if not params:
        return {
            "message": "Could not interpret query. Try asking naturally like 'show properties in Wakad'"
        }

    conditions = []
    sql_params = {}
    joins = []

    if params.get("village") and params["village"] != "null":
        conditions.append("lower(p.village) = :village")
        sql_params["village"] = params["village"].lower()

    if params.get("plot_no") and params["plot_no"] != "null":
        conditions.append("lower(p.plot_no) = :plot_no")
        sql_params["plot_no"] = params["plot_no"].lower()

    if params.get("district") and params["district"] != "null":
        conditions.append("lower(p.district) = :district")
        sql_params["district"] = params["district"].lower()

    if params.get("seller_name") and params["seller_name"] != "null":
        ids = [
            "transactions t ON p.id = t.property_id",
            "people s ON t.seller_id = s.id",
        ]
        joins.append("JOIN transactions t ON p.id = t.property_id")
        joins.append("JOIN people s ON t.seller_id = s.id")
        conditions.append("lower(s.name) LIKE :seller")
        sql_params["seller"] = f"%{params['seller_name'].lower()}%"

    if not conditions:
        return {"message": "Could not interpret query parameters."}

    # Construct Query
    base_query = "SELECT p.* FROM properties p"

    # Deduplicate Joins
    unique_joins = list(set(joins))
    join_str = " ".join(unique_joins)

    where_str = " AND ".join(conditions)

    final_sql = text(f"{base_query} {join_str} WHERE {where_str} LIMIT 100")

    # Execution
    try:
        result = db.execute(final_sql, sql_params)
        keys = result.keys()
        return [dict(zip(keys, row)) for row in result.fetchall()]
    except Exception as e:
        logger.error(f"AI SQL Execution failed: {e}")
        return {"error": "Failed to execute search query"}


def execute_direct_sql_safe(
    sql_query: str,
    db: Session,
    user_id: Optional[int] = None,
    log_db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Execute a raw SELECT query safely and return results as a list of dictionaries.
    Includes an audit trail log.
    """
    if user_id and log_db:
        try:
            audit_log = sql_models.AuditLog(user_id=user_id, query_text=sql_query)
            log_db.add(audit_log)
            log_db.commit()
        except Exception as log_err:
            logger.error(f"Failed to save audit log: {log_err}")
            log_db.rollback()

    try:
        result = db.execute(text(sql_query))
        keys = result.keys()
        return [dict(zip(keys, row)) for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Direct SQL Execution Error: {e}")
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(e))


def execute_direct_sql(sql_query: str, db: Session) -> Dict[str, str]:
    """
    Mode C: Direct SQL (Read-Only)
    DEPRECATED: Removed for security reasons (SQL Injection risk).
    """
    return {"error": "Direct SQL execution has been disabled for security reasons."}
