# NeuroAnim Improvements Guide

This document outlines improvements made and further recommendations for enhancing the NeuroAnim system's code generation, script writing, and overall quality.

---

## ✅ Issues Fixed

### 1. Audio Generation Problem - RESOLVED

**Problem:** Narration text contained prefixes like "Narration Script:\n\n" which were being sent to TTS, causing poor audio quality or failures.

**Solution Implemented:**
- Added `_clean_narration_text()` method in `orchestrator.py` that strips prefixes and formatting artifacts
- Updated `generate_narration()` in `mcp_servers/creative.py` to return clean text without prefixes
- Improved prompt to explicitly instruct the model not to add labels

**Location:** 
- `orchestrator.py` lines 353-389 (new method)
- `mcp_servers/creative.py` lines 558-608 (improved prompt and cleaning)

---

## 🎯 Recommendations for Further Improvements

### 2. Manim Code Generation Quality

#### Current Issues:
- Syntax errors (unclosed parentheses, brackets)
- Invalid color names (DARK_GREEN, LIGHT_BLUE don't exist in Manim)
- Incorrect animation method names (using lowercase instead of capitalized)
- Missing imports or incomplete code blocks
- Using deprecated Manim classes or methods

#### Improvements Made:
✅ Enhanced prompts in `mcp_servers/creative.py` with explicit requirements:
- List of valid color constants
- Correct animation method names with capitalization
- Use of `MovingCameraScene` for better flexibility
- Syntax validation requirements

#### Additional Recommendations:

**A. Add Code Post-Processing Pipeline**

Create `utils/code_validator.py`:

```python
import ast
import re
from typing import Dict, List, Optional

class ManimCodeValidator:
    """Validate and fix common Manim code issues."""
    
    VALID_COLORS = {
        'WHITE', 'BLACK', 'GRAY', 'GREY', 'LIGHT_GRAY', 'DARK_GRAY',
        'RED', 'GREEN', 'BLUE', 'YELLOW', 'ORANGE', 'PINK', 'PURPLE',
        'TEAL', 'GOLD', 'MAROON', 'RED_A', 'RED_B', 'RED_C', 'RED_D',
        'RED_E', 'GREEN_A', 'GREEN_B', 'GREEN_C', 'GREEN_D', 'GREEN_E',
        'BLUE_A', 'BLUE_B', 'BLUE_C', 'BLUE_D', 'BLUE_E'
    }
    
    INVALID_COLOR_REPLACEMENTS = {
        'DARK_GREEN': 'GREEN_D',
        'LIGHT_GREEN': 'GREEN_A',
        'DARK_BLUE': 'BLUE_D',
        'LIGHT_BLUE': 'BLUE_A',
        'DARK_RED': 'RED_D',
        'LIGHT_RED': 'RED_A',
    }
    
    @staticmethod
    def validate_syntax(code: str) -> Dict[str, any]:
        """Check if code has valid Python syntax."""
        try:
            ast.parse(code)
            return {"valid": True, "errors": []}
        except SyntaxError as e:
            return {
                "valid": False,
                "errors": [f"Syntax error at line {e.lineno}: {e.msg}"]
            }
    
    @staticmethod
    def fix_colors(code: str) -> str:
        """Replace invalid color names with valid ones."""
        for invalid, valid in ManimCodeValidator.INVALID_COLOR_REPLACEMENTS.items():
            code = re.sub(rf'\b{invalid}\b', valid, code)
        return code
    
    @staticmethod
    def ensure_imports(code: str) -> str:
        """Ensure proper Manim imports exist."""
        if 'from manim import' not in code and 'import manim' not in code:
            code = 'from manim import *\n\n' + code
        return code
    
    @staticmethod
    def fix_common_issues(code: str) -> str:
        """Apply common fixes to generated code."""
        # Fix colors
        code = ManimCodeValidator.fix_colors(code)
        
        # Ensure imports
        code = ManimCodeValidator.ensure_imports(code)
        
        # Fix common typos in animation methods
        typo_fixes = {
            r'\.fadein\(': '.FadeIn(',
            r'\.fadeout\(': '.FadeOut(',
            r'\.write\(': '.Write(',
            r'\.create\(': '.Create(',
            r'self\.play\(flash\(': 'self.play(Flash(',
            r'self\.play\(indicate\(': 'self.play(Indicate(',
        }
        
        for pattern, replacement in typo_fixes.items():
            code = re.sub(pattern, replacement, code, flags=re.IGNORECASE)
        
        return code
```

**B. Implement Multi-Stage Validation**

In `orchestrator.py`, enhance `_generate_and_validate_code()`:

```python
async def _generate_and_validate_code(
    self, topic: str, concept_plan: str, max_retries: int = 3
) -> str:
    """Generate and validate Manim code with multiple checks."""
    
    from utils.code_validator import ManimCodeValidator
    validator = ManimCodeValidator()
    
    for attempt in range(max_retries):
        # Generate code
        code_result = await self.call_tool(...)
        raw_code = self._extract_python_code(code_result["text"])
        
        # Stage 1: Fix common issues
        fixed_code = validator.fix_common_issues(raw_code)
        
        # Stage 2: Syntax validation
        syntax_check = validator.validate_syntax(fixed_code)
        if not syntax_check["valid"]:
            logger.warning(f"Syntax error in attempt {attempt + 1}")
            # Retry with error feedback
            continue
        
        # Stage 3: Test import (optional, quick check)
        try:
            compile(fixed_code, '<string>', 'exec')
        except Exception as e:
            logger.warning(f"Compilation error: {e}")
            continue
        
        return fixed_code
    
    raise Exception("Failed to generate valid code after retries")
```

**C. Use Few-Shot Examples in Prompts**

Add working examples to the code generation prompt:

```python
EXAMPLE_CODE = '''
from manim import *

class ExampleScene(MovingCameraScene):
    def construct(self):
        # Title
        title = Text("Example Animation", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        
        # Create objects
        circle = Circle(radius=1, color=BLUE)
        square = Square(side_length=2, color=RED)
        square.next_to(circle, RIGHT, buff=1)
        
        # Animate
        self.play(Create(circle), Create(square))
        self.wait(1)
        self.play(circle.animate.shift(RIGHT * 2))
        self.wait(1)
'''

# Include in prompt:
prompt = f"""
Here's an example of proper Manim code structure:

{EXAMPLE_CODE}

Now generate similar code for: {concept}
...
"""
```

---

### 3. Script Writing (Narration) Quality

#### Current Issues:
- Sometimes too technical or too simple for the audience
- Inconsistent pacing
- May include unnecessary conversational elements
- Duration mismatch with actual content

#### Improvements Made:
✅ Completely rewritten prompt in `mcp_servers/creative.py`:
- Clear instruction to output only spoken text
- Word count guidance based on duration
- Explicit formatting requirements
- Post-processing to remove prefixes

#### Additional Recommendations:

**A. Add Narration Quality Scoring**

Create `utils/narration_analyzer.py`:

```python
class NarrationAnalyzer:
    """Analyze and score narration quality."""
    
    @staticmethod
    def estimate_duration(text: str, wpm: int = 150) -> float:
        """Estimate speaking duration in seconds."""
        word_count = len(text.split())
        return (word_count / wpm) * 60
    
    @staticmethod
    def check_reading_level(text: str) -> Dict:
        """Analyze text complexity."""
        # Could use textstat library
        import textstat
        
        return {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "grade_level": textstat.flesch_kincaid_grade(text),
            "syllable_count": textstat.syllable_count(text),
        }
    
    @staticmethod
    def validate_audience_match(text: str, audience: str) -> bool:
        """Check if text matches target audience."""
        grade_map = {
            "elementary": (3, 5),
            "middle_school": (6, 8),
            "high_school": (9, 12),
            "undergraduate": (13, 16),
        }
        
        if audience not in grade_map:
            return True
        
        min_grade, max_grade = grade_map[audience]
        actual_grade = textstat.flesch_kincaid_grade(text)
        
        return min_grade <= actual_grade <= max_grade + 2
```

**B. Implement Iterative Refinement**

```python
async def generate_refined_narration(self, topic, audience, duration, max_attempts=2):
    """Generate narration with quality checks and refinement."""
    
    analyzer = NarrationAnalyzer()
    
    for attempt in range(max_attempts):
        # Generate narration
        narration = await self.generate_narration(...)
        
        # Check duration match
        estimated_duration = analyzer.estimate_duration(narration)
        target_duration = duration * 60
        
        if abs(estimated_duration - target_duration) > 15:  # 15 sec tolerance
            feedback = f"Duration mismatch: got {estimated_duration}s, need {target_duration}s"
            # Regenerate with feedback
            continue
        
        # Check audience match
        if not analyzer.validate_audience_match(narration, audience):
            feedback = f"Complexity doesn't match {audience} level"
            continue
        
        return narration
    
    # Return best attempt even if not perfect
    return narration
```

**C. Use Structured Output Format**

Modify prompt to request JSON structure:

```python
prompt = f"""
Generate narration in JSON format:

{{
    "narration": "The actual spoken text...",
    "key_points": ["point 1", "point 2"],
    "transitions": ["0:00 - Introduction", "0:30 - Main concept"],
    "emphasis_words": ["important", "theorem", "result"]
}}

Topic: {concept}
Audience: {target_audience}
Duration: {duration} seconds
"""

# Parse and extract just the narration part
result = json.loads(response)
narration_text = result["narration"]
```

---

### 4. Overall System Improvements

#### A. Add Caching Layer

Save generated components to avoid regeneration:

```python
import hashlib
import json
from pathlib import Path

class GenerationCache:
    """Cache generated content."""
    
    def __init__(self, cache_dir: Path = Path("cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_hash(self, topic: str, params: Dict) -> str:
        """Generate cache key."""
        key = f"{topic}_{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def get_narration(self, topic: str, audience: str) -> Optional[str]:
        """Retrieve cached narration."""
        key = self._get_hash(topic, {"audience": audience, "type": "narration"})
        cache_file = self.cache_dir / f"{key}.txt"
        
        if cache_file.exists():
            return cache_file.read_text()
        return None
    
    def save_narration(self, topic: str, audience: str, content: str):
        """Save narration to cache."""
        key = self._get_hash(topic, {"audience": audience, "type": "narration"})
        cache_file = self.cache_dir / f"{key}.txt"
        cache_file.write_text(content)
```

#### B. Implement Quality Metrics Dashboard

Track generation success rates, error types, average durations:

```python
class MetricsCollector:
    """Collect and report system metrics."""
    
    def __init__(self):
        self.metrics = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "errors": {},
            "average_duration": 0,
        }
    
    def record_success(self, duration: float):
        self.metrics["total_generations"] += 1
        self.metrics["successful_generations"] += 1
        self._update_average_duration(duration)
    
    def record_failure(self, error_type: str):
        self.metrics["total_generations"] += 1
        self.metrics["failed_generations"] += 1
        self.metrics["errors"][error_type] = self.metrics["errors"].get(error_type, 0) + 1
    
    def get_report(self) -> Dict:
        """Get metrics report."""
        success_rate = (
            self.metrics["successful_generations"] / self.metrics["total_generations"]
            if self.metrics["total_generations"] > 0
            else 0
        )
        
        return {
            **self.metrics,
            "success_rate": success_rate,
        }
```

#### C. Add Preview Mode

Generate low-quality preview before full render:

```python
async def generate_preview(self, topic: str, audience: str) -> Dict:
    """Generate quick preview without full rendering."""
    
    # Generate only concept plan and narration
    concept = await self.generate_concept(topic, audience)
    narration = await self.generate_narration(topic, concept, audience)
    
    # Generate code but don't render
    code = await self.generate_code(topic, concept)
    
    return {
        "concept": concept,
        "narration": narration,
        "code": code,
        "estimated_duration": len(narration.split()) / 150 * 60,
    }
```

#### D. Error Recovery Strategies

Implement better fallback mechanisms:

```python
class GenerationStrategy:
    """Handle generation with multiple fallback strategies."""
    
    async def generate_with_fallback(self, primary_fn, fallback_fn, *args):
        """Try primary method, fall back if it fails."""
        try:
            return await primary_fn(*args)
        except Exception as e:
            logger.warning(f"Primary method failed: {e}, trying fallback")
            return await fallback_fn(*args)
    
    async def generate_code_resilient(self, topic: str, concept: str):
        """Generate code with multiple strategies."""
        
        strategies = [
            ("Complex with camera", lambda: self.generate_with_camera_scene(topic)),
            ("Simple Scene", lambda: self.generate_simple_scene(topic)),
            ("Template-based", lambda: self.use_code_template(topic)),
        ]
        
        for strategy_name, strategy_fn in strategies:
            try:
                logger.info(f"Trying strategy: {strategy_name}")
                return await strategy_fn()
            except Exception as e:
                logger.warning(f"Strategy {strategy_name} failed: {e}")
                continue
        
        raise Exception("All code generation strategies failed")
```

---

## 📋 Implementation Priority

### High Priority (Immediate)
1. ✅ Fix audio generation (DONE)
2. ✅ Improve narration prompts (DONE)
3. ✅ Add Gradio frontend (DONE)
4. 🔲 Implement code validator with post-processing
5. 🔲 Add syntax validation before rendering

### Medium Priority (Next Sprint)
6. 🔲 Add narration quality analyzer
7. 🔲 Implement caching layer
8. 🔲 Add preview mode
9. 🔲 Enhance error recovery

### Low Priority (Future)
10. 🔲 Metrics dashboard
11. 🔲 Advanced code templates
12. 🔲 Multi-model ensemble for better quality
13. 🔲 User feedback loop for iterative improvement

---

## 🧪 Testing Recommendations

### Unit Tests
```python
def test_narration_cleaning():
    """Test narration text cleaning."""
    dirty = "Narration Script:\n\nThis is the actual text"
    clean = orchestrator._clean_narration_text(dirty)
    assert clean == "This is the actual text"

def test_code_validation():
    """Test Manim code validation."""
    invalid_code = "circle = Circle(color=DARK_GREEN)"
    fixed = validator.fix_colors(invalid_code)
    assert "GREEN_D" in fixed

def test_duration_estimation():
    """Test narration duration estimation."""
    text = "This is a test " * 150  # 150 words
    duration = analyzer.estimate_duration(text, wpm=150)
    assert 59 <= duration <= 61  # Should be ~60 seconds
```

### Integration Tests
```python
async def test_full_pipeline():
    """Test complete generation pipeline."""
    orchestrator = NeuroAnimOrchestrator()
    await orchestrator.initialize()
    
    result = await orchestrator.generate_animation(
        topic="Test Topic",
        target_audience="high_school",
        animation_length_minutes=1.0
    )
    
    assert result["success"]
    assert Path(result["output_file"]).exists()
    assert len(result["narration"]) > 50
    assert "from manim import" in result["manim_code"]
```

---

## 📊 Success Metrics

Track these to measure improvement:

1. **Code Generation Success Rate**: % of generated code that renders without errors
2. **Audio Quality Score**: User ratings or automated speech quality metrics
3. **Narration Accuracy**: Duration match, audience level match
4. **End-to-End Success**: % of complete generations without manual intervention
5. **User Satisfaction**: Feedback scores from Gradio interface

Target Goals:
- Code success rate: >85%
- Audio quality: >4/5
- Duration accuracy: ±10 seconds
- End-to-end success: >75%

---

## 🔧 Configuration Best Practices

Create `config.yaml` for easy tuning:

```yaml
generation:
  max_retries: 3
  timeout_seconds: 300
  
narration:
  words_per_minute: 150
  min_words: 50
  max_words: 1000
  
code_generation:
  temperature: 0.3
  max_tokens: 2048
  default_scene_class: "MovingCameraScene"
  
rendering:
  quality: "medium"
  frame_rate: 30
  format: "mp4"
  
audio:
  primary_provider: "elevenlabs"
  fallback_providers: ["huggingface", "gtts"]
  default_voice: "rachel"
```

---

## 🎓 Educational Content Guidelines

To maximize educational value:

1. **Clear Learning Objectives**: Start narration with "In this video, you'll learn..."
2. **Progressive Complexity**: Build from simple to complex
3. **Visual-Audio Sync**: Time narration with visual reveals
4. **Repetition**: Reinforce key concepts 2-3 times
5. **Real-World Connections**: Include practical applications
6. **Assessment**: Quiz questions that test understanding, not memorization

---

## 📝 Future Enhancements

1. **Multi-Language Support**: Generate narration in multiple languages
2. **Custom Voice Cloning**: Use teacher's voice with ElevenLabs
3. **Interactive Elements**: Clickable annotations in video
4. **Series Generation**: Create multi-video curriculum
5. **Adaptive Learning**: Adjust complexity based on quiz results
6. **Collaborative Editing**: Allow teachers to refine generated content

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Status:** Living document - update as improvements are implemented