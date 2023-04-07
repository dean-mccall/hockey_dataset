import pytest
from hockey_dataset import wikipedia


def test_extract_teams():
    teams = wikipedia.extract_teams()
    assert len(teams) == 32
