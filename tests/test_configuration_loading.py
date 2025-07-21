import os
import tempfile
import unittest
from pathlib import Path

from summer_core.utils.config import (
    ConfigurationLoader,
    Environment,
    MapPropertySource,
    PropertySourcesPropertyResolver,
    TomlPropertySource,
    YamlPropertySource,
)
from summer_core.utils.resource import FileSystemResource


class TestPropertySources(unittest.TestCase):
    """Test cases for property sources."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        
        # Create test YAML file
        self.yaml_file = self.base_dir / "test.yml"
        self.yaml_file.write_text(
            "app:\n"
            "  name: Test Application\n"
            "  version: 1.0.0\n"
            "  description: A test application\n"
            "  debug: true\n"
            "  port: 8080\n"
            "database:\n"
            "  url: jdbc:postgresql://localhost:5432/testdb\n"
            "  username: test\n"
            "  password: password\n"
            "  pool:\n"
            "    min-size: 5\n"
            "    max-size: 20\n"
        )
        
        # Create test TOML file
        self.toml_file = self.base_dir / "test.toml"
        self.toml_file.write_text(
            '[app]\n'
            'name = "TOML Application"\n'
            'version = "1.0.0"\n'
            'description = "A TOML application"\n'
            'debug = true\n'
            'port = 8080\n'
            '\n'
            '[database]\n'
            'url = "jdbc:postgresql://localhost:5432/testdb"\n'
            'username = "test"\n'
            'password = "password"\n'
            '\n'
            '[database.pool]\n'
            'min-size = 5\n'
            'max-size = 20\n'
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_map_property_source(self):
        """Test MapPropertySource."""
        properties = {
            "app.name": "Test Application",
            "app.version": "1.0.0",
            "app.debug": "true",
        }
        source = MapPropertySource("test", properties)
        
        self.assertEqual("Test Application", source.get_property("app.name"))
        self.assertEqual("1.0.0", source.get_property("app.version"))
        self.assertEqual("true", source.get_property("app.debug"))
        self.assertIsNone(source.get_property("app.unknown"))
        
        self.assertTrue(source.contains_property("app.name"))
        self.assertFalse(source.contains_property("app.unknown"))
        
        self.assertEqual({"app.name", "app.version", "app.debug"}, source.get_property_names())
    
    def test_toml_property_source(self):
        """Test TomlPropertySource."""
        # Check if we have either tomli or tomllib available
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli
        except ImportError:
            self.skipTest("Neither tomli nor tomllib is available")
        
        resource = FileSystemResource(str(self.toml_file))
        source = TomlPropertySource("test", resource)
        
        self.assertEqual("TOML Application", source.get_property("app.name"))
        self.assertEqual("1.0.0", source.get_property("app.version"))
        self.assertEqual("A TOML application", source.get_property("app.description"))
        self.assertEqual(True, source.get_property("app.debug"))
        self.assertEqual(8080, source.get_property("app.port"))
        self.assertEqual("jdbc:postgresql://localhost:5432/testdb", source.get_property("database.url"))
        self.assertEqual("test", source.get_property("database.username"))
        self.assertEqual("password", source.get_property("database.password"))
        self.assertEqual(5, source.get_property("database.pool.min-size"))
        self.assertEqual(20, source.get_property("database.pool.max-size"))
        self.assertIsNone(source.get_property("app.unknown"))
        
        self.assertTrue(source.contains_property("app.name"))
        self.assertFalse(source.contains_property("app.unknown"))
        
        expected_names = {
            "app.name", "app.version", "app.description", "app.debug", "app.port",
            "database.url", "database.username", "database.password",
            "database.pool.min-size", "database.pool.max-size",
        }
        self.assertEqual(expected_names, source.get_property_names())
    
    def test_yaml_property_source(self):
        """Test YamlPropertySource."""
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML is not installed")
        
        resource = FileSystemResource(str(self.yaml_file))
        source = YamlPropertySource("test", resource)
        
        self.assertEqual("Test Application", source.get_property("app.name"))
        self.assertEqual("1.0.0", source.get_property("app.version"))
        self.assertEqual("A test application", source.get_property("app.description"))
        self.assertEqual(True, source.get_property("app.debug"))
        self.assertEqual(8080, source.get_property("app.port"))
        self.assertEqual("jdbc:postgresql://localhost:5432/testdb", source.get_property("database.url"))
        self.assertEqual("test", source.get_property("database.username"))
        self.assertEqual("password", source.get_property("database.password"))
        self.assertEqual(5, source.get_property("database.pool.min-size"))
        self.assertEqual(20, source.get_property("database.pool.max-size"))
        self.assertIsNone(source.get_property("app.unknown"))
        
        self.assertTrue(source.contains_property("app.name"))
        self.assertFalse(source.contains_property("app.unknown"))
        
        expected_names = {
            "app.name", "app.version", "app.description", "app.debug", "app.port",
            "database.url", "database.username", "database.password",
            "database.pool.min-size", "database.pool.max-size",
        }
        self.assertEqual(expected_names, source.get_property_names())


class TestPropertyResolver(unittest.TestCase):
    """Test cases for property resolver."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.resolver = PropertySourcesPropertyResolver()
        
        # Add property sources (first added has highest precedence)
        self.resolver.add_property_source(MapPropertySource("first", {
            "app.name": "First Application",
            "app.version": "1.0.0",
            "app.unique1": "first",
        }))
        self.resolver.add_property_source(MapPropertySource("second", {
            "app.name": "Second Application",
            "app.debug": "true",
            "app.unique2": "second",
        }))
    
    def test_property_resolution_order(self):
        """Test property resolution order."""
        # First source has precedence
        self.assertEqual("First Application", self.resolver.get_property("app.name"))
        self.assertEqual("1.0.0", self.resolver.get_property("app.version"))
        self.assertEqual("true", self.resolver.get_property("app.debug"))
        self.assertEqual("first", self.resolver.get_property("app.unique1"))
        self.assertEqual("second", self.resolver.get_property("app.unique2"))
        self.assertIsNone(self.resolver.get_property("app.unknown"))
    
    def test_placeholder_resolution(self):
        """Test placeholder resolution."""
        # Add a source with placeholders
        self.resolver.add_property_source(MapPropertySource("placeholders", {
            "app.full-name": "${app.name} ${app.version}",
            "app.nested": "Nested ${app.full-name}",
            "app.with-default": "${app.unknown:default value}",
            "app.debug-str": "Debug is ${app.debug}",
        }))
        
        self.assertEqual("First Application 1.0.0", self.resolver.resolve_placeholders("${app.full-name}"))
        self.assertEqual("Nested First Application 1.0.0", self.resolver.resolve_placeholders("${app.nested}"))
        self.assertEqual("default value", self.resolver.resolve_placeholders("${app.unknown:default value}"))
        self.assertEqual("Debug is true", self.resolver.resolve_placeholders("${app.debug-str}"))
        
        # Test with unresolvable placeholder
        with self.assertRaises(ValueError):
            self.resolver.resolve_placeholders("${app.unknown}")
        
        # Test with ignore unresolvable placeholders
        self.resolver.ignore_unresolvable_placeholders = True
        self.assertEqual("${app.unknown}", self.resolver.resolve_placeholders("${app.unknown}"))


