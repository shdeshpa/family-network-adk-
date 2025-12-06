"""Pytest fixtures for graph tests."""

import pytest
from src.graph.graphlite.config import GraphLiteConfig
from src.graph.graphlite.client import GraphLiteClient
from src.graph.family.graph import FamilyGraph


@pytest.fixture
def config():
    """Test configuration."""
    return GraphLiteConfig()


@pytest.fixture
def client(config):
    """GraphLite client."""
    return GraphLiteClient(config)


@pytest.fixture
def graph(config):
    """FamilyGraph instance."""
    return FamilyGraph(config)
