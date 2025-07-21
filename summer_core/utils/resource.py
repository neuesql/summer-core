"""
Resource abstraction layer for accessing resources from various sources.
"""
import fnmatch
import glob
import os
import pathlib
import re
from abc import ABC, abstractmethod
from typing import BinaryIO, Dict, Iterator, List, Optional, Pattern, Set, Union
from urllib.parse import urlparse
import urllib.request


class Resource(ABC):
    """
    Interface for accessing resources from various sources.
    Resources can be files, URLs, classpath resources, etc.
    """
    
    @abstractmethod
    def exists(self) -> bool:
        """Check if the resource exists."""
        pass
    
    @abstractmethod
    def get_filename(self) -> str:
        """Get the filename of the resource."""
        pass
    
    @abstractmethod
    def get_path(self) -> str:
        """Get the path of the resource."""
        pass
    
    @abstractmethod
    def get_url(self) -> str:
        """Get the URL of the resource."""
        pass
    
    @abstractmethod
    def get_input_stream(self) -> BinaryIO:
        """Get an input stream for reading the resource."""
        pass
    
    @abstractmethod
    def get_content_as_bytes(self) -> bytes:
        """Get the content of the resource as bytes."""
        pass
    
    def get_content_as_string(self, encoding: str = "utf-8") -> str:
        """Get the content of the resource as a string."""
        return self.get_content_as_bytes().decode(encoding)
    
    @abstractmethod
    def get_content_length(self) -> int:
        """Get the content length of the resource."""
        pass
    
    @abstractmethod
    def get_last_modified(self) -> int:
        """Get the last modified timestamp of the resource."""
        pass


class FileSystemResource(Resource):
    """Resource implementation for accessing files on the filesystem."""
    
    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self.file_path = pathlib.Path(self.path)
    
    def exists(self) -> bool:
        return self.file_path.exists()
    
    def get_filename(self) -> str:
        return self.file_path.name
    
    def get_path(self) -> str:
        return self.path
    
    def get_url(self) -> str:
        return f"file:{self.path}"
    
    def get_input_stream(self) -> BinaryIO:
        return open(self.path, "rb")
    
    def get_content_as_bytes(self) -> bytes:
        with open(self.path, "rb") as f:
            return f.read()
    
    def get_content_length(self) -> int:
        if self.exists():
            return self.file_path.stat().st_size
        return 0
    
    def get_last_modified(self) -> int:
        if self.exists():
            return int(self.file_path.stat().st_mtime)
        return 0
    
    def __str__(self) -> str:
        return f"FileSystemResource: {self.path}"


class ClassPathResource(Resource):
    """Resource implementation for accessing resources from the classpath."""
    
    def __init__(self, path: str, class_loader=None):
        if path.startswith("/"):
            path = path[1:]
        self.path = path
        self.class_loader = class_loader
    
    def exists(self) -> bool:
        try:
            # Try to get the resource as a file
            self._get_resource_path()
            return True
        except (FileNotFoundError, ImportError):
            return False
    
    def get_filename(self) -> str:
        return os.path.basename(self.path)
    
    def get_path(self) -> str:
        return self.path
    
    def get_url(self) -> str:
        return f"classpath:{self.path}"
    
    def _get_resource_path(self) -> str:
        """Get the actual file path of the resource."""
        # Split the path into package and resource name
        parts = self.path.split("/")
        if len(parts) <= 1:
            raise FileNotFoundError(f"Invalid classpath resource: {self.path}")
        
        package = ".".join(parts[:-1])
        resource_name = parts[-1]
        
        try:
            # Try to find the module
            module = __import__(package, fromlist=["__file__"])
            module_path = os.path.dirname(module.__file__)
            resource_path = os.path.join(module_path, resource_name)
            
            if not os.path.exists(resource_path):
                raise FileNotFoundError(f"Resource not found: {self.path}")
            
            return resource_path
        except (ImportError, AttributeError) as e:
            raise FileNotFoundError(f"Resource not found: {self.path}") from e
    
    def get_input_stream(self) -> BinaryIO:
        resource_path = self._get_resource_path()
        return open(resource_path, "rb")
    
    def get_content_as_bytes(self) -> bytes:
        with self.get_input_stream() as stream:
            return stream.read()
    
    def get_content_length(self) -> int:
        try:
            resource_path = self._get_resource_path()
            return os.path.getsize(resource_path)
        except FileNotFoundError:
            return 0
    
    def get_last_modified(self) -> int:
        try:
            resource_path = self._get_resource_path()
            return int(os.path.getmtime(resource_path))
        except FileNotFoundError:
            return 0
    
    def __str__(self) -> str:
        return f"ClassPathResource: {self.path}"


