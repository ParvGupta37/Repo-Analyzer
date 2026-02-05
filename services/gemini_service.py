"""
Refactored Gemini 3 service - SINGLE API CALL architecture.
Generates all analysis in one structured response to avoid rate limits.
"""
import os
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator

# Try to import Google GenAI SDK
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# ============================================================================
# STRUCTURED OUTPUT SCHEMA - Enforces deterministic, frontend-ready responses
# ============================================================================

class TechStackItem(BaseModel):
    """Single technology in the stack."""
    name: str = Field(..., max_length=50, description="Technology name")
    category: str = Field(..., max_length=30, description="Category (Language/Framework/Database/Tool)")
    version: Optional[str] = Field(None, max_length=20, description="Version if detected")


class ComponentItem(BaseModel):
    """Single architectural component."""
    name: str = Field(..., max_length=50, description="Component name")
    purpose: str = Field(..., max_length=200, description="What this component does")
    files: List[str] = Field(default_factory=list, max_items=5, description="Key files")


class FileInsight(BaseModel):
    """Insight about a specific file."""
    path: str = Field(..., max_length=200)
    role: str = Field(..., max_length=30, description="entry_point/config/core/utility")
    purpose: str = Field(..., max_length=150, description="One-line explanation")


class RepositoryAnalysis(BaseModel):
    """Complete repository analysis - single structured response."""
    
    # Core summary (short, scannable)
    summary: str = Field(..., min_length=50, max_length=300, description="2-3 sentence project summary")
    purpose: str = Field(..., max_length=150, description="What problem this solves")
    
    # Tech stack
    tech_stack: List[TechStackItem] = Field(..., min_items=1, max_items=15)
    primary_language: str = Field(..., max_length=30)
    
    # Architecture
    architecture_pattern: str = Field(..., max_length=50, description="MVC/Microservices/Monolith/etc")
    components: List[ComponentItem] = Field(default_factory=list, max_items=10)
    data_flow: str = Field(..., max_length=300, description="How data moves through the system")
    
    # File organization
    key_files: List[FileInsight] = Field(default_factory=list, max_items=10)
    
    # Setup and contribution
    setup_steps: List[str] = Field(..., min_items=2, max_items=6, description="Setup steps as short strings")
    contribution_areas: List[str] = Field(default_factory=list, max_items=5, description="Safe areas for new contributors")
    
    # Risks and limitations
    risky_areas: List[str] = Field(default_factory=list, max_items=5, description="Areas requiring caution")
    known_issues: List[str] = Field(default_factory=list, max_items=5, description="From GitHub issues analysis")
    
    # Metadata
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Analysis confidence")
    
    @validator('summary', 'purpose', 'data_flow')
    def no_fluff(cls, v):
        """Remove common AI fluff phrases."""
        fluff_phrases = [
            "it's important to note",
            "it should be noted",
            "as mentioned",
            "basically",
            "essentially",
            "in conclusion",
            "to summarize"
        ]
        result = v
        for phrase in fluff_phrases:
            result = result.replace(phrase, "").replace(phrase.title(), "")
        return result.strip()


# ============================================================================
# GEMINI SERVICE - Single call, validated output
# ============================================================================

