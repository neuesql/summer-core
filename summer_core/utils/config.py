"""
Configuration loading and property resolution for the Summer Core framework.
"""
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Union

from summer_core.utils.resource import Resource, ResourceLoader, PathMatchingResourcePatternResolver


class PropertySource(ABC):
    """
    Interface for a source of properties.
    """
    
    @abstractmethod
    def get_property(self, name: str) -> Optional[Any]:
        """
        Get a property by name.
        
        Args:
            name: The name of the property.
            
        Returns:
            The property value, or None if not found.
        """
        pass
    
    @abstractmethod
    def get_property_names(self) -> Set[str]:
        """
        Get all property names.
        
        Returns:
            A set of all property names.
        """
        pass
    
    @abstractmethod
    def contains_property(self, name: str) -> bool:
        """
        Check if a property exists.
        
        Args:
            name: The name of the property.
            
        Returns:
            True if the property exists, False otherwise.
        """
        pass


class MapPropertySource(PropertySource):
    """
    PropertySource implementation backed by a dictionary.
    """
    
    def __init__(self, name: str, properties: Dict[str, Any]):
        self.name = name
        self.properties = properties
    
    def get_property(self, name: str) -> Optional[Any]:
        return self.properties.get(name)
    
    def get_property_names(self) -> Set[str]:
        return set(self.properties.keys())
    
    def contains_property(self, name: str) -> bool:
        return name in self.properties


class TomlPropertySource(MapPropertySource):
    """
    PropertySource implementation backed by a TOML resource.
    """
    
    def __init__(self, name: str, resource: Resource):
        self.resource = resource
        properties = self._load_toml(resource)
        super().__init__(name, properties)
    
    def _load_toml(self, resource: Resource) -> Dict[str, Any]:
        """
        Load TOML from a resource.
        
        Args:
            resource: The resource to load TOML from.
            
        Returns:
            A dictionary of properties.
        """
        if not resource.exists():
            return {}
        
        # Try to import tomllib (Python 3.11+) first, then fall back to tomli
        toml_parser = None
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
                toml_parser = tomllib
            else:
                import tomli
                toml_parser = tomli
        except ImportError:
            raise ImportError("TOML parsing requires tomli (Python < 3.11) or tomllib (Python >= 3.11)")
        
        content = resource.get_content_as_bytes()
        toml_dict = toml_parser.loads(content.decode('utf-8')) or {}
        
        # Flatten the TOML dictionary
        properties = {}
        self._flatten_dict(toml_dict, "", properties)
        
        return properties
    
    def _flatten_dict(self, d: Dict[str, Any], prefix: str, result: Dict[str, Any]) -> None:
        """
        Flatten a nested dictionary.
        
        Args:
            d: The dictionary to flatten.
            prefix: The prefix for keys.
            result: The result dictionary.
        """
        for key, value in d.items():
            new_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                self._flatten_dict(value, new_key, result)
            else:
                result[new_key] = value


class YamlPropertySource(MapPropertySource):
    """
    PropertySource implementation backed by a YAML resource.
    """
    
    def __init__(self, name: str, resource: Resource):
        self.resource = resource
        properties = self._load_yaml(resource)
        super().__init__(name, properties)
    
    def _load_yaml(self, resource: Resource) -> Dict[str, Any]:
        """
        Load YAML from a resource.
        
        Args:
            resource: The resource to load YAML from.
            
        Returns:
            A dictionary of properties.
        """
        if not resource.exists():
            return {}
        
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML support. Install it with 'pip install pyyaml'.")
        
        content = resource.get_content_as_string()
        yaml_dict = yaml.safe_load(content) or {}
        
        # Flatten the YAML dictionary
        properties = {}
        self._flatten_dict(yaml_dict, "", properties)
        
        return properties
    
    def _flatten_dict(self, d: Dict[str, Any], prefix: str, result: Dict[str, Any]) -> None:
        """
        Flatten a nested dictionary.
        
        Args:
            d: The dictionary to flatten.
            prefix: The prefix for keys.
            result: The result dictionary.
        """
        for key, value in d.items():
            new_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                self._flatten_dict(value, new_key, result)
            else:
                result[new_key] = value


class PropertySourcesPropertyResolver:
    """
    Property resolver that resolves properties from a list of property sources.
    """
    
    def __init__(self):
        self.property_sources: List[PropertySource] = []
        self.placeholder_prefix = "${"
        self.placeholder_suffix = "}"
        self.value_separator = ":"
        self.ignore_unresolvable_placeholders = False
    
    def add_property_source(self, property_source: PropertySource) -> None:
        """
        Add a property source.
        
        Args:
            property_source: The property source to add.
        """
        # Add to the end of the list for proper precedence (first added has highest precedence)
        self.property_sources.append(property_source)
    
    def get_property(self, name: str) -> Optional[Any]:
        """
        Get a property by name.
        
        Args:
            name: The name of the property.
            
        Returns:
            The property value, or None if not found.
        """
        for source in self.property_sources:
            value = source.get_property(name)
            if value is not None:
                return value
        return None
    
    def get_property_names(self) -> Set[str]:
        """
        Get all property names.
        
        Returns:
            A set of all property names.
        """
        names = set()
        for source in self.property_sources:
            names.update(source.get_property_names())
        return names
    
    def contains_property(self, name: str) -> bool:
        """
        Check if a property exists.
        
        Args:
            name: The name of the property.
            
        Returns:
            True if the property exists, False otherwise.
        """
        for source in self.property_sources:
            if source.contains_property(name):
                return True
        return False
    
    def resolve_placeholders(self, text: str) -> str:
        """
        Resolve placeholders in a string.
        
        Args:
            text: The string to resolve placeholders in.
            
        Returns:
            The string with placeholders resolved.
        """
        if not text or self.placeholder_prefix not in text:
            return text
        
        # Use a regex to find all placeholders
        pattern = re.compile(f"{re.escape(self.placeholder_prefix)}(.*?){re.escape(self.placeholder_suffix)}")
        
        def replace_placeholder(match):
            placeholder = match.group(1)
            default_value = None
            
            # Check for default value
            if self.value_separator in placeholder:
                placeholder, default_value = placeholder.split(self.value_separator, 1)
            
            # Resolve the placeholder
            value = self.get_property(placeholder)
            if value is None:
                if default_value is not None:
                    return default_value
                elif self.ignore_unresolvable_placeholders:
                    return match.group(0)
                else:
                    raise ValueError(f"Could not resolve placeholder '{placeholder}' in value '{text}'")
            
            return str(value)
        
        # Replace all placeholders
        result = pattern.sub(replace_placeholder, text)
        
        # Recursively resolve nested placeholders (up to a reasonable depth)
        if self.placeholder_prefix in result and result != text:
            return self.resolve_placeholders(result)
        
        return result


