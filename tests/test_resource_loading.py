import os
import tempfile
import unittest
from pathlib import Path

from summer_core.utils.resource import (
    ClassPathResource,
    DefaultResourceLoader,
    FileSystemResource,
    PathMatchingResourcePatternResolver,
    Resource,
    ResourceLoader,
    UrlResource,
)


class TestResource(unittest.TestCase):
    """Test cases for the Resource interface and implementations."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file_path = os.path.join(self.temp_dir.name, "test.txt")
        with open(self.temp_file_path, "w") as f:
            f.write("test content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_file_system_resource(self):
        """Test FileSystemResource implementation."""
        resource = FileSystemResource(self.temp_file_path)
        
        self.assertTrue(resource.exists())
        self.assertEqual("test.txt", resource.get_filename())
        self.assertEqual(self.temp_file_path, resource.get_path())
        self.assertEqual(f"file:{self.temp_file_path}", resource.get_url())
        self.assertEqual(b"test content", resource.get_content_as_bytes())
        self.assertEqual("test content", resource.get_content_as_string())
        self.assertEqual(12, resource.get_content_length())
        self.assertGreater(resource.get_last_modified(), 0)
    
    def test_classpath_resource(self):
        """Test ClassPathResource implementation."""
        # We'll use the summer_core package which we know exists
        resource = ClassPathResource("summer_core/utils/resource.py")
        
        self.assertTrue(resource.exists())
        self.assertEqual("resource.py", resource.get_filename())
        self.assertEqual("summer_core/utils/resource.py", resource.get_path())
        self.assertEqual("classpath:summer_core/utils/resource.py", resource.get_url())
        self.assertGreater(len(resource.get_content_as_bytes()), 0)
        self.assertGreater(len(resource.get_content_as_string()), 0)
        self.assertGreater(resource.get_content_length(), 0)
        self.assertGreater(resource.get_last_modified(), 0)
    
    def test_url_resource(self):
        """Test UrlResource implementation."""
        # Skip actual URL tests as they require network access
        resource = UrlResource("https://example.com")
        
        self.assertEqual("", resource.get_filename())
        self.assertEqual("/", resource.get_path())
        self.assertEqual("https://example.com", resource.get_url())
    
    def test_non_existent_resource(self):
        """Test behavior with non-existent resources."""
        resource = FileSystemResource("non_existent_file.txt")
        
        self.assertFalse(resource.exists())
        self.assertEqual("non_existent_file.txt", resource.get_filename())
        self.assertEqual(0, resource.get_content_length())
        self.assertEqual(0, resource.get_last_modified())
        
        with self.assertRaises(FileNotFoundError):
            resource.get_content_as_bytes()


class TestResourceLoader(unittest.TestCase):
    """Test cases for the ResourceLoader interface and implementations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loader = DefaultResourceLoader()
        
        # Create a temporary directory with test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file1 = os.path.join(self.temp_dir.name, "test1.txt")
        self.test_file2 = os.path.join(self.temp_dir.name, "test2.txt")
        self.test_subdir = os.path.join(self.temp_dir.name, "subdir")
        os.makedirs(self.test_subdir, exist_ok=True)
        self.test_file3 = os.path.join(self.test_subdir, "test3.txt")
        
        with open(self.test_file1, "w") as f:
            f.write("test1 content")
        with open(self.test_file2, "w") as f:
            f.write("test2 content")
        with open(self.test_file3, "w") as f:
            f.write("test3 content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_get_resource(self):
        """Test getting a resource by location."""
        # File resource
        resource = self.loader.get_resource(f"file:{self.test_file1}")
        self.assertTrue(resource.exists())
        self.assertEqual("test1.txt", resource.get_filename())
        self.assertEqual("test1 content", resource.get_content_as_string())
        
        # Classpath resource (default)
        resource = self.loader.get_resource("summer_core/utils/resource.py")
        self.assertTrue(resource.exists())
        self.assertEqual("resource.py", resource.get_filename())
    
    def test_get_resource_as_string(self):
        """Test getting a resource as a string."""
        content = self.loader.get_resource_as_string(f"file:{self.test_file1}")
        self.assertEqual("test1 content", content)


class TestResourcePatternResolver(unittest.TestCase):
    """Test cases for the ResourcePatternResolver interface and implementations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.resolver = PathMatchingResourcePatternResolver()
        
        # Create a temporary directory with test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        
        # Create test files
        (self.base_dir / "test1.txt").write_text("test1 content")
        (self.base_dir / "test2.txt").write_text("test2 content")
        (self.base_dir / "test.xml").write_text("<test>content</test>")
        
        # Create subdirectories with files
        subdir1 = self.base_dir / "subdir1"
        subdir1.mkdir()
        (subdir1 / "test3.txt").write_text("test3 content")
        (subdir1 / "test4.xml").write_text("<test>content4</test>")
        
        subdir2 = self.base_dir / "subdir2"
        subdir2.mkdir()
        (subdir2 / "test5.txt").write_text("test5 content")
        (subdir2 / "test6.xml").write_text("<test>content6</test>")
        
        # Create a nested subdirectory
        nested = subdir1 / "nested"
        nested.mkdir()
        (nested / "test7.txt").write_text("test7 content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_get_resource(self):
        """Test getting a single resource."""
        resource = self.resolver.get_resource(f"file:{self.base_dir}/test1.txt")
        self.assertTrue(resource.exists())
        self.assertEqual("test1.txt", resource.get_filename())
        self.assertEqual("test1 content", resource.get_content_as_string())
    
    def test_get_resources_with_exact_path(self):
        """Test getting resources with an exact path."""
        resources = self.resolver.get_resources(f"file:{self.base_dir}/test1.txt")
        self.assertEqual(1, len(resources))
        self.assertEqual("test1.txt", resources[0].get_filename())
        self.assertEqual("test1 content", resources[0].get_content_as_string())
    
    def test_get_resources_with_wildcard(self):
        """Test getting resources with a wildcard pattern."""
        # Test *.txt pattern
        resources = self.resolver.get_resources(f"file:{self.base_dir}/*.txt")
        self.assertEqual(2, len(resources))
        filenames = sorted([r.get_filename() for r in resources])
        self.assertEqual(["test1.txt", "test2.txt"], filenames)
        
        # Test *.xml pattern
        resources = self.resolver.get_resources(f"file:{self.base_dir}/*.xml")
        self.assertEqual(1, len(resources))
        self.assertEqual("test.xml", resources[0].get_filename())
    
    def test_get_resources_with_double_wildcard(self):
        """Test getting resources with a double wildcard pattern."""
        # Test **/*.txt pattern (recursive)
        resources = self.resolver.get_resources(f"file:{self.base_dir}/**/*.txt")
        self.assertEqual(5, len(resources))
        
        # Test **/*.xml pattern (recursive)
        resources = self.resolver.get_resources(f"file:{self.base_dir}/**/*.xml")
        self.assertEqual(3, len(resources))
    
    def test_get_resources_with_specific_directory(self):
        """Test getting resources from a specific directory."""
        resources = self.resolver.get_resources(f"file:{self.base_dir}/subdir1/*.txt")
        self.assertEqual(1, len(resources))
        self.assertEqual("test3.txt", resources[0].get_filename())
    
    def test_get_resources_with_non_existent_pattern(self):
        """Test getting resources with a non-existent pattern."""
        resources = self.resolver.get_resources(f"file:{self.base_dir}/non_existent/*.txt")
        self.assertEqual(0, len(resources))


if __name__ == "__main__":
    unittest.main()