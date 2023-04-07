import pytest
import tempfile
from hockey_dataset import wikipedia
from pathlib import Path



def test_extract_teams():
    teams = wikipedia.extract_teams()
    assert len(teams) == 32


def test_save_to_folder():
    with tempfile.TemporaryDirectory() as output_folder:
        wikipedia.save_to_folder(output_folder, wikipedia.JSON_FORMAT)

        #  check the number of teams created
        team_path = Path(output_folder).joinpath(wikipedia.JSON_PATH_NAME).joinpath(wikipedia.TEAM_PATH_NAME)
        team_files = list(team_path.iterdir())
        assert len(team_files) == 32, 'should be exactly 32 team files'

        #  check the number of players created
        player_path = Path(output_folder).joinpath(wikipedia.JSON_PATH_NAME).joinpath(wikipedia.PLAYER_PATH_NAME)
        player_files = list(player_path.iterdir())
        assert len(player_files) >= 800, 'should be at least more than 800 players'







