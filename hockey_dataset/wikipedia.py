"""extract player statistics from wikipedia"""
from datetime import datetime
import logging
import shutil
import time
import os
import json
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from numpyencoder import NumpyEncoder
import requests
from requests.compat import urljoin



#  configure logging
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s | %(name)s | %(levelname)s | %(message)s')


#  constants
JSON_FORMAT = 0
WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org/'
NHL_LEAGUE_URL = urljoin(WIKIPEDIA_BASE_URL, '/wiki/National_Hockey_League')
JSON_PATH_NAME = 'json'
PLAYER_PATH_NAME = 'player'
TEAM_PATH_NAME = 'team'
REQUEST_READ_TIMEOUT = 10



def clean_career_statistic_number(raw_text):
    """remove non-numeric characters from number in career statistics"""
    if raw_text is None:
        result = None
    else:
        result = raw_text.strip().replace('—', '').replace(',', '')
        if len(result) > 0:
            if result.isnumeric():
                result = pd.to_numeric(result)
            else:
                result = None
        else:
            result = None

    return result


def clean_attribute_name(raw_text):
    """translate infobox label to snake case attribute name"""
    return raw_text.lower().replace(' ', '_')



def clean_attribute_value(raw_text):
    """clean unicode values from scraped text"""
    return raw_text.replace('\n', '').replace('\u2013', '-')


def extract_teams():
    """use the league page to find teams"""
    logging.debug('starting league scrape')

    # result array
    teams = []

    # read the page
    league_page = requests.get(NHL_LEAGUE_URL, timeout = REQUEST_READ_TIMEOUT)
    if league_page.status_code == 200:
        logging.debug('finding teams')

        #  parse the page
        soup = BeautifulSoup(league_page.text, 'lxml')

        #  find span with teams id
        teams_span = soup.find('span', id = 'Teams')

        #  find the table of teams
        teams_table = teams_span.find_next('table')
        team_rows = teams_table.findChildren('tr')
        row_count = 0
        for team_row in team_rows:
            row_count = row_count + 1

            #  skip the header row
            if row_count > 1:
                team_header_cells = team_row.findChildren('th')
                team_cells = team_row.findChildren('td')
                if len(team_header_cells) > 0:
                    #  handle conference identification that spans all columns
                    if team_header_cells[0].get('colspan') == '10':
                        league_conference = team_header_cells[0].text

                    #  division names span rows
                    elif team_header_cells[0].get('rowspan') is not None:
                        rowspan = pd.to_numeric(team_header_cells[0].get('rowspan'))
                        if rowspan > 1:
                            conference_division = team_header_cells[0].text

                #  information about the teams
                if len(team_cells) > 0:
                    team_anchor = team_cells[0].findChildren('a')
                    team_url = team_anchor[0].get('href')
                    team_name = team_anchor[0].text

                    team = {
                        "league_conference": league_conference,
                        "conference_division": conference_division,
                        "team_name": team_name,
                        "team_url": urljoin(WIKIPEDIA_BASE_URL, team_url)
                    }
                    teams.append(team)

        logging.info('collected %s teams', len(teams))
        return teams
    else:
        message = 'http request failed retrieving league page'
        logging.error(message)
        raise Exception(message)



def extract_roster(team):
    """find the players on a team"""
    logging.debug('collecting roster for %s', team['team_url'])

    #  read the page
    team_page = requests.get(team['team_url'], timeout = REQUEST_READ_TIMEOUT)
    if team_page.status_code == 200:
        logging.debug('finding roster')
        soup = BeautifulSoup(team_page.text, 'lxml')

        #  find span with teams id
        roster_span = soup.find('span', id = 'Current_roster')
        roster_table = roster_span.findNext('table')

        roster_players = []
        player_rows = roster_table.findChildren('tr')
        player_row_count = 0
        for player_row in player_rows:
            player_row_count = player_row_count + 1

            if player_row_count > 1:
                player_cells = player_row.findChildren('th')
                player_anchor = player_cells[0].findChildren('a')

                roster_player = {
                    "player_url": urljoin(WIKIPEDIA_BASE_URL, player_anchor[0].get('href')),
                    "player_name": player_anchor[0].text
                }
                roster_players.append(roster_player)

        logging.info('found %s players on %s', len(roster_players), team['team_url'])
        return roster_players
    else:
        message = 'http request failed for league page'
        logging.error(message)
        raise Exception(message)