class UrlResource(Resource):
    """Resource implementation for accessing resources from URLs."""
    
    def __init__(self, url: str):
        self.url = url
        self.url_obj = urlparse(url)
    
    def exists(self) -> bool:
        try:
            with urllib.request.urlopen(self.url) as response:
                return response.status == 200
        except Exception:
            return False
    
    def get_filename(self) -> str:
        path = self.url_obj.path
        return os.path.basename(path) if path else ""
    
    def get_path(self) -> str:
        return self.url_obj.path if self.url_obj.path else "/"
    
    def get_url(self) -> str:
        return self.url
    
    def get_input_stream(self) -> BinaryIO:
        return urllib.request.urlopen(self.url)
    
    def get_content_as_bytes(self) -> bytes:
        with self.get_input_stream() as stream:
            return stream.read()
    
    def get_content_length(self) -> int:
        try:
            with urllib.request.urlopen(self.url) as response:
                return int(response.headers.get("Content-Length", 0))
        except Exception:
            return 0
    
    def get_last_modified(self) -> int:
        try:
            with urllib.request.urlopen(self.url) as response:
                last_modified = response.headers.get("Last-Modified")
                if last_modified:
                    import email.utils
                    import time
                    time_tuple = email.utils.parsedate_tz(last_modified)
                    if time_tuple:
                        return int(time.mktime(time_tuple[:9]))
            return 0
        except Exception:
            return 0
    
    def __str__(self) -> str:
        return f"UrlResource: {self.url}"


class ResourceLoader(ABC):
    """
    Interface for loading resources from various sources.
    """
    
    @abstractmethod
    def get_resource(self, location: str) -> Resource:
        """
        Get a resource by location.
        
        Args:
            location: The location of the resource.
            
        Returns:
            The resource.
        """
        pass
    
    @abstractmethod
    def get_resources(self, location_pattern: str) -> List[Resource]:
        """
        Get resources matching a location pattern.
        
        Args:
            location_pattern: The location pattern to match.
            
        Returns:
            A list of matching resources.
        """
        pass
    
    def get_resource_as_string(self, location: str, encoding: str = "utf-8") -> str:
        """
        Get a resource as a string.
        
        Args:
            location: The location of the resource.
            encoding: The encoding to use.
            
        Returns:
            The resource content as a string.
        """
        return self.get_resource(location).get_content_as_string(encoding)


class DefaultResourceLoader(ResourceLoader):
    """
    Default implementation of ResourceLoader.
    """
    
    def __init__(self, class_loader=None):
        self.class_loader = class_loader
    
    def get_resource(self, location: str) -> Resource:
        """
        Get a resource by location.
        
        Args:
            location: The location of the resource.
            
        Returns:
            The resource.
        """
        if location.startswith("classpath:"):
            return ClassPathResource(location[10:], self.class_loader)
        elif location.startswith("file:"):
            return FileSystemResource(location[5:])
        elif location.startswith("http:") or location.startswith("https:"):
            return UrlResource(location)
        else:
            # Default to classpath resource
            return ClassPathResource(location, self.class_loader)
    
    def get_resources(self, location_pattern: str) -> List[Resource]:
        """
        Get resources matching a location pattern.
        
        Args:
            location_pattern: The location pattern to match.
            
        Returns:
            A list of matching resources.
        """
        # Delegate to pattern resolver
        return PathMatchingResourcePatternResolver(self).get_resources(location_pattern)