class Environment:
    """
    Interface for accessing properties and profiles.
    """
    
    def __init__(self):
        self.property_resolver = PropertySourcesPropertyResolver()
        self.active_profiles: Set[str] = set()
        self.default_profiles: Set[str] = {"default"}
    
    def get_property(self, name: str, default_value: Any = None) -> Any:
        """
        Get a property by name.
        
        Args:
            name: The name of the property.
            default_value: The default value if the property is not found.
            
        Returns:
            The property value, or the default value if not found.
        """
        value = self.property_resolver.get_property(name)
        if value is not None and isinstance(value, str) and "${" in value:
            value = self.resolve_placeholders(value)
        return value if value is not None else default_value
    
    def get_required_property(self, name: str) -> Any:
        """
        Get a required property by name.
        
        Args:
            name: The name of the property.
            
        Returns:
            The property value.
            
        Raises:
            ValueError: If the property is not found.
        """
        value = self.get_property(name)
        if value is None:
            raise ValueError(f"Required property '{name}' not found")
        return value
    
    def contains_property(self, name: str) -> bool:
        """
        Check if a property exists.
        
        Args:
            name: The name of the property.
            
        Returns:
            True if the property exists, False otherwise.
        """
        return self.property_resolver.contains_property(name)
    
    def get_property_names(self) -> Set[str]:
        """
        Get all property names.
        
        Returns:
            A set of all property names.
        """
        return self.property_resolver.get_property_names()
    
    def resolve_placeholders(self, text: str) -> str:
        """
        Resolve placeholders in a string.
        
        Args:
            text: The string to resolve placeholders in.
            
        Returns:
            The string with placeholders resolved.
        """
        return self.property_resolver.resolve_placeholders(text)
    
    def add_property_source(self, property_source: PropertySource) -> None:
        """
        Add a property source.
        
        Args:
            property_source: The property source to add.
        """
        self.property_resolver.add_property_source(property_source)
    
    def get_active_profiles(self) -> Set[str]:
        """
        Get the active profiles.
        
        Returns:
            A set of active profiles.
        """
        return self.active_profiles.copy()
    
    def set_active_profiles(self, profiles: List[str]) -> None:
        """
        Set the active profiles.
        
        Args:
            profiles: The profiles to set as active.
        """
        self.active_profiles = set(profiles)
    
    def add_active_profile(self, profile: str) -> None:
        """
        Add an active profile.
        
        Args:
            profile: The profile to add.
        """
        self.active_profiles.add(profile)
    
    def get_default_profiles(self) -> Set[str]:
        """
        Get the default profiles.
        
        Returns:
            A set of default profiles.
        """
        return self.default_profiles.copy()
    
    def set_default_profiles(self, profiles: List[str]) -> None:
        """
        Set the default profiles.
        
        Args:
            profiles: The profiles to set as default.
        """
        self.default_profiles = set(profiles)
    
    def accept_profile(self, profile: str) -> bool:
        """
        Check if a profile is active.
        
        Args:
            profile: The profile to check.
            
        Returns:
            True if the profile is active, False otherwise.
        """
        if not profile:
            return True
        
        if profile.startswith("!"):
            return not self.accept_profile(profile[1:])
        
        return profile in self.active_profiles or (not self.active_profiles and profile in self.default_profiles)


class ConfigurationLoader:
    """
    Utility for loading configuration from various sources.
    """
    
    def __init__(self, resource_loader: ResourceLoader = None):
        self.resource_loader = resource_loader or PathMatchingResourcePatternResolver()
        self.environment = Environment()
        
        # Add system properties
        system_env = {k: v for k, v in os.environ.items()}
        self.environment.add_property_source(MapPropertySource("systemProperties", system_env))
    
    def load_yaml(self, location: str) -> None:
        """
        Load YAML from a resource.
        
        Args:
            location: The location of the resource.
        """
        resources = self.resource_loader.get_resources(location)
        for resource in resources:
            name = f"yaml_{resource.get_filename()}"
            self.environment.add_property_source(YamlPropertySource(name, resource))
    
    def load_toml(self, location: str) -> None:
        """
        Load TOML from a resource.
        
        Args:
            location: The location of the resource.
        """
        resources = self.resource_loader.get_resources(location)
        for resource in resources:
            name = f"toml_{resource.get_filename()}"
            self.environment.add_property_source(TomlPropertySource(name, resource))
    
    def get_environment(self) -> Environment:
        """
        Get the environment.
        
        Returns:
            The environment.
        """
        return self.environment