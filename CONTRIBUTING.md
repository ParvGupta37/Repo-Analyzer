# Contributing to GitHub Repository Analyzer

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Git
- Virtual environment tool (venv or conda)

### Setup Development Environment

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Repo-Analyzer.git
   cd Repo-Analyzer
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run Tests**
   ```bash
   pytest
   ```

## 📝 Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes
- Write clean, documented code
- Follow existing code style
- Add type hints
- Write docstrings for functions/classes

### 3. Test Your Changes
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_github_service.py

# Run with coverage
pytest --cov=services --cov-report=html
```

### 4. Commit Changes
```bash
git add .
git commit -m "feat: add comparative analysis feature"
```

**Commit Message Format**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Adding tests
- `refactor:` Code refactoring
- `perf:` Performance improvements

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
```
Then create a Pull Request on GitHub.

## 🧪 Testing Guidelines

### Writing Tests
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_analyze_repo_with_invalid_url`
- Mock external API calls (GitHub, Gemini)

### Example Test
```python
import pytest
from services.github_service import GitHubService

@pytest.mark.asyncio
async def test_parse_repo_url_success():
    service = GitHubService()
    owner, repo = service.parse_repo_url("https://github.com/user/repo")
    assert owner == "user"
    assert repo == "repo"
```

## 📐 Code Style

### Python Style Guide
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use async/await for I/O operations

### Example
```python
async def fetch_data(repo_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Fetch repository data from database.
    
    Args:
        repo_id: UUID of the repository
        db: Database session
        
    Returns:
        Dictionary containing repository data
        
    Raises:
        ValueError: If repository not found
    """
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise ValueError(f"Repository not found: {repo_id}")
    
    return {"id": repo.id, "url": repo.repo_url}
```

## 🐛 Reporting Bugs

### Before Submitting
1. Check existing issues
2. Verify bug in latest version
3. Collect error logs and stack traces

### Bug Report Template
```markdown
**Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: Windows 11
- Python: 3.11
- Version: 3.0.0
```

## 💡 Feature Requests

We welcome feature suggestions! Please:
1. Check existing feature requests
2. Describe the use case
3. Explain expected behavior
4. Provide examples if possible

## 🔍 Code Review Process

All submissions require review. We look for:
- ✅ Tests pass
- ✅ Code follows style guide
- ✅ Documentation updated
- ✅ No breaking changes (or clearly documented)
- ✅ Performance impact considered

## 📚 Documentation

When adding features:
- Update README.md
- Add docstrings
- Update API documentation
- Add examples

## 🎯 Areas for Contribution

### Good First Issues
- Adding tests
- Improving documentation
- Fixing typos
- Adding type hints

### Advanced Contributions
- Performance optimizations
- New analysis features
- Dashboard enhancements
- Integration with other services

## 📞 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an Issue
- **Security**: Email maintainers directly

## 📜 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing! 🎉
