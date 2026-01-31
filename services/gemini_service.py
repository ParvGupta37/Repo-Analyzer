"""
Gemini 3 LLM service for generating analysis and answering questions.
Uses the new Google GenAI SDK with Gemini 3 models.
Includes fallback mock implementation if Gemini SDK is unavailable.
"""
import os
import json
from typing import Dict, List, Optional

# Try to import Google GenAI SDK, fall back to mock if unavailable
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiService:
    """Service for interacting with Gemini 3 LLM or mock fallback."""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model_name = None
        self.using_mock = False
        
        # Allow selection between Gemini 3 Flash and Pro via environment variable
        # Default to Flash for better speed/cost ratio
        gemini_model = os.getenv("GEMINI_MODEL", "flash")  # Options: "flash" or "pro"
        
        if GEMINI_AVAILABLE and self.api_key:
            # Initialize Google GenAI client
            self.client = genai.Client(api_key=self.api_key)
            
            # Select Gemini 3 model based on configuration
            if gemini_model.lower() == "pro":
                self.model_name = 'gemini-3-pro-preview'
            else:
                self.model_name = 'gemini-3-flash-preview'
        else:
            self.using_mock = True
    
    async def generate_content(self, prompt: str) -> str:
        """Generate content using Gemini 3 or mock."""
        if self.client and self.model_name:
            try:
                # Use the new Google GenAI SDK syntax
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                print(f"Gemini 3 API error: {str(e)}")
                return self._mock_response(prompt)
        else:
            return self._mock_response(prompt)
    
    def _mock_response(self, prompt: str) -> str:
        """
        Mock implementation that returns deterministic placeholder text.
        Used when Gemini SDK is unavailable or API key is not configured.
        """
        if "PROJECT OVERVIEW" in prompt:
            return """This repository appears to be a well-structured software project with clear organization and modern development practices. The codebase demonstrates professional software engineering principles with proper separation of concerns and modular architecture."""
        
        elif "TECH STACK" in prompt:
            return json.dumps([
                {
                    "name": "Python",
                    "category": "Programming Language",
                    "reasoning": "Primary language based on file extensions and project structure"
                },
                {
                    "name": "FastAPI",
                    "category": "Web Framework",
                    "reasoning": "Detected from configuration files and import statements"
                }
            ])
        
        elif "ARCHITECTURE" in prompt:
            components = [
                {"name": "API Layer", "description": "Handles HTTP requests and responses"},
                {"name": "Business Logic", "description": "Core application logic and processing"},
                {"name": "Data Layer", "description": "Database interactions and persistence"}
            ]
            return json.dumps({
                "overview": "The architecture follows a layered pattern with clear separation between API, business logic, and data layers.",
                "components": components,
                "data_flow": "Requests flow from API layer through business logic to data layer and back."
            })
        
        elif "ISSUES ANALYSIS" in prompt:
            return json.dumps({
                "recurring_problems": "Common issues include dependency management and configuration challenges.",
                "risky_areas": "Areas requiring careful attention include authentication and data validation.",
                "active_features": "Recent development focuses on performance optimization and user experience improvements."
            })
        
        elif "CONTRIBUTOR GUIDE" in prompt:
            return json.dumps({
                "getting_started": "1. Clone the repository\n2. Install dependencies\n3. Set up configuration files\n4. Run tests to verify setup",
                "safe_areas": "Documentation, test files, and utility functions are safe areas for new contributors.",
                "caution_areas": "Core business logic and database schemas require careful review before modification.",
                "feature_extension_guide": "Follow the existing patterns in the codebase. Add new features in dedicated modules and include comprehensive tests."
            })
        
        elif "ANSWER THE QUESTION" in prompt:
            # Extract question from prompt for context
            question_lower = prompt.lower()
            
            if "purpose" in question_lower or "what does" in question_lower:
                return "Based on the repository structure and codebase, this component handles specific functionality within the application. It integrates with other modules to provide core features."
            elif "how" in question_lower:
                return "The implementation follows standard patterns for this type of functionality. It uses appropriate libraries and frameworks to achieve its goals efficiently."
            elif "why" in question_lower:
                return "This design choice was likely made to ensure maintainability, scalability, and adherence to best practices in software development."
            else:
                return "Based on the repository analysis, the answer depends on the specific context and requirements. Please refer to the documentation and source code for detailed information."
        
        else:
            return "Analysis complete. This is a mock response - configure Gemini API key for detailed analysis."
    
    async def analyze_project_overview(self, context: Dict) -> str:
        """Generate project overview from repository context."""
        prompt = f"""
Analyze this GitHub repository and provide a comprehensive PROJECT OVERVIEW.

Repository: {context.get('repo_name')}
Primary Language: {context.get('primary_language')}

README Content:
{context.get('readme', 'No README available')[:2000]}

Key Files:
{self._format_file_list(context.get('files', [])[:10])}

Provide a clear, concise overview of what this project does, its main purpose, and key features.
Write 2-3 paragraphs. Be specific and informative.
"""
        return await self.generate_content(prompt)
    
    async def analyze_tech_stack(self, context: Dict) -> List[Dict]:
        """Analyze and extract technology stack."""
        prompt = f"""
Analyze this repository's TECH STACK.

Repository: {context.get('repo_name')}
Primary Language: {context.get('primary_language')}

Configuration Files Found:
{self._format_file_list(context.get('config_files', []))}

Source Files:
{self._format_file_list(context.get('source_files', [])[:15])}

File Contents Summary:
{context.get('file_contents', 'Limited content available')[:1500]}

Return a JSON array of technology stack items. Each item should have:
- name: Technology name
- category: Category (e.g., "Framework", "Database", "Language", "Library", "Tool")
- reasoning: Brief explanation of why this technology is identified

Return ONLY valid JSON array, no additional text.
"""
        response = await self.generate_content(prompt)
        
        try:
            # Try to parse JSON response
            tech_stack = json.loads(response)
            if isinstance(tech_stack, list):
                return tech_stack
        except json.JSONDecodeError:
            pass
        
        # Fallback: return minimal tech stack
        return [
            {
                "name": context.get('primary_language', 'Unknown'),
                "category": "Programming Language",
                "reasoning": "Primary language of the repository"
            }
        ]
    
    async def analyze_architecture(self, context: Dict) -> Dict:
        """Analyze system architecture."""
        prompt = f"""
Analyze the ARCHITECTURE of this repository.

Repository: {context.get('repo_name')}

Project Structure:
{self._format_file_list(context.get('all_files', [])[:30])}

Key Source Files:
{self._format_file_list(context.get('source_files', [])[:20])}

Provide a JSON object with:
- overview: High-level architecture description (2-3 sentences)
- components: Array of main components, each with "name" and "description"
- data_flow: Description of how data flows through the system

Return ONLY valid JSON, no additional text.
"""
        response = await self.generate_content(prompt)
        
        try:
            arch_data = json.loads(response)
            if isinstance(arch_data, dict):
                return arch_data
        except json.JSONDecodeError:
            pass
        
        # Fallback
        return {
            "overview": "Modular architecture with separated concerns.",
            "components": [{"name": "Core", "description": "Main application logic"}],
            "data_flow": "Standard data flow patterns."
        }
    
    async def analyze_issues(self, context: Dict) -> Dict:
        """Analyze GitHub issues for insights."""
        prompt = f"""
Analyze these GitHub ISSUES to identify patterns and insights.

Repository: {context.get('repo_name')}

Open Issues ({len(context.get('open_issues', []))}):
{self._format_issues(context.get('open_issues', [])[:15])}

Recently Closed Issues ({len(context.get('closed_issues', []))}):
{self._format_issues(context.get('closed_issues', [])[:10])}

Provide a JSON object with:
- recurring_problems: Common problems or bug patterns
- risky_areas: Areas of code that seem problematic
- active_features: Features being actively developed

Return ONLY valid JSON, no additional text.
"""
        response = await self.generate_content(prompt)
        
        try:
            issues_data = json.loads(response)
            if isinstance(issues_data, dict):
                return issues_data
        except json.JSONDecodeError:
            pass
        
        # Fallback
        return {
            "recurring_problems": "No significant patterns identified.",
            "risky_areas": "Review areas with frequent changes.",
            "active_features": "Check open issues for active development."
        }
    
    async def generate_contributor_guide(self, context: Dict) -> Dict:
        """Generate contributor guide."""
        prompt = f"""
Create a CONTRIBUTOR GUIDE for new developers joining this project.

Repository: {context.get('repo_name')}
Tech Stack: {', '.join([t.get('name', '') for t in context.get('tech_stack', [])])}

Architecture Overview:
{context.get('architecture_overview', 'Not available')}

Issues Insights:
Recurring Problems: {context.get('recurring_problems', 'None identified')}
Risky Areas: {context.get('risky_areas', 'None identified')}

Provide a JSON object with:
- getting_started: Step-by-step guide for new contributors
- safe_areas: Parts of codebase safe for beginners
- caution_areas: Parts requiring careful attention
- feature_extension_guide: How to add new features

Return ONLY valid JSON, no additional text.
"""
        response = await self.generate_content(prompt)
        
        try:
            guide_data = json.loads(response)
            if isinstance(guide_data, dict):
                return guide_data
        except json.JSONDecodeError:
            pass
        
        # Fallback
        return {
            "getting_started": "Clone repository, install dependencies, run tests.",
            "safe_areas": "Documentation and test files.",
            "caution_areas": "Core business logic.",
            "feature_extension_guide": "Follow existing patterns."
        }
    
    async def answer_question(self, question: str, context: Dict) -> str:
        """Answer a question about the repository."""
        prompt = f"""
ANSWER THE QUESTION about this repository using the provided context.

Repository: {context.get('repo_name')}

Question: {question}

Context Available:
- Project Overview: {context.get('overview', 'Not available')[:500]}
- Architecture: {context.get('architecture', 'Not available')[:500]}
- Tech Stack: {', '.join([t.get('name', '') for t in context.get('tech_stack', [])])}
- Files: {len(context.get('files', []))} files analyzed

Additional Context:
{context.get('additional_info', '')}

Provide a clear, accurate, and helpful answer based on the repository context.
If the answer isn't clear from the context, say so and provide the best inference you can make.
"""
        return await self.generate_content(prompt)
    
    def _format_file_list(self, files: List) -> str:
        """Format file list for prompt."""
        if not files:
            return "No files"
        
        formatted = []
        for f in files[:20]:  # Limit to prevent prompt overflow
            if isinstance(f, dict):
                formatted.append(f"- {f.get('path', f.get('file_path', 'unknown'))}")
            else:
                formatted.append(f"- {f}")
        return "\n".join(formatted)
    
    def _format_issues(self, issues: List[Dict]) -> str:
        """Format issues for prompt."""
        if not issues:
            return "No issues"
        
        formatted = []
        for issue in issues[:10]:
            title = issue.get('title', 'No title')
            labels = ', '.join([l.get('name', '') for l in issue.get('labels', [])])
            formatted.append(f"- {title} [{labels}]")
        
        return "\n".join(formatted)