from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, List, Optional
from datetime import datetime
import json
import asyncio

from app.api.deps import SessionDep, get_current_active_user, get_db
from app.db.models import User
from app.core.config import settings
from app.domain.entities import Conversation, ChatMessage, AgentExecution
from app.domain.enums import AgentType, AgentStatus
from app.agents import agent_graph
from app.core.security import ALGORITHM
from jose import jwt

from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.orm import Session
from app.infrastructure.database import SessionLocal

router = APIRouter()

# Pydantic Schemas for Chat
class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    answer: str
    conversation_id: int

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ─── Conversation Management ──────────────────────────────

@router.get("/conversations", response_model=List[ConversationResponse])
def get_conversations(
    db: SessionDep,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get all conversations for the current logged-in user.
    """
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()
    return conversations

@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    db: SessionDep,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new conversation thread.
    """
    conv = Conversation(
        title="New Conversation",
        user_id=current_user.id,
        org_id=getattr(current_user, "org_id", 1),
        model=settings.LLM_MODEL
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def get_conversation_messages(
    conversation_id: int,
    db: SessionDep,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get all messages within a specific conversation.
    """
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return conv.messages

# ─── Chat Streaming & Sync Endpoints ──────────────────────

@router.post("/", response_model=ChatResponse)
def chat_sync(
    request: ChatRequest,
    db: SessionDep,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Synchronous chat endpoint using the Multi-Agent LangGraph system.
    """
    conv_id = request.conversation_id
    if not conv_id:
        conv = Conversation(
            title=request.query[:50],
            user_id=current_user.id,
            org_id=getattr(current_user, "org_id", 1)
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
    else:
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv.updated_at = datetime.utcnow()
        db.commit()

    user_msg = ChatMessage(
        conversation_id=conv_id,
        role="user",
        content=request.query
    )
    db.add(user_msg)
    db.commit()

    try:
        history = []
        for msg in conv.messages[:-1]:
            if msg.role == "user":
                history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history.append(AIMessage(content=msg.content))

        history.append(HumanMessage(content=request.query))

        initial_state = {
            "messages": history,
            "plan": [],
            "current_step": 0,
            "context": {},
            "final_response": "",
            "agent_logs": [],
            "user_id": current_user.id,
            "org_id": getattr(current_user, "org_id", 1),
            "department": getattr(current_user, "department", "general")
        }

        result = agent_graph.invoke(initial_state)
        answer = result.get("final_response", "I could not generate an answer.")

        assistant_msg = ChatMessage(
            conversation_id=conv_id,
            role="assistant",
            content=answer
        )
        db.add(assistant_msg)
        db.commit()

        return ChatResponse(answer=answer, conversation_id=conv_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: SessionDep,
    current_user: User = Depends(get_current_active_user)
):
    """
    SSE Streaming endpoint executing the multi-agent graph in real-time.
    """
    conv_id = request.conversation_id
    if not conv_id:
        conv = Conversation(
            title=request.query[:50],
            user_id=current_user.id,
            org_id=getattr(current_user, "org_id", 1)
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
    else:
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv.updated_at = datetime.utcnow()
        db.commit()

    user_msg = ChatMessage(
        conversation_id=conv_id,
        role="user",
        content=request.query
    )
    db.add(user_msg)
    db.commit()

    async def event_generator():
        inner_db = SessionLocal()
        try:
            history = []
            conv_obj = inner_db.query(Conversation).filter(Conversation.id == conv_id).first()
            for msg in conv_obj.messages[:-1]:
                if msg.role == "user":
                    history.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    history.append(AIMessage(content=msg.content))
            
            history.append(HumanMessage(content=request.query))

            initial_state = {
                "messages": history,
                "plan": [],
                "current_step": 0,
                "context": {},
                "final_response": "",
                "agent_logs": [],
                "user_id": current_user.id,
                "org_id": getattr(current_user, "org_id", 1),
                "department": getattr(current_user, "department", "general")
            }

            final_text = ""
            current_agent = "planner"

            async for event in agent_graph.astream_events(
                initial_state,
                version="v2"
            ):
                kind = event.get("event")
                name = event.get("name")
                
                if kind == "on_chain_start" and name in ["planner", "retrieval", "reasoning", "report", "workflow", "code", "meeting", "analytics"]:
                    current_agent = name
                    yield f"data: {json.dumps({'agent_step': {'agent': name, 'status': 'running'}}) }\n\n"
                    
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        if current_agent in ["report", "reasoning"]:
                            final_text += token
                            yield f"data: {json.dumps({'token': token}) }\n\n"
            
            db_assistant_msg = ChatMessage(
                conversation_id=conv_id,
                role="assistant",
                content=final_text or "Processed tasks successfully."
            )
            inner_db.add(db_assistant_msg)
            inner_db.commit()

            yield f"data: {json.dumps({'done': True, 'full_text': final_text or 'Done', 'conversation_id': conv_id}) }\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}) }\n\n"
        finally:
            inner_db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ─── WebSocket Bidirectional Endpoint ────────────────────

@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """
    Bidirectional WebSocket endpoint for secure real-time chat.
    Expects authentication via token payload in first message.
    """
    await websocket.accept()
    db = SessionLocal()
    current_user = None
    
    try:
        # First message must be authentication payload
        auth_msg = await websocket.receive_text()
        auth_data = json.loads(auth_msg)
        token = auth_data.get("token")
        
        if not token:
            await websocket.send_text(json.dumps({"error": "Unauthorized: Missing token"}))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            db.close()
            return
            
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if not email:
                raise ValueError()
            current_user = db.query(User).filter(User.email == email).first()
        except Exception:
            await websocket.send_text(json.dumps({"error": "Unauthorized: Invalid token"}))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            db.close()
            return

        if not current_user or not current_user.is_active:
            await websocket.send_text(json.dumps({"error": "Unauthorized: User inactive"}))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            db.close()
            return
            
        await websocket.send_text(json.dumps({"info": "Authentication successful"}))

        # Main communication loop
        while True:
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            query = data.get("query")
            conv_id = data.get("conversation_id")
            
            if not query:
                continue

            # Fetch or create conversation
            if not conv_id:
                conv = Conversation(
                    title=query[:50],
                    user_id=current_user.id,
                    org_id=getattr(current_user, "org_id", 1)
                )
                db.add(conv)
                db.commit()
                db.refresh(conv)
                conv_id = conv.id
            else:
                conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
                if not conv:
                    await websocket.send_text(json.dumps({"error": "Conversation not found"}))
                    continue

            # Insert user message
            user_msg = ChatMessage(
                conversation_id=conv_id,
                role="user",
                content=query
            )
            db.add(user_msg)
            db.commit()

            # Execute LangGraph and stream
            history = []
            for msg in conv.messages[:-1]:
                if msg.role == "user":
                    history.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    history.append(AIMessage(content=msg.content))
            
            history.append(HumanMessage(content=query))

            initial_state = {
                "messages": history,
                "plan": [],
                "current_step": 0,
                "context": {},
                "final_response": "",
                "agent_logs": [],
                "user_id": current_user.id,
                "org_id": getattr(current_user, "org_id", 1),
                "department": getattr(current_user, "department", "general")
            }

            final_text = ""
            current_agent = "planner"

            async for event in agent_graph.astream_events(initial_state, version="v2"):
                kind = event.get("event")
                name = event.get("name")
                
                if kind == "on_chain_start" and name in ["planner", "retrieval", "reasoning", "report", "workflow", "code", "meeting", "analytics"]:
                    current_agent = name
                    await websocket.send_text(json.dumps({"agent_step": {"agent": name, "status": "running"}}))
                    
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        if current_agent in ["report", "reasoning"]:
                            final_text += token
                            await websocket.send_text(json.dumps({"token": token}))
            
            # Save assistant message
            db_assistant_msg = ChatMessage(
                conversation_id=conv_id,
                role="assistant",
                content=final_text or "Processed successfully."
            )
            db.add(db_assistant_msg)
            db.commit()

            await websocket.send_text(json.dumps({"done": True, "full_text": final_text, "conversation_id": conv_id}))

    except WebSocketDisconnect:
        pass
    finally:
        db.close()