class GeminiServiceV2:
    """Refactored Gemini service - ONE call per repository analysis."""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model_name = None
        self.using_mock = False
        
        gemini_model = os.getenv("GEMINI_MODEL", "flash")
        
        if GEMINI_AVAILABLE and self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = 'gemini-3-pro-preview' if gemini_model.lower() == "pro" else 'gemini-3-flash-preview'
        else:
            self.using_mock = True
    
    async def analyze_repository(self, context: Dict) -> RepositoryAnalysis:
        """
        SINGLE API CALL to analyze entire repository.
        Returns validated, structured, frontend-ready data.
        """
        prompt = self._build_unified_prompt(context)
        
        if self.client and self.model_name:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                raw_text = response.text
                
                # Clean response (remove markdown fences if present)
                if raw_text.strip().startswith("```"):
                    raw_text = raw_text.split("```json")[-1].split("```")[0].strip()
                elif raw_text.strip().startswith("{"):
                    pass  # Already clean JSON
                else:
                    # Try to extract JSON from text
                    import re
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    if json_match:
                        raw_text = json_match.group(0)
                
                # Parse and validate
                data = json.loads(raw_text)
                analysis = RepositoryAnalysis(**data)
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"Gemini returned invalid JSON: {str(e)}")
                return self._fallback_analysis(context)
            except Exception as e:
                print(f"Gemini API error: {str(e)}")
                return self._fallback_analysis(context)
        else:
            return self._fallback_analysis(context)
    
    def _build_unified_prompt(self, context: Dict) -> str:
        """Build single comprehensive prompt for all analysis."""
        
        repo_name = context.get('repo_name', 'Unknown')
        primary_lang = context.get('primary_language', 'Unknown')
        readme = (context.get('readme') or 'No README available')[:3000]
        
        files_list = "\n".join([
            f"- {f['path']} ({f.get('language', 'unknown')})"
            for f in context.get('files', [])[:20]
        ])
        
        config_files = [f['path'] for f in context.get('config_files', [])[:10]]
        entry_files = [f['path'] for f in context.get('source_files', []) if f.get('role') == 'entry_point'][:5]
        
        issues_summary = f"{len(context.get('open_issues', []))} open, {len(context.get('closed_issues', []))} recently closed"
        
        # Extract issue titles for pattern detection
        issue_titles = [
            issue.get('title', '')
            for issue in (context.get('open_issues', [])[:10] + context.get('closed_issues', [])[:5])
        ]
        
        prompt = f"""Analyze this GitHub repository and return ONLY valid JSON (no markdown, no prose).

Repository: {repo_name}
Primary Language: {primary_lang}

README (first 3000 chars):
{readme}

Key Files:
{files_list}

Configuration Files: {', '.join(config_files) if config_files else 'None detected'}
Entry Points: {', '.join(entry_files) if entry_files else 'Not identified'}

GitHub Issues: {issues_summary}
Recent Issue Patterns: {', '.join(issue_titles[:5]) if issue_titles else 'No issues'}

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON matching this exact schema
2. Use SHORT, SCANNABLE strings (no essays)
3. Be SPECIFIC and EVIDENCE-BASED (no speculation)
4. NO fluff phrases like "it's important to note" or "essentially"
5. Keep arrays to specified max lengths
6. All strings must be concise and frontend-ready

Return JSON with these exact keys:

{{
  "summary": "2-3 sentence explanation of what this project does",
  "purpose": "What problem does this solve (max 150 chars)",
  "tech_stack": [
    {{
      "name": "TechName",
      "category": "Language|Framework|Database|Tool|Library",
      "version": "1.0.0 or null"
    }}
  ],
  "primary_language": "{primary_lang}",
  "architecture_pattern": "MVC|Microservices|Monolith|Library|CLI|etc",
  "components": [
    {{
      "name": "ComponentName",
      "purpose": "What it does (max 200 chars)",
      "files": ["file1.py", "file2.py"]
    }}
  ],
  "data_flow": "How data moves through system (max 300 chars)",
  "key_files": [
    {{
      "path": "path/to/file",
      "role": "entry_point|config|core|utility",
      "purpose": "One-line explanation (max 150 chars)"
    }}
  ],
  "setup_steps": [
    "Step 1: Clone repo",
    "Step 2: Install dependencies",
    "Step 3-6: ..."
  ],
  "contribution_areas": [
    "Documentation",
    "Tests",
    "etc"
  ],
  "risky_areas": [
    "Authentication module",
    "Database migrations"
  ],
  "known_issues": [
    "Issue pattern 1 from GitHub",
    "Issue pattern 2"
  ],
  "confidence_score": 0.9
}}

Analyze based on README and file structure. Use evidence only. Be concise. Return valid JSON only.
"""
        return prompt
    
    def _fallback_analysis(self, context: Dict) -> RepositoryAnalysis:
        """Deterministic fallback when Gemini unavailable."""
        primary_lang = context.get('primary_language', 'Unknown')
        repo_name = context.get('repo_name', 'Unknown')
        
        return RepositoryAnalysis(
            summary=f"{repo_name} is a {primary_lang} project. Analysis limited due to API constraints.",
            purpose="Project analysis unavailable",
            tech_stack=[
                TechStackItem(
                    name=primary_lang,
                    category="Programming Language",
                    version=None
                )
            ],
            primary_language=primary_lang,
            architecture_pattern="Unknown",
            components=[],
            data_flow="Analysis unavailable",
            key_files=[],
            setup_steps=[
                "Clone repository",
                "Review README for setup instructions"
            ],
            contribution_areas=["Documentation"],
            risky_areas=[],
            known_issues=[],
            confidence_score=0.3
        )
    
    async def answer_question(self, question: str, analysis: RepositoryAnalysis, additional_context: str = "") -> str:
        """
        Answer question using pre-analyzed data.
        This is a SEPARATE call (for Q&A), not part of initial analysis.
        """
        # Build concise context from analysis
        context_str = f"""Repository Analysis:
Summary: {analysis.summary}
Purpose: {analysis.purpose}
Tech Stack: {', '.join([t.name for t in analysis.tech_stack])}
Architecture: {analysis.architecture_pattern}
Components: {', '.join([c.name for c in analysis.components])}

{additional_context}
"""
        
        prompt = f"""Answer this question about the repository. Be CONCISE (max 100 words).

Question: {question}

Context:
{context_str}

Rules:
- Answer in 2-4 sentences maximum
- Be specific and direct
- No fluff or filler
- If unsure, say so briefly

Answer:"""
        
        if self.client and self.model_name:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                return f"Unable to answer due to API limitation. Based on analysis: {analysis.summary}"
        else:
            return f"Based on analysis: {analysis.summary[:150]}"