def extract_player(player):
    """retrieve data from player data from wikipedia page"""
    logging.debug('scraping data from %s', player['player_url'])

    # page contents
    player_page = requests.get(player['player_url'], timeout = REQUEST_READ_TIMEOUT)

    # parse the contents if the page was retrieved
    if player_page.status_code == 200:
        soup = BeautifulSoup(player_page.text, 'lxml')

        #  scrape the player information in the infobox
        player = {
            "player_name": player['player_name'],
            "player_url": player['player_url']
        }

        #  player tombstone information is in an infobox
        infobox_table = soup.find('table', {"class": "infobox vcard"})
        infobox_rows = infobox_table.findChildren('tr')
        for infobox_row in infobox_rows:
            attribute_name_column = infobox_row.findChildren('th')
            attribute_name = None
            if len(attribute_name_column) > 0:
                attribute_name = clean_attribute_name(attribute_name_column[0].text)

            attribute_value = None
            attribute_value_column = infobox_row.findChildren('td')
            if len(attribute_value_column) > 0:
                #  handle some of the infobox attributes more carefully
                match attribute_name:
                    case 'born':
                        bday_span = soup.find('span', {"class": "bday"})
                        if bday_span is not None:
                            if len(bday_span) > 0:
                                attribute_value = datetime.strptime(bday_span.text, "%Y-%m-%d")
                    case 'height':
                        attribute_value = int(attribute_value_column[0].text.split('(')[1].split('\xa0')[0])
                    case 'weight':
                        attribute_value = int(attribute_value_column[0].text.split('(')[1].split('\xa0')[0])
                    case 'position':
                        attribute_value = clean_attribute_value(attribute_value_column[0].text)
                    case _:
                        attribute_value = clean_attribute_value(attribute_value_column[0].text)

            #  only add the attribute if there is a value
            if attribute_name is not None and attribute_value is not None:
                player[attribute_name] = attribute_value


        #  scrape the career statistics
        try:
            career_statistic_span = soup.find('span', id = 'Career_statistics')
            career_statistic_table = career_statistic_span.find_next('table')
            career_statistic_rows = career_statistic_table.findChildren('tr')

            #  array of career statistics
            career_statistics = []
            for career_statistic_row in career_statistic_rows:
                columns = career_statistic_row.findChildren('td')
                if len(columns) > 0:
                    try:
                        career_statistic = {
                            "season": clean_attribute_value(columns[0].text.strip()),
                            "team": clean_attribute_value(columns[1].text.strip()),
                            "league": clean_attribute_value(columns[2].text.strip()),
                            "regular_season_games_played_count": clean_career_statistic_number(columns[3].text),
                            "regular_season_goal_count": clean_career_statistic_number(columns[4].text),
                            "regular_season_assist_count": clean_career_statistic_number(columns[5].text),
                            "regular_season_point_count": clean_career_statistic_number(columns[6].text),
                            "regular_season_penalty_minute_count": clean_career_statistic_number(columns[7].text),
                            "playoff_season_games_played_count": clean_career_statistic_number(columns[8].text),
                            "playoff_season_goal_count": clean_career_statistic_number(columns[9].text),
                            "playoff_season_assist_count": clean_career_statistic_number(columns[10].text),
                            "playoff_season_point_count": clean_career_statistic_number(columns[11].text),
                            "playoff_season_penalty_minute_count": clean_career_statistic_number(columns[12].text)
                        }
                        career_statistics.append(career_statistic)
                    except Exception as e:
                        #  the player pages are not uniform
                        logging.error('failed parsing player stats from %s', player['player_url'])
                        logging.error(str(e))
                        #  swallow the error and continue looking

                #  add the career stats to the player dictionary
                player['career_statistics'] = career_statistics
        except Exception as e:
            logging.error('structure of career statistics is unexpected for %s', player['player_url'])
            logging.error(str(e))
            #  swallow the error and continue to next player


        return player
    else:
        message = 'http request for player ' + player['player_url']
        logging.error(message)
        #  swallow the error and process the next player



def save_player_json(output_path):
    """serialize the player details to JSON files"""
    player_count = 0
    for player_detail in extract_players():
        player_count = player_count + 1
        if player_detail is not None:
            player_file_name = (player_detail['player_url'].rsplit('/', 1)[-1]).lower()
            with open(output_path.joinpath(player_file_name + '.json'), 'w', encoding = "utf8") as player_file:
                player_file.write(json.dumps(player_detail, indent = 4, cls = NumpyEncoder, default=str))
        else:
            logging.error('blank player')

    logging.info('wrote %s players', player_count)


def extract_players():
    """return a dictionary object with all player data"""
    #  extract the data from wikipedia
    players = []

    #  scrape an array of teams pages
    teams = extract_teams()
    for team in teams:
        #  scrape a list of players from the team page
        roster = extract_roster(team)
        for rostered_player in roster:
            players.append(extract_player(rostered_player))

    logging.info('found %s players', len(players))
    return players



def save_team_json(output_folder_name:str):
    """write team data in JSON format"""

    output_path = Path(output_folder_name)

    team_count = 0
    for team in extract_teams():
        team_count = team_count + 1
        if team is not None:
            team_file_name = team['team_name'].lower().replace(' ', '_')
            with open(output_path.joinpath(team_file_name + '.json') , 'w', encoding = 'utf8') as team_file:
                team_file.write(json.dumps(team, indent = 4, cls = NumpyEncoder, default=str))
        else:
            logging.error('blank team')

    logging.info('write %s teams', team_count)


def save_to_folder(output_folder_name: str, format: int):
    """save extract to a format"""

    output_path = Path(output_folder_name)
    json_path = output_path.joinpath(JSON_PATH_NAME)
    player_path = json_path.joinpath(PLAYER_PATH_NAME)
    team_path = json_path.joinpath(TEAM_PATH_NAME)

    json_path.mkdir(exist_ok = True)
    player_path.mkdir(exist_ok = True)
    team_path.mkdir(exist_ok = True)

    match format:
        case 0:
            save_team_json(team_path)
            save_player_json(player_path)
        case _:
            raise Exception('unknown file format')


