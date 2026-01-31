"""
API routes for repository analysis and Q&A.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.pydantic_models import (
    AnalyzeRepoRequest, AnalyzeRepoResponse,
    AskQuestionRequest, AskQuestionResponse
)
from services.analysis_service import AnalysisService

router = APIRouter()
analysis_service = AnalysisService()


async def run_analysis_background(repo_url: str, db: AsyncSession):
    """Background task for repository analysis."""
    try:
        await analysis_service.analyze_repository(repo_url, db)
    except Exception as e:
        print(f"Background analysis failed for {repo_url}: {str(e)}")


@router.post("/analyze-repo", response_model=AnalyzeRepoResponse)
async def analyze_repo(
    request: AnalyzeRepoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a GitHub repository.
    
    This endpoint initiates repository analysis in the background.
    The analysis includes:
    - Fetching repository metadata
    - Analyzing code structure
    - Generating tech stack insights
    - Creating architecture summary
    - Analyzing GitHub issues
    - Generating contributor guide
    """
    try:
        # Validate URL format
        if not request.repo_url or 'github.com' not in request.repo_url:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository URL"
            )
        
        # Parse URL to get owner and repo name
        github_service = analysis_service.github
        try:
            owner, repo_name = github_service.parse_repo_url(request.repo_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Check if repository already exists
        from sqlalchemy import select
        from models.schemas import Repository
        import uuid
        
        result = await db.execute(
            select(Repository).where(Repository.repo_url == request.repo_url)
        )
        existing_repo = result.scalar_one_or_none()
        
        if existing_repo:
            repo_id = existing_repo.id
        else:
            # Generate new repo_id but DON'T create the repository yet
            # Let the background task create it with full metadata
            repo_id = str(uuid.uuid4())
        
        # Start analysis in background with the repo_id
        from db.database import async_session_maker
        
        async def background_analysis():
            async with async_session_maker() as bg_db:
                try:
                    # Pass the repo_id to ensure consistency
                    await analysis_service.analyze_repository(
                        request.repo_url, 
                        bg_db,
                        repo_id=repo_id
                    )
                except Exception as e:
                    print(f"Background analysis error: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        background_tasks.add_task(background_analysis)
        
        return AnalyzeRepoResponse(
            repo_id=repo_id,
            status="processing",
            message="Repository analysis started. Use the repo_id to ask questions once processing completes."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
        )


@router.post("/ask", response_model=AskQuestionResponse)
async def ask_question(
    request: AskQuestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question about an analyzed repository.
    
    This endpoint answers context-aware questions about the repository,
    including file purposes, architecture, and implementation details.
    """
    try:
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
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "repo-analyzer"}