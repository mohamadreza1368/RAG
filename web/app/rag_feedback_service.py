import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal, RAGQueryFeedbackLog, RAGChunkFeedbackStat, ChatMessage

logger = logging.getLogger(__name__)


def calculate_bayesian_boost(likes: int, dislikes: int) -> float:
    """
    محاسبه ضریب بهبود یا جریمه بیزی برای رتبه‌بندی چانک‌ها:
    Boost = ((Likes - Dislikes) / (Likes + Dislikes + 2)) * 0.20
    دامنه مقدار: بین -0.20 تا +0.20
    """
    total = likes + dislikes
    if total <= 0:
        return 0.0
    boost = ((likes - dislikes) / (total + 2.0)) * 0.20
    return round(float(boost), 4)


class RAGFeedbackService:
    """
    سرویس مدیریت بازخورد سراسری و دائمی چانک‌ها و پرسش‌های اکوسیستم RAG
    """

    @staticmethod
    def record_retrieval(
        query: str,
        message_id: Optional[int],
        session_id: Optional[str],
        engine_id: str,
        sources: List[Dict[str, Any]],
        db: Optional[Session] = None
    ) -> Optional[int]:
        """
        ثبت دائمی یک جستجو و چانک‌های بازیابی‌شده متناظر در پایگاه داده
        """
        if not sources or not query:
            return None

        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            chunk_ids = []
            for s in sources:
                cid = s.get("chunk_id")
                if cid is not None:
                    cid_str = str(cid)
                    chunk_ids.append(cid_str)

                    # Ensure chunk row exists in stats table
                    stat = db.query(RAGChunkFeedbackStat).filter(RAGChunkFeedbackStat.chunk_id == cid_str).first()
                    if not stat:
                        stat = RAGChunkFeedbackStat(
                            chunk_id=cid_str,
                            rule_title=s.get("rule_title"),
                            article_no=str(s.get("article_no") or s.get("article") or "")[:50],
                            like_count=0,
                            dislike_count=0,
                            net_boost_score=0.0
                        )
                        db.add(stat)

            if not chunk_ids:
                return None

            log_entry = RAGQueryFeedbackLog(
                query_text=query.strip(),
                message_id=message_id,
                session_id=session_id,
                engine_id=engine_id or "regulatory",
                retrieved_chunk_ids=json.dumps(chunk_ids, ensure_ascii=False),
                feedback=None
            )
            db.add(log_entry)
            db.commit()
            return log_entry.id

        except Exception as e:
            logger.error(f"Failed to record RAG query retrieval log: {e}", exc_info=True)
            if db:
                db.rollback()
            return None
        finally:
            if own_session and db:
                db.close()

    @staticmethod
    def apply_feedback(
        message_id: int,
        feedback_type: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        اعمال بازخورد لایک یا دیس‌لایک کاربر روی چانک‌های پیام و به‌روزرسانی نمرات جهانی
        """
        clean_feedback = feedback_type.lower().strip() if feedback_type else "none"
        if clean_feedback not in ["like", "dislike", "none"]:
            raise ValueError(f"Invalid feedback type: {feedback_type}")

        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            # 1. Find log entry or recover from ChatMessage.rag_metadata
            log = db.query(RAGQueryFeedbackLog).filter(RAGQueryFeedbackLog.message_id == message_id).first()
            chunk_ids = []

            if log:
                try:
                    chunk_ids = json.loads(log.retrieved_chunk_ids or "[]")
                except Exception:
                    chunk_ids = []
            else:
                msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
                if msg and msg.rag_metadata:
                    try:
                        meta = json.loads(msg.rag_metadata)
                        sources = meta.get("sources", [])
                        chunk_ids = [str(s.get("chunk_id")) for s in sources if s.get("chunk_id") is not None]
                        # Create backfilled log entry
                        log = RAGQueryFeedbackLog(
                            query_text="(بازیابی از کانتکست پیام)",
                            message_id=message_id,
                            session_id=msg.session_id,
                            engine_id=meta.get("engine_id", "regulatory"),
                            retrieved_chunk_ids=json.dumps(chunk_ids, ensure_ascii=False),
                            feedback=None
                        )
                        db.add(log)
                    except Exception as ex:
                        logger.warning(f"Could not parse rag_metadata for message {message_id}: {ex}")

            if not chunk_ids:
                return {"status": "no_chunks_found", "message_id": message_id}

            previous_feedback = log.feedback if log else None
            target_feedback = None if clean_feedback == "none" else clean_feedback

            # If unchanged, return early
            if previous_feedback == target_feedback:
                return {
                    "status": "unchanged",
                    "feedback": target_feedback,
                    "affected_chunks": len(chunk_ids)
                }

            # 2. Update chunk cumulative statistics
            updated_stats = []
            for cid in chunk_ids:
                stat = db.query(RAGChunkFeedbackStat).filter(RAGChunkFeedbackStat.chunk_id == str(cid)).first()
                if not stat:
                    stat = RAGChunkFeedbackStat(
                        chunk_id=str(cid),
                        like_count=0,
                        dislike_count=0,
                        net_boost_score=0.0
                    )
                    db.add(stat)

                # Revert previous feedback impact
                if previous_feedback == "like":
                    stat.like_count = max(0, stat.like_count - 1)
                elif previous_feedback == "dislike":
                    stat.dislike_count = max(0, stat.dislike_count - 1)

                # Apply new feedback impact
                if target_feedback == "like":
                    stat.like_count += 1
                elif target_feedback == "dislike":
                    stat.dislike_count += 1

                stat.net_boost_score = calculate_bayesian_boost(stat.like_count, stat.dislike_count)
                updated_stats.append({
                    "chunk_id": stat.chunk_id,
                    "likes": stat.like_count,
                    "dislikes": stat.dislike_count,
                    "boost": stat.net_boost_score
                })

            if log:
                log.feedback = target_feedback

            db.commit()

            return {
                "status": "success",
                "message_id": message_id,
                "feedback": target_feedback,
                "affected_chunks": len(chunk_ids),
                "stats_sample": updated_stats[:3]
            }

        except Exception as e:
            logger.error(f"Error applying feedback for message {message_id}: {e}", exc_info=True)
            if db:
                db.rollback()
            raise
        finally:
            if own_session and db:
                db.close()

    @staticmethod
    def get_chunk_boost_map(chunk_ids: List[Any], db: Optional[Session] = None) -> Dict[str, float]:
        """
        دریافت نگاشت ضریب تقویت نمره برای شناسه‌های چانک
        خروجی: {'chunk_id': net_boost_score, ...}
        """
        if not chunk_ids:
            return {}

        clean_ids = [str(cid) for cid in chunk_ids if cid is not None]
        if not clean_ids:
            return {}

        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            records = db.query(
                RAGChunkFeedbackStat.chunk_id,
                RAGChunkFeedbackStat.net_boost_score
            ).filter(RAGChunkFeedbackStat.chunk_id.in_(clean_ids)).all()

            return {r[0]: float(r[1] or 0.0) for r in records}
        except Exception as e:
            logger.warning(f"Could not load chunk boost scores: {e}")
            return {}
        finally:
            if own_session and db:
                db.close()


rag_feedback_service = RAGFeedbackService()