class TestEnvironment(unittest.TestCase):
    """Test cases for environment."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.env = Environment()
        
        # Add property sources
        self.env.add_property_source(MapPropertySource("test", {
            "app.name": "Test Application",
            "app.version": "1.0.0",
            "app.debug": "true",
        }))
    
    def test_property_access(self):
        """Test property access."""
        self.assertEqual("Test Application", self.env.get_property("app.name"))
        self.assertEqual("1.0.0", self.env.get_property("app.version"))
        self.assertEqual("true", self.env.get_property("app.debug"))
        self.assertIsNone(self.env.get_property("app.unknown"))
        
        # Test with default value
        self.assertEqual("default", self.env.get_property("app.unknown", "default"))
        
        # Test required property
        self.assertEqual("Test Application", self.env.get_required_property("app.name"))
        with self.assertRaises(ValueError):
            self.env.get_required_property("app.unknown")
        
        # Test contains property
        self.assertTrue(self.env.contains_property("app.name"))
        self.assertFalse(self.env.contains_property("app.unknown"))
        
        # Test property names
        self.assertEqual({"app.name", "app.version", "app.debug"}, self.env.get_property_names())
    
    def test_placeholder_resolution(self):
        """Test placeholder resolution."""
        # Add a source with placeholders
        self.env.add_property_source(MapPropertySource("placeholders", {
            "app.full-name": "${app.name} ${app.version}",
            "app.with-default": "${app.unknown:default value}",
        }))
        
        self.assertEqual("Test Application 1.0.0", self.env.resolve_placeholders("${app.full-name}"))
        self.assertEqual("default value", self.env.resolve_placeholders("${app.with-default}"))
    
    def test_profiles(self):
        """Test profiles."""
        # Default profile
        self.assertEqual({"default"}, self.env.get_default_profiles())
        self.assertTrue(self.env.accept_profile("default"))
        self.assertFalse(self.env.accept_profile("dev"))
        
        # Set active profiles
        self.env.set_active_profiles(["dev", "test"])
        self.assertEqual({"dev", "test"}, self.env.get_active_profiles())
        self.assertTrue(self.env.accept_profile("dev"))
        self.assertTrue(self.env.accept_profile("test"))
        self.assertFalse(self.env.accept_profile("prod"))
        self.assertFalse(self.env.accept_profile("default"))  # Default profiles are ignored when active profiles are set
        
        # Add active profile
        self.env.add_active_profile("prod")
        self.assertEqual({"dev", "test", "prod"}, self.env.get_active_profiles())
        self.assertTrue(self.env.accept_profile("prod"))
        
        # Negated profile
        self.assertFalse(self.env.accept_profile("!dev"))
        self.assertTrue(self.env.accept_profile("!staging"))
        
        # Empty profile
        self.assertTrue(self.env.accept_profile(""))


class TestConfigurationLoader(unittest.TestCase):
    """Test cases for configuration loader."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        
        # Create test YAML file
        self.yaml_file = self.base_dir / "application.yml"
        self.yaml_file.write_text(
            "app:\n"
            "  name: YAML Application\n"
            "  version: 2.0.0\n"
            "  description: A YAML application\n"
            "  debug: false\n"
            "  port: 9090\n"
            "database:\n"
            "  url: jdbc:postgresql://localhost:5432/testdb\n"
            "  username: test\n"
            "  password: password\n"
        )
        
        # Create profile-specific YAML file
        self.prod_yaml_file = self.base_dir / "application-prod.yml"
        self.prod_yaml_file.write_text(
            "app:\n"
            "  name: Production Application\n"
            "  debug: false\n"
            "  profile: prod\n"
            "database:\n"
            "  url: jdbc:postgresql://prod-db:5432/proddb\n"
        )
        
        # Create test TOML file
        self.toml_file = self.base_dir / "application.toml"
        self.toml_file.write_text(
            '[app]\n'
            'name = "TOML Application"\n'
            'version = "3.0.0"\n'
            'description = "A TOML application"\n'
            'debug = true\n'
            'port = 7070\n'
            '\n'
            '[database]\n'
            'url = "jdbc:postgresql://localhost:5432/tomldb"\n'
            'username = "toml_user"\n'
            'password = "toml_password"\n'
        )
        
        # Create profile-specific TOML file
        self.dev_toml_file = self.base_dir / "application-dev.toml"
        self.dev_toml_file.write_text(
            '[app]\n'
            'name = "Dev TOML Application"\n'
            'debug = true\n'
            'profile = "dev"\n'
        )
        
        # Create configuration loader
        self.loader = ConfigurationLoader()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_load_toml(self):
        """Test loading TOML."""
        # Check if we have either tomli or tomllib available
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli
        except ImportError:
            self.skipTest("Neither tomli nor tomllib is available")
        
        self.loader.load_toml(f"file:{self.toml_file}")
        env = self.loader.get_environment()
        
        self.assertEqual("TOML Application", env.get_property("app.name"))
        self.assertEqual("3.0.0", env.get_property("app.version"))
        self.assertEqual("A TOML application", env.get_property("app.description"))
        self.assertEqual(True, env.get_property("app.debug"))
        self.assertEqual(7070, env.get_property("app.port"))
        self.assertEqual("jdbc:postgresql://localhost:5432/tomldb", env.get_property("database.url"))
        self.assertEqual("toml_user", env.get_property("database.username"))
        self.assertEqual("toml_password", env.get_property("database.password"))
    
    def test_load_yaml(self):
        """Test loading YAML."""
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML is not installed")
        
        self.loader.load_yaml(f"file:{self.yaml_file}")
        env = self.loader.get_environment()
        
        self.assertEqual("YAML Application", env.get_property("app.name"))
        self.assertEqual("2.0.0", env.get_property("app.version"))
        self.assertEqual("A YAML application", env.get_property("app.description"))
        self.assertEqual(False, env.get_property("app.debug"))
        self.assertEqual(9090, env.get_property("app.port"))
        self.assertEqual("jdbc:postgresql://localhost:5432/testdb", env.get_property("database.url"))
        self.assertEqual("test", env.get_property("database.username"))
        self.assertEqual("password", env.get_property("database.password"))
    
    def test_load_multiple_sources(self):
        """Test loading multiple sources."""
        # Check for YAML
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML is not installed")
            
        # Check for TOML (either tomli or tomllib)
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli
        except ImportError:
            self.skipTest("Neither tomli nor tomllib is available")
        
        # Create a new loader for this test
        loader = ConfigurationLoader()
        
        # Load TOML first, then YAML (TOML should have precedence)
        loader.load_toml(f"file:{self.toml_file}")
        loader.load_yaml(f"file:{self.yaml_file}")
        env = loader.get_environment()
        
        # TOML values should take precedence
        self.assertEqual("TOML Application", env.get_property("app.name"))
        self.assertEqual("3.0.0", env.get_property("app.version"))
        self.assertEqual("A TOML application", env.get_property("app.description"))
        self.assertEqual(True, env.get_property("app.debug"))
        self.assertEqual(7070, env.get_property("app.port"))
        
        # Database properties from TOML
        self.assertEqual("jdbc:postgresql://localhost:5432/tomldb", env.get_property("database.url"))
        self.assertEqual("toml_user", env.get_property("database.username"))
        self.assertEqual("toml_password", env.get_property("database.password"))
    
    def test_profile_specific_configuration(self):
        """Test profile-specific configuration."""
        # Check for YAML
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML is not installed")
            
        # Check for TOML (either tomli or tomllib)
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli
        except ImportError:
            self.skipTest("Neither tomli nor tomllib is available")
        
        # Create a new loader for this test
        loader = ConfigurationLoader()
        
        # Load dev profile TOML first (should have highest precedence)
        loader.load_toml(f"file:{self.dev_toml_file}")
        
        # Then load base TOML and YAML
        loader.load_toml(f"file:{self.toml_file}")
        loader.load_yaml(f"file:{self.yaml_file}")
        
        env = loader.get_environment()
        env.set_active_profiles(["dev"])
        
        # Dev profile TOML should override base TOML
        self.assertEqual("Dev TOML Application", env.get_property("app.name"))
        self.assertEqual("3.0.0", env.get_property("app.version"))  # From base TOML
        self.assertEqual("A TOML application", env.get_property("app.description"))  # From base TOML
        self.assertEqual(True, env.get_property("app.debug"))  # From dev TOML
        self.assertEqual(7070, env.get_property("app.port"))  # From base TOML
        self.assertEqual("dev", env.get_property("app.profile"))  # Only in dev TOML
        
        # Create a new loader for testing prod profile
        prod_loader = ConfigurationLoader()
        
        # Load prod profile YAML first (should have highest precedence)
        prod_loader.load_yaml(f"file:{self.prod_yaml_file}")
        
        # Then load base YAML
        prod_loader.load_yaml(f"file:{self.yaml_file}")
        
        prod_env = prod_loader.get_environment()
        prod_env.set_active_profiles(["prod"])
        
        # Prod profile YAML should override base YAML
        self.assertEqual("Production Application", prod_env.get_property("app.name"))
        self.assertEqual("2.0.0", prod_env.get_property("app.version"))  # From base YAML
        self.assertEqual("A YAML application", prod_env.get_property("app.description"))  # From base YAML
        self.assertEqual(False, prod_env.get_property("app.debug"))  # From prod YAML
        self.assertEqual(9090, prod_env.get_property("app.port"))  # From base YAML
        self.assertEqual("prod", prod_env.get_property("app.profile"))  # Only in prod YAML
        self.assertEqual("jdbc:postgresql://prod-db:5432/proddb", prod_env.get_property("database.url"))  # From prod YAML
    
    def test_placeholder_resolution(self):
        """Test placeholder resolution."""
        # Check for TOML (either tomli or tomllib)
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli
        except ImportError:
            self.skipTest("Neither tomli nor tomllib is available")
        
        # Create a TOML file with placeholders
        placeholder_file = self.base_dir / "placeholder.toml"
        placeholder_file.write_text(
            '[app]\n'
            'name = "Placeholder Application"\n'
            'version = "3.0.0"\n'
            'full-name = "${app.name} ${app.version}"\n'
            'nested = "Nested ${app.full-name}"\n'
            'with-default = "${app.unknown:default value}"\n'
        )
        
        self.loader.load_toml(f"file:{placeholder_file}")
        env = self.loader.get_environment()
        
        self.assertEqual("Placeholder Application", env.get_property("app.name"))
        self.assertEqual("3.0.0", env.get_property("app.version"))
        self.assertEqual("Placeholder Application 3.0.0", env.get_property("app.full-name"))
        self.assertEqual("Nested Placeholder Application 3.0.0", env.get_property("app.nested"))
        self.assertEqual("default value", env.get_property("app.with-default"))
    
    def test_environment_variables(self):
        """Test environment variables."""
        # Set a test environment variable
        os.environ["TEST_ENV_VAR"] = "test value"
        
        # Create a new loader to pick up the environment variable
        loader = ConfigurationLoader()
        env = loader.get_environment()
        self.assertEqual("test value", env.get_property("TEST_ENV_VAR"))


if __name__ == "__main__":
    unittest.main()