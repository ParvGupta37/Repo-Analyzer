"""
Production API Routes - Hardened with proper async flow and persistence.
Implements Option A: Status-based async flow.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db, async_session_maker
from models.pydantic_models import (
    AnalyzeRepoRequest, AnalyzeRepoResponse,
    AskQuestionRequest, AskQuestionResponse
)
from services.analysis_service import AnalysisServiceFinal

router = APIRouter()
analysis_service = AnalysisServiceFinal()


@router.post("/analyze-repo", response_model=AnalyzeRepoResponse)
async def analyze_repo(
    request: AnalyzeRepoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start repository analysis (returns immediately with status='processing').
    
    Flow:
    1. Validate URL
    2. Create repo + analysis_session with status='processing'
    3. Commit to database
    4. Return immediately with repo_id and status
    5. Background task does actual analysis
    """
    try:
        # Validate URL
        if not request.repo_url or 'github.com' not in request.repo_url:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository URL"
            )
        
        # Start analysis (synchronous setup)
        result = await analysis_service.start_analysis(request.repo_url, db)
        
        repo_id = result['repo_id']
        
        # Background task for actual analysis (with NEW session)
        async def background_analysis():
            """
            Runs in background with its OWN database session.
            This is critical for SQLite persistence.
            """
            async with async_session_maker() as bg_db:
                try:
                    await analysis_service.execute_analysis(repo_id, bg_db)
                except Exception as e:
                    print(f"Background analysis error: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        background_tasks.add_task(background_analysis)
        
        return AnalyzeRepoResponse(
            repo_id=repo_id,
            status="processing",
            message="Analysis started. Use GET /api/status/{repo_id} to check progress."
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
        )


@router.get("/status/{repo_id}")
async def get_analysis_status(
    repo_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get analysis status for a repository.
    
    Returns:
        {
            "repo_id": "...",
            "status": "processing|completed|failed|not_found",
            "started_at": "...",
            "completed_at": "...",
            "error_message": "..."
        }
    """
    try:
        status = await analysis_service.get_status(repo_id, db)
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/analysis/{repo_id}")
async def get_analysis(
    repo_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete analysis for a repository.
    
    Requirements:
    - Analysis must be completed (status='completed')
    - Returns frontend-ready structured JSON
    - ZERO Gemini calls (reads from database only)
    """
    try:
        analysis = await analysis_service.get_analysis(repo_id, db)
        return analysis
    except ValueError as e:
        # Analysis not completed or not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis: {str(e)}"
        )


@router.post("/ask", response_model=AskQuestionResponse)
async def ask_question(
    request: AskQuestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Answer question about analyzed repository.
    
    Requirements:
    - Analysis MUST be completed first
    - Returns 400 if analysis not completed
    - ZERO Gemini calls (uses stored data only)
    - Idempotent and deterministic
    """
    try:
        # Check status first
        status = await analysis_service.get_status(request.repo_id, db)
        
        if status['status'] == 'not_found':
            raise HTTPException(
                status_code=404,
                detail=f"Repository not found: {request.repo_id}"
            )
        
        if status['status'] == 'processing':
            raise HTTPException(
                status_code=400,
                detail="Analysis still in progress. Please wait for completion."
            )
        
        if status['status'] == 'failed':
            raise HTTPException(
                status_code=400,
                detail=f"Analysis failed: {status.get('error_message', 'Unknown error')}"
            )
        
        # Status is 'completed' - safe to answer
        result = await analysis_service.answer_question(
            request.repo_id,
            request.question,
            db
        )
        
        return AskQuestionResponse(
            repo_id=result['repo_id'],
            question=result['question'],
            answer=result['answer'],
            created_at=result['created_at']
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint with system info."""
    return {
        "status": "healthy",
        "service": "repo-analyzer-final",
        "architecture": "production",
        "features": {
            "single_gemini_call": True,
            "split_table_storage": True,
            "status_based_async": True,
            "proper_persistence": True,
            "idempotent_qa": True
        }
    }