"""
Analysis service that orchestrates repository analysis workflow.
Coordinates GitHub fetching, file filtering, LLM analysis, and database storage.
"""
import uuid
import json
from datetime import datetime
from typing import Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import (
    Repository, AnalysisSession, RepoFile, TechStack,
    ArchitectureSummary, IssuesInsights, ContributorGuide, QALog
)
from services.github_service import GitHubService
from services.gemini_service import GeminiService
from utils.file_filter import FileFilter


class AnalysisService:
    """Service for analyzing GitHub repositories."""
    
    def __init__(self):
        self.github = GitHubService()
        self.gemini = GeminiService()
        self.file_filter = FileFilter()
    
    async def analyze_repository(self, repo_url: str, db: AsyncSession, repo_id: str = None) -> str:
        """
        Main analysis workflow.
        Returns repo_id for the analyzed repository.
        """
        # Parse and validate URL
        try:
            owner, repo_name = self.github.parse_repo_url(repo_url)
        except ValueError as e:
            raise ValueError(f"Invalid repository URL: {str(e)}")
        
        def ensure_string(value):
            """Convert any value to string, handling lists/dicts by JSON encoding."""
            if value is None:
                return ''
            elif isinstance(value, (list, dict)):
                return json.dumps(value)
            elif isinstance(value, str):
                return value
            else:
                return str(value)
        
        # Check if repository already exists or use provided repo_id
        result = await db.execute(
            select(Repository).where(Repository.repo_url == repo_url)
        )
        existing_repo = result.scalar_one_or_none()
        
        if existing_repo:
            repo_id = existing_repo.id
        elif repo_id is None:
            repo_id = str(uuid.uuid4())
        
        # Initialize session variable
        session = None

        try:
            # Fetch repository metadata FIRST
            metadata = await self.github.get_repo_metadata(owner, repo_name)
            
            # Create or update repository record BEFORE creating session
            if not existing_repo:
                repository = Repository(
                    id=repo_id,
                    repo_url=repo_url,
                    owner=owner,
                    name=repo_name,
                    primary_language=metadata.get('language'),
                    created_at=datetime.fromisoformat(metadata['created_at'].replace('Z', '+00:00')) if metadata.get('created_at') else None,
                    analyzed_at=datetime.utcnow()
                )
                db.add(repository)
                await db.commit()  # Commit repository first
            else:
                existing_repo.analyzed_at = datetime.utcnow()
                existing_repo.primary_language = metadata.get('language')
                await db.commit()
            
            # NOW create analysis session (after repository exists)
            session_id = str(uuid.uuid4())
            session = AnalysisSession(
                id=session_id,
                repo_id=repo_id,
                status="in_progress",
                started_at=datetime.utcnow()
            )
            db.add(session)
            await db.commit()
            
            # Fetch README
            readme = await self.github.get_readme(owner, repo_name)
            
            # Fetch repository tree
            tree = await self.github.get_repository_tree(owner, repo_name)
            
            # Filter important files
            important_files = self.file_filter.filter_important_files(tree, max_files=30)
            
            # Fetch content of important files (limited to prevent overload)
            file_contents = {}
            for file_info in important_files[:10]:  # Limit to 10 files
                content = await self.github.get_file_content(owner, repo_name, file_info['path'])
                if content and len(content) < 10000:  # Skip very large files
                    file_contents[file_info['path']] = content[:2000]  # Truncate for context
            
            # Fetch issues
            open_issues = await self.github.get_issues(owner, repo_name, state="open", max_issues=30)
            closed_issues = await self.github.get_issues(owner, repo_name, state="closed", max_issues=20)
            
            # Build context for LLM
            context = {
                'repo_name': f"{owner}/{repo_name}",
                'primary_language': metadata.get('language'),
                'readme': readme,
                'files': important_files,
                'all_files': important_files,
                'config_files': [f for f in important_files if f['role'] == 'configuration'],
                'source_files': [f for f in important_files if f['role'] in ['source_code', 'entry_point']],
                'file_contents': json.dumps(file_contents, indent=2),
                'open_issues': open_issues,
                'closed_issues': closed_issues
            }
            
            # Generate analysis using Gemini
            
            # 1. Project Overview
            overview = await self.gemini.analyze_project_overview(context)
            
            # 2. Tech Stack
            tech_stack_data = await self.gemini.analyze_tech_stack(context)
            
            # Store tech stack
            for tech_item in tech_stack_data:
                tech_id = str(uuid.uuid4())
                tech = TechStack(
                    id=tech_id,
                    repo_id=repo_id,
                    name=tech_item.get('name', 'Unknown'),
                    category=tech_item.get('category', 'Other'),
                    reasoning=tech_item.get('reasoning', '')
                )
                db.add(tech)
            
            # 3. Architecture Analysis
            arch_data = await self.gemini.analyze_architecture(context)
            
            arch_summary = ArchitectureSummary(
                repo_id=repo_id,
                overview=ensure_string(arch_data.get('overview')),
                components=ensure_string(arch_data.get('components')),
                data_flow=ensure_string(arch_data.get('data_flow'))
            )
            
            # Check if architecture summary exists
            result = await db.execute(
                select(ArchitectureSummary).where(ArchitectureSummary.repo_id == repo_id)
            )
            existing_arch = result.scalar_one_or_none()
            
            if existing_arch:
                existing_arch.overview = arch_summary.overview
                existing_arch.components = arch_summary.components
                existing_arch.data_flow = arch_summary.data_flow
            else:
                db.add(arch_summary)
            
            # 4. Issues Analysis
            issues_data = await self.gemini.analyze_issues(context)

            issues_insights = IssuesInsights(
                repo_id=repo_id,
                recurring_problems=ensure_string(issues_data.get('recurring_problems', '')),
                risky_areas=ensure_string(issues_data.get('risky_areas', '')),
                active_features=ensure_string(issues_data.get('active_features', ''))
            )
            
            result = await db.execute(
                select(IssuesInsights).where(IssuesInsights.repo_id == repo_id)
            )
            existing_issues = result.scalar_one_or_none()
            
            if existing_issues:
                existing_issues.recurring_problems = issues_insights.recurring_problems
                existing_issues.risky_areas = issues_insights.risky_areas
                existing_issues.active_features = issues_insights.active_features
            else:
                db.add(issues_insights)
            
            # 5. Contributor Guide
            guide_context = {
                **context,
                'tech_stack': tech_stack_data,
                'architecture_overview': arch_data.get('overview', ''),
                'recurring_problems': issues_data.get('recurring_problems', ''),
                'risky_areas': issues_data.get('risky_areas', '')
            }
            
            guide_data = await self.gemini.generate_contributor_guide(guide_context)
            
            contributor_guide = ContributorGuide(
                repo_id=repo_id,
                getting_started=ensure_string(guide_data.get('getting_started')),
                safe_areas=ensure_string(guide_data.get('safe_areas')),
                caution_areas=ensure_string(guide_data.get('caution_areas')),
                feature_extension_guide=ensure_string(guide_data.get('feature_extension_guide'))
            )
            
            result = await db.execute(
                select(ContributorGuide).where(ContributorGuide.repo_id == repo_id)
            )
            existing_guide = result.scalar_one_or_none()
            
            if existing_guide:
                existing_guide.getting_started = contributor_guide.getting_started
                existing_guide.safe_areas = contributor_guide.safe_areas
                existing_guide.caution_areas = contributor_guide.caution_areas
                existing_guide.feature_extension_guide = contributor_guide.feature_extension_guide
            else:
                db.add(contributor_guide)
            
            # 6. Store file information
            for file_info in important_files[:30]:
                file_id = str(uuid.uuid4())
                repo_file = RepoFile(
                    id=file_id,
                    repo_id=repo_id,
                    file_path=file_info['path'],
                    language=file_info.get('language', 'Unknown'),
                    role=file_info.get('role', 'other'),
                    summary=f"Priority: {file_info.get('priority', 0)}"
                )
                db.add(repo_file)
            
            # Mark session as completed
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            
            await db.commit()
            
            return repo_id
            
        except Exception as e:
            # Mark session as failed (if session was created)
            if session is not None:
                session.status = "failed"
            session.completed_at = datetime.utcnow()
            await db.commit()
            raise ValueError(f"Analysis failed: {str(e)}")
    
    async def answer_question(self, repo_id: str, question: str, db: AsyncSession) -> Dict:
        """Answer a question about the repository."""
        # Fetch repository data
        result = await db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise ValueError(f"Repository not found: {repo_id}")
        
        # Fetch architecture summary
        result = await db.execute(
            select(ArchitectureSummary).where(ArchitectureSummary.repo_id == repo_id)
        )
        arch = result.scalar_one_or_none()
        
        # Fetch tech stack
        result = await db.execute(
            select(TechStack).where(TechStack.repo_id == repo_id)
        )
        tech_stack = result.scalars().all()
        
        # Fetch contributor guide
        result = await db.execute(
            select(ContributorGuide).where(ContributorGuide.repo_id == repo_id)
        )
        guide = result.scalar_one_or_none()
        
        # Fetch files
        result = await db.execute(
            select(RepoFile).where(RepoFile.repo_id == repo_id)
        )
        files = result.scalars().all()
        
        # Build context
        context = {
            'repo_name': f"{repository.owner}/{repository.name}",
            'overview': arch.overview if arch else '',
            'architecture': arch.data_flow if arch else '',
            'tech_stack': [{'name': t.name, 'category': t.category} for t in tech_stack],
            'files': [{'file_path': f.file_path, 'role': f.role} for f in files],
            'additional_info': ''
        }
        
        # Check if question is about a specific file
        question_lower = question.lower()
        for file in files:
            if file.file_path.lower() in question_lower:
                context['additional_info'] += f"\nFile: {file.file_path}\nRole: {file.role}\nLanguage: {file.language}\n"
        
        # Generate answer
        answer = await self.gemini.answer_question(question, context)
        
        # Store Q&A log
        qa_id = str(uuid.uuid4())
        qa_log = QALog(
            id=qa_id,
            repo_id=repo_id,
            question=question,
            answer=answer,
            created_at=datetime.utcnow()
        )
        db.add(qa_log)
        await db.commit()
        
        return {
            'repo_id': repo_id,
            'question': question,
            'answer': answer,
            'created_at': qa_log.created_at
        }