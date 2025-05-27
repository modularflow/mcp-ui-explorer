#!/usr/bin/env python3
"""
Comprehensive test script for the modularized MCP UI Explorer.
This script validates that all components work correctly after modularization.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported correctly."""
    print("🔍 Testing imports...")
    
    try:
        # Test main package imports
        from mcp_ui_explorer import UIExplorer, create_server, main, wrapper
        print("✅ Main package imports successful")
        
        # Test model imports
        from mcp_ui_explorer.models import RegionType, ControlType
        from mcp_ui_explorer.models import (
            ScreenshotUIInput, ClickUIElementInput, KeyboardInputInput,
            PressKeyInput, HotKeyInput, FindNearCursorInput, UITarsInput,
            UIVerificationInput, CreateMemorySummaryInput, DocumentStepInput,
            GetStepStatusInput
        )
        print("✅ Model imports successful")
        
        # Test config imports
        from mcp_ui_explorer.config import get_settings, Settings
        print("✅ Config imports successful")
        
        # Test utils imports
        from mcp_ui_explorer.utils import get_logger, setup_logging, CoordinateConverter
        print("✅ Utils imports successful")
        
        # Test services imports
        from mcp_ui_explorer.services import UITarsService, MemoryService, VerificationService
        print("✅ Services imports successful")
        
        # Test core imports
        from mcp_ui_explorer.core import UIActions, ToolUsageTracker, ActionLogger, StepTracker
        print("✅ Core imports successful")
        
        # Test server imports
        from mcp_ui_explorer.server import create_server, run_server, ServerWrapper
        print("✅ Server imports successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration system."""
    print("\n⚙️ Testing configuration...")
    
    try:
        from mcp_ui_explorer.config import get_settings
        
        settings = get_settings()
        print(f"✅ Settings loaded: {type(settings).__name__}")
        print(f"   - UI-TARS API URL: {settings.ui_tars.api_url}")
        print(f"   - Memory enabled: {settings.memory.enabled}")
        print(f"   - Log level: {settings.logging.level}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        traceback.print_exc()
        return False

def test_ui_explorer_creation():
    """Test UIExplorer instantiation."""
    print("\n🎯 Testing UIExplorer creation...")
    
    try:
        from mcp_ui_explorer import UIExplorer
        
        explorer = UIExplorer()
        print("✅ UIExplorer created successfully")
        print(f"   - Tool usage tracker: {type(explorer.tool_usage_tracker).__name__}")
        print(f"   - Action logger: {type(explorer.action_logger).__name__}")
        print(f"   - Step tracker: {type(explorer.step_tracker).__name__}")
        print(f"   - UI-TARS service: {type(explorer.ui_tars_service).__name__}")
        print(f"   - Memory service: {type(explorer.memory_service).__name__}")
        print(f"   - Verification service: {type(explorer.verification_service).__name__}")
        print(f"   - UI actions: {type(explorer.ui_actions).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ UIExplorer creation failed: {e}")
        traceback.print_exc()
        return False

def test_server_creation():
    """Test MCP server creation."""
    print("\n🖥️ Testing server creation...")
    
    try:
        from mcp_ui_explorer import create_server
        
        server = create_server()
        print("✅ MCP server created successfully")
        print(f"   - Server type: {type(server).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        traceback.print_exc()
        return False

def test_coordinate_converter():
    """Test coordinate conversion utilities."""
    print("\n📐 Testing coordinate converter...")
    
    try:
        from mcp_ui_explorer.utils import CoordinateConverter
        
        converter = CoordinateConverter(screen_width=1920, screen_height=1080)
        
        # Test absolute to normalized
        normalized = converter.absolute_to_normalized(960, 540)
        print(f"✅ Absolute (960, 540) -> Normalized {normalized}")
        
        # Test normalized to absolute
        absolute = converter.normalized_to_absolute(0.5, 0.5)
        print(f"✅ Normalized (0.5, 0.5) -> Absolute {absolute}")
        
        return True
        
    except Exception as e:
        print(f"❌ Coordinate converter test failed: {e}")
        traceback.print_exc()
        return False

def test_model_validation():
    """Test Pydantic model validation."""
    print("\n📋 Testing model validation...")
    
    try:
        from mcp_ui_explorer.models import ScreenshotUIInput, ClickUIElementInput
        
        # Test valid input
        screenshot_input = ScreenshotUIInput(region="screen", min_size=20)
        print(f"✅ ScreenshotUIInput validation: {screenshot_input.region}")
        
        click_input = ClickUIElementInput(x=100, y=200, wait_time=2.0)
        print(f"✅ ClickUIElementInput validation: ({click_input.x}, {click_input.y})")
        
        # Test invalid input
        try:
            invalid_input = ClickUIElementInput(x="invalid", y=200)
            print("❌ Should have failed validation")
            return False
        except Exception:
            print("✅ Invalid input correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Model validation test failed: {e}")
        traceback.print_exc()
        return False

async def test_async_functionality():
    """Test async functionality."""
    print("\n⚡ Testing async functionality...")
    
    try:
        from mcp_ui_explorer import UIExplorer
        
        explorer = UIExplorer()
        
        # Test step tracking
        result = await explorer.document_step("Test step for validation")
        print(f"✅ Async step documentation: {result['success']}")
        
        status = await explorer.get_step_status()
        print(f"✅ Async step status: {len(status.get('steps', []))} steps tracked")
        
        return True
        
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_package_structure():
    """Test package structure and organization."""
    print("\n📁 Testing package structure...")
    
    try:
        import mcp_ui_explorer
        from pathlib import Path
        
        package_path = Path(mcp_ui_explorer.__file__).parent
        
        # Check for expected directories
        expected_dirs = ['models', 'config', 'utils', 'services', 'core', 'server']
        for dir_name in expected_dirs:
            dir_path = package_path / dir_name
            if dir_path.exists():
                print(f"✅ Directory exists: {dir_name}/")
            else:
                print(f"❌ Missing directory: {dir_name}/")
                return False
        
        # Check for __init__.py files
        for dir_name in expected_dirs:
            init_file = package_path / dir_name / "__init__.py"
            if init_file.exists():
                print(f"✅ Init file exists: {dir_name}/__init__.py")
            else:
                print(f"❌ Missing init file: {dir_name}/__init__.py")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Package structure test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting comprehensive modular structure tests...\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_configuration),
        ("UIExplorer Creation", test_ui_explorer_creation),
        ("Server Creation", test_server_creation),
        ("Coordinate Converter", test_coordinate_converter),
        ("Model Validation", test_model_validation),
        ("Package Structure", test_package_structure),
    ]
    
    async_tests = [
        ("Async Functionality", test_async_functionality),
    ]
    
    results = []
    
    # Run synchronous tests
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Run asynchronous tests
    for test_name, test_func in async_tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The modular structure is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the output above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 