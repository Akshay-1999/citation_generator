from db.config import Database
from utils.logging_utils import set_system_logger    
import uuid
import datetime
import json
from typing import List, Optional

logger = set_system_logger("system_logger")

async def create_chat_thread(user_id: str , thread_title : str = None):
    """
    Create a new chat thread for a user in the chathistory schema.
    """
    try:
        logger.info(f"=== Creating new chat thread for user: {user_id} ===")
        thread_id = str(uuid.uuid4())
        pool = await Database.get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO chathistory.chat_threads (thread_id, user_id, thread_title, thread_created_at, thread_updated_at , is_deleted)
                VALUES ($1, $2, $3, NOW(), NOW() , false)
                """,
                thread_id, user_id , thread_title
            )
        logger.info(f"=== Chat thread created successfully: {thread_id} ===")
        return {"thread_id": thread_id}
    except Exception as e:
        logger.error(f"=== Error creating chat thread for user {user_id}: {e} ===")
        raise


async def append_message_to_thread(user_id: str, messages: List[dict], thread_id: str, file_context: Optional[List[dict]] = None):
    """
    Appends messages to a thread in the chathistory schema.
    """
    if not thread_id or not messages:
        return

    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise ValueError(f"Invalid thread_id format: {thread_id}")

    pool = await Database.get_pool()
    now = datetime.datetime.now(datetime.timezone.utc)

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Get next sequence number
            next_sequence = await conn.fetchval(
                """
                SELECT COALESCE(MAX(sequence_number), 0) + 1 
                FROM chathistory.messages 
                WHERE thread_id = $1
                """,
                thread_uuid
            )
            
            for i, msg in enumerate(messages):
                msg['sequence_number'] = next_sequence + i
                message_id = msg.get('message_id') or str(uuid.uuid4())
                
                await conn.execute(
                    """
                    INSERT INTO chathistory.messages (
                        message_id, thread_id, user_id, role, messages_content, 
                        created_at, citations, confidence_level, sequence_number, file_context_name
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    message_id, thread_uuid, user_id, msg.get('role'), msg.get('content'),
                    msg.get('timestamp', now), json.dumps(msg.get('citations', [])),
                    msg.get('confidence_level'), msg['sequence_number'], 
                    json.dumps(file_context) if file_context else None
                )
            
            await conn.execute(
                "UPDATE chathistory.chat_threads SET thread_updated_at = $1 WHERE thread_id = $2",
                now, thread_uuid
            )


async def get_user_threads(user_id: str):
    """
    Fetch all chat threads for a user, ordered by most recent update.
    """
    try:
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT thread_id, thread_title as title, thread_status as status, thread_updated_at 
                FROM chathistory.chat_threads 
                WHERE user_id = $1 AND is_deleted = false
                ORDER BY thread_updated_at DESC
                """,
                user_id
            )
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"--- Error fetching threads for user {user_id}: {e} ---")
        return []


async def get_thread_messages(thread_id: str):
    """
    Fetch all messages for a specific thread, ordered by sequence number.
    """
    try:
        thread_uuid = uuid.UUID(thread_id)
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, messages_content as content, created_at, citations, confidence_level, file_context_name 
                FROM chathistory.messages 
                WHERE thread_id = $1 
                ORDER BY sequence_number ASC
                """,
                thread_uuid
            )
            
            messages = []
            for row in rows:
                msg = dict(row)
                # Ensure citations and timestamp are JSON serializable
                if msg['citations']:
                    try:
                        msg['citations'] = json.loads(msg['citations']) if isinstance(msg['citations'], str) else msg['citations']
                    except:
                        msg['citations'] = []
                
                # Parse and simplify attachments from file_context_name
                if msg.get('file_context_name'):
                    try:
                        full_context = json.loads(msg['file_context_name']) if isinstance(msg['file_context_name'], str) else msg['file_context_name']
                        if isinstance(full_context, list):
                            msg['attachments'] = [{'filename': f.get('filename')} for f in full_context if isinstance(f, dict) and f.get('filename')]
                        else:
                            msg['attachments'] = []
                    except:
                        msg['attachments'] = []
                else:
                    msg['attachments'] = []

                if msg.get('created_at'):
                    msg['timestamp'] = msg['created_at'].isoformat()
                messages.append(msg)
            return messages
    except Exception as e:
        logger.error(f"--- Error fetching messages for thread {thread_id}: {e} ---")
        return []

async def delete_thread(thread_id: str , user_id: str):
    """
    Delete a chat thread for a user in the chathistory schema.
    """
    try:
        logger.info(f"=== Deleting chat thread for user: {thread_id} ===")
        pool = await Database.get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE chathistory.chat_threads SET is_deleted = true WHERE thread_id = $1 AND user_id = $2
                """,
                thread_id , user_id
            )
        logger.info(f"=== Chat thread deleted successfully: {thread_id} ===")
        return {"thread_id": thread_id}
    except Exception as e:
        logger.error(f"=== Error creating chat thread for user {user_id}: {e} ===")
        raise

async def rename_thread(thread_id: str, thread_title: str , user_id: str):
    """
    Rename a chat thread for a user in the chathistory schema.
    """
    try:
        logger.info(f"=== Renaming chat thread for user: {thread_id} ===")
        pool = await Database.get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE chathistory.chat_threads SET thread_title = $1 WHERE thread_id = $2 AND user_id = $3
                """,
                thread_title, thread_id , user_id
            )
        logger.info(f"=== Chat thread renamed successfully: {thread_id} ===")
        return {"thread_id": thread_id}
    except Exception as e:
        logger.error(f"=== Error renaming chat thread for user {user_id}: {e} ===")
        raise