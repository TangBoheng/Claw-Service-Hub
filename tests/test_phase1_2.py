"""
Test script for Phase 1-2: SkillMetadata + skill.md

This test verifies:
1. ToolService has new fields (emoji, requires)
2. to_metadata_dict() returns lightweight metadata
3. ServiceRegistry can store and retrieve skill.md
4. Client can load and send skill_doc
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.registry import ToolService, ServiceRegistry


def test_tool_service_metadata():
    """Test ToolService metadata fields"""
    print("\n[Test 1] ToolService metadata fields")

    service = ToolService(
        id="test-123",
        name="test-service",
        description="A test service",
        emoji="🧪",
        requires={"bins": ["python"], "env": ["API_KEY"]},
        tags=["test", "demo"]
    )

    # Verify fields
    assert service.emoji == "🧪", "emoji field not set correctly"
    assert service.requires == {"bins": ["python"], "env": ["API_KEY"]}, "requires field not set correctly"

    # Test to_metadata_dict
    metadata = service.to_metadata_dict()
    assert "emoji" in metadata, "emoji not in metadata"
    assert "requires" in metadata, "requires not in metadata"
    assert metadata["emoji"] == "🧪"
    assert metadata["requires"]["bins"] == ["python"]

    print("  ✓ ToolService metadata fields work correctly")
    print(f"  ✓ Metadata: {metadata}")


async def test_skill_doc_storage():
    """Test ServiceRegistry skill.md storage"""
    print("\n[Test 2] ServiceRegistry skill.md storage")

    registry = ServiceRegistry()

    service = ToolService(
        id="",  # 空ID，注册时会自动生成
        name="doc-service",
        description="Service with documentation"
    )

    skill_doc = """---
name: doc-service
description: A documented service
---

# Full Documentation

This is the complete skill.md content.
"""

    # Register with skill_doc
    service_id = await registry.register(service, skill_doc)

    # Verify skill_doc is stored
    retrieved_doc = registry.get_skill_doc(service_id)
    assert retrieved_doc == skill_doc, "skill_doc not stored correctly"

    # Verify service is stored
    retrieved_service = registry.get(service_id)
    assert retrieved_service is not None, "service not found"
    assert retrieved_service.name == "doc-service"

    # Verify metadata list
    metadata_list = registry.list_all_metadata()
    assert len(metadata_list) == 1, "metadata list length incorrect"
    assert metadata_list[0]["name"] == "doc-service"

    # Unregister and verify cleanup
    await registry.unregister(service_id)
    assert registry.get_skill_doc(service_id) is None, "skill_doc not cleaned up"

    print("  ✓ ServiceRegistry skill.md storage works correctly")
    print(f"  ✓ Service ID: {service_id}")


def test_client_skill_loading():
    """Test client skill.md loading"""
    print("\n[Test 3] Client skill.md loading")

    # Create a test skill directory
    test_skill_dir = "/tmp/test-csv-processor-skill"
    os.makedirs(test_skill_dir, exist_ok=True)

    skill_md_content = """---
name: test-csv
description: Test CSV processor
---

# Test Skill

This is test content.
"""

    with open(os.path.join(test_skill_dir, "SKILL.md"), "w") as f:
        f.write(skill_md_content)

    # Import client and test loading
    from client.client import ToolServiceClient

    client = ToolServiceClient(
        name="test-csv",
        skill_dir=test_skill_dir
    )

    # Verify skill_doc is loaded
    assert client.skill_doc == skill_md_content, "skill_doc not loaded correctly"

    # Cleanup
    import shutil
    shutil.rmtree(test_skill_dir)

    print("  ✓ Client skill.md loading works correctly")
    print(f"  ✓ Loaded {len(skill_md_content)} bytes of skill_doc")


async def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Phase 1-2 Tests: SkillMetadata + skill.md")
    print("=" * 50)

    try:
        test_tool_service_metadata()
        await test_skill_doc_storage()
        test_client_skill_loading()

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