class ResourcePatternResolver(ResourceLoader):
    """
    Interface for resolving resource patterns into Resource objects.
    """
    
    # Classpath all URL prefix
    CLASSPATH_ALL_URL_PREFIX = "classpath*:"
    
    def get_resources(self, location_pattern: str) -> List[Resource]:
        """
        Resolve the given location pattern into Resource objects.
        
        Args:
            location_pattern: The location pattern to resolve.
            
        Returns:
            A list of matching resources.
        """
        pass


class PathMatchingResourcePatternResolver(ResourcePatternResolver):
    """
    A ResourcePatternResolver implementation that supports Ant-style path patterns.
    """
    
    def __init__(self, resource_loader: ResourceLoader = None):
        self.resource_loader = resource_loader or DefaultResourceLoader()
    
    def get_resource(self, location: str) -> Resource:
        """
        Get a resource by location.
        
        Args:
            location: The location of the resource.
            
        Returns:
            The resource.
        """
        return self.resource_loader.get_resource(location)
    
    def get_resources(self, location_pattern: str) -> List[Resource]:
        """
        Get resources matching a location pattern.
        
        Args:
            location_pattern: The location pattern to match.
            
        Returns:
            A list of matching resources.
        """
        if location_pattern.startswith(self.CLASSPATH_ALL_URL_PREFIX):
            # Classpath* pattern
            pattern = location_pattern[len(self.CLASSPATH_ALL_URL_PREFIX):]
            return self._find_all_classpath_resources(pattern)
        elif self._is_pattern(location_pattern):
            # Pattern with wildcards
            return self._find_path_matching_resources(location_pattern)
        else:
            # Single resource
            return [self.get_resource(location_pattern)]
    
    def _is_pattern(self, path: str) -> bool:
        """
        Check if the given path contains a pattern.
        
        Args:
            path: The path to check.
            
        Returns:
            True if the path contains a pattern, False otherwise.
        """
        return "*" in path or "?" in path or "[" in path
    
    def _find_all_classpath_resources(self, location: str) -> List[Resource]:
        """
        Find all classpath resources matching the given location.
        
        Args:
            location: The location to match.
            
        Returns:
            A list of matching resources.
        """
        import importlib.metadata
        import sys
        
        resources = []
        
        # Check if the location contains a pattern
        if self._is_pattern(location):
            # Get all packages
            packages = set()
            for dist in importlib.metadata.distributions():
                packages.update(dist.read_text("top_level.txt").splitlines())
            
            # Remove empty strings
            packages = {pkg for pkg in packages if pkg}
            
            # Convert location to a regex pattern
            pattern = fnmatch.translate(location)
            regex = re.compile(pattern)
            
            # Check each package for matching resources
            for package in packages:
                try:
                    module = __import__(package)
                    package_path = os.path.dirname(module.__file__)
                    
                    for root, _, files in os.walk(package_path):
                        rel_path = os.path.relpath(root, package_path)
                        if rel_path == ".":
                            rel_path = ""
                        
                        for file in files:
                            resource_path = os.path.join(rel_path, file).replace("\\", "/")
                            if regex.match(resource_path):
                                # Convert to package path
                                parts = resource_path.split("/")
                                if len(parts) > 1:
                                    pkg_path = f"{package}.{'.'.join(parts[:-1])}"
                                    resources.append(ClassPathResource(f"{pkg_path}/{parts[-1]}"))
                                else:
                                    resources.append(ClassPathResource(f"{package}/{resource_path}"))
                except (ImportError, AttributeError):
                    # Skip packages that can't be imported
                    continue
        else:
            # Simple classpath resource
            resources.append(ClassPathResource(location))
        
        return resources
    
    def _find_path_matching_resources(self, location_pattern: str) -> List[Resource]:
        """
        Find all resources matching the given pattern.
        
        Args:
            location_pattern: The pattern to match.
            
        Returns:
            A list of matching resources.
        """
        resources = []
        
        # Check if it's a URL pattern
        if location_pattern.startswith("file:"):
            # File pattern
            file_pattern = location_pattern[5:]
            root_dir = self._determine_root_dir(file_pattern)
            root_dir_resource = FileSystemResource(root_dir)
            
            if not root_dir_resource.exists():
                return []
            
            pattern = file_pattern[len(root_dir):]
            if pattern.startswith("/"):
                pattern = pattern[1:]
            
            resources = self._find_matching_files(root_dir, pattern)
        elif location_pattern.startswith("classpath:"):
            # Classpath pattern
            classpath_pattern = location_pattern[10:]
            root_dir = self._determine_root_dir(classpath_pattern)
            pattern = classpath_pattern[len(root_dir):]
            if pattern.startswith("/"):
                pattern = pattern[1:]
            
            # Convert root_dir to package format
            package = root_dir.replace("/", ".")
            if package.endswith("."):
                package = package[:-1]
            
            try:
                module = __import__(package)
                package_path = os.path.dirname(module.__file__)
                
                resources = self._find_matching_files_in_dir(package_path, pattern, f"classpath:{root_dir}")
            except ImportError:
                # Package not found
                pass
        else:
            # Default to file system
            root_dir = self._determine_root_dir(location_pattern)
            pattern = location_pattern[len(root_dir):]
            if pattern.startswith("/"):
                pattern = pattern[1:]
            
            resources = self._find_matching_files(root_dir, pattern)
        
        return resources
    
    def _determine_root_dir(self, location: str) -> str:
        """
        Determine the root directory for the given location.
        
        Args:
            location: The location to check.
            
        Returns:
            The root directory.
        """
        prefix_end = location.find(":") + 1
        root_dir_end = location.find("*", prefix_end)
        if root_dir_end == -1:
            root_dir_end = location.find("?", prefix_end)
        if root_dir_end == -1:
            root_dir_end = location.find("[", prefix_end)
        
        if root_dir_end != -1:
            root_dir = location[:root_dir_end]
            if root_dir.endswith("/"):
                return root_dir
            index = root_dir.rfind("/")
            return root_dir[:index + 1] if index != -1 else ""
        else:
            return location
    
    def _find_matching_files(self, root_dir: str, pattern: str) -> List[Resource]:
        """
        Find all files matching the given pattern in the root directory.
        
        Args:
            root_dir: The root directory to search in.
            pattern: The pattern to match.
            
        Returns:
            A list of matching resources.
        """
        full_pattern = os.path.join(root_dir, pattern).replace("\\", "/")
        files = glob.glob(full_pattern, recursive=True)
        return [FileSystemResource(file) for file in files]
    
    def _find_matching_files_in_dir(self, dir_path: str, pattern: str, prefix: str) -> List[Resource]:
        """
        Find all files matching the given pattern in the directory.
        
        Args:
            dir_path: The directory to search in.
            pattern: The pattern to match.
            prefix: The prefix to add to the resource path.
            
        Returns:
            A list of matching resources.
        """
        resources = []
        
        # Convert pattern to regex
        regex_pattern = fnmatch.translate(pattern)
        regex = re.compile(regex_pattern)
        
        for root, _, files in os.walk(dir_path):
            rel_path = os.path.relpath(root, dir_path).replace("\\", "/")
            if rel_path == ".":
                rel_path = ""
            
            for file in files:
                resource_path = f"{rel_path}/{file}" if rel_path else file
                resource_path = resource_path.replace("\\", "/")
                
                if regex.match(resource_path):
                    if prefix.startswith("classpath:"):
                        # Convert to classpath resource
                        classpath = prefix[10:]
                        full_path = f"{classpath}/{resource_path}" if classpath else resource_path
                        resources.append(ClassPathResource(full_path))
                    else:
                        # File resource
                        full_path = os.path.join(dir_path, resource_path)
                        resources.append(FileSystemResource(full_path))
        
        return resources