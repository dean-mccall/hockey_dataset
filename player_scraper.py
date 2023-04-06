import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import logging
from requests.compat import urljoin
import os
import json
from numpyencoder import NumpyEncoder
import shutil
import time


#  configure logging
logging.basicConfig(level = logging.INFO, format = '%(asctime)s | %(name)s | %(levelname)s | %(message)s')

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org/'
NHL_LEAGUE_URL = urljoin(WIKIPEDIA_BASE_URL, '/wiki/National_Hockey_League')


#
#  remove non-numeric characters from number in career statistics
#
def clean_career_statistic_number(raw_text):
    if raw_text is None:
        result = None
    else:
        result = raw_text.strip().replace('—', '').replace(',', '')
        if len(result) > 0:
            result = pd.to_numeric(result)
        else:
            result = None

    return result


#
#  translate infobox label to snake case attribute name
#
def clean_attribute_name(raw_text):
    result = None
    
    # lower case
    result = raw_text.lower()

    # snake case
    result = result.replace(' ', '_')

    # special characters

    return result


def clean_attribute_value(raw_text):
    return raw_text.replace(u'\n', '').replace(u'\u2013', '-')


#
#  NHL
#
def scrape_league(league_wikipedia_url):
    logging.debug('starting league scrape.  league_wikipedia_url = %s', league_wikipedia_url)

    # result array
    teams = []

    # read the page
    league_page = requests.get(league_wikipedia_url)
    if league_page.status_code == 200:
        logging.debug('finding teams')

        #  parse the page
        soup = BeautifulSoup(league_page.text, 'lxml')

        #  find span with teams id
        teams_span = soup.find('span', id = 'Teams')

        #  find the table of teams
        teams_table = teams_span.find_next('table')
        team_rows = teams_table.find_all('tr')
        row_count = 0
        for team_row in team_rows:
            row_count = row_count + 1

            #  skip the header row
            if row_count > 1:
                team_header_cells = team_row.select('th')
                team_cells = team_row.select('td')
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
                    team_anchor = team_cells[0].select('a')
                    team_url = team_anchor[0].get('href')
                    team_name = team_anchor[0].text

                    team = {
                        "league_conference": league_conference,
                        "conference_division": conference_division,
                        "team": team_name,
                        "team_url": urljoin(WIKIPEDIA_BASE_URL, team_url)
                    }
                    teams.append(team)

        logging.info('collected %s teams', len(teams))
        return teams
    else:
        message = 'http request failed retrieving league page'
        logging.error(message)
        raise Exception(message)

    




#
#  find the players on a team
#
def scrape_roster(team):
    logging.debug('collecting roster for %s', team['team_url'])

    #  read the page
    team_page = requests.get(team['team_url'])
    if team_page.status_code == 200:
        logging.debug('finding roster')
        soup = BeautifulSoup(team_page.text, 'lxml')

        #  find span with teams id
        players_and_personnel_span = soup.find('span', id = 'Players_and_personnel')
        roster_span = soup.find('span', id = 'Current_roster')
        roster_table = roster_span.findNext('table')

        players = []
        player_rows = roster_table.findChildren('tr')
        player_row_count = 0
        for player_row in player_rows:
            player_row_count = player_row_count + 1

            if player_row_count > 1:
                player_cells = player_row.findChildren('th')
                player_anchor = player_cells[0].findChildren('a')

                player = {
                    "player_url": urljoin(WIKIPEDIA_BASE_URL, player_anchor[0].get('href')),
                    "player_name": player_anchor[0].text
                }
                players.append(player)

        logging.info('found %s players on %s', len(players), team['team_url'])
        return players
    else:
        message = 'http request failed for league page'
        logging.error(message)
        raise Exception(message)



#
#  retrieve data from player data from wikipedia page
#
def scrape_player(player):

    # page contents
    player_page = requests.get(player['player_url'])

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
        infobox_rows = infobox_table.findAll('tr')
        for infobox_row in infobox_rows:
            attribute_name_column = infobox_row.findAll('th')
            attribute_name = None
            if len(attribute_name_column) > 0:
                attribute_name = clean_attribute_name(attribute_name_column[0].text)

            attribute_value = None
            attribute_value_column = infobox_row.findAll('td')
            if len(attribute_value_column) > 0:
                #  handle some of the infobox attributes more carefully
                match attribute_name:
                    case 'born':
                        bday_span = soup.find('span', {"class": "bday"})
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
            if attribute_name is not None:
                player[attribute_name] = attribute_value


        #  scrape the career statistics
        try:
            career_statistic_span = soup.find('span', id = 'Career_statistics')
            career_statistic_table = career_statistic_span.find_next('table')
            career_statistic_rows = career_statistic_table.findAll('tr')

            #  array of career statistics
            career_statistics = []
            for career_statistic_row in career_statistic_rows:
                columns = career_statistic_row.findAll('td')
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
                    except (IndexError, ValueError):
                        #  the player pages are not uniform
                        logging.error('failed parsing player stats from %s', player['player_url'])
                        #  swallow the error and continue looking

                #  add the career stats to the player dictionary
                player['career_statistics'] = career_statistics
        except:
            logging.error('structure of career statistics is unexpected for %s', player['player_url'])


        return player
    else:
        message = 'http request for player ' + player['player_url']
        logging.error(message)
        # raise Exception(message)
    

#
#  archive a folder
#
def archive_folder(source_folder_name):
    logging.debug('archiving %s', source_folder_name)

    base_name = os.path.basename(os.path.normpath(source_folder_name))
    time_stamp = time.strftime('%Y%m%d-%H%M%S')
    target_folder_name = 'data/archive/' + time_stamp + '_' + base_name

    shutil.move(source_folder_name, target_folder_name)
    logging.debug('moved %s to %s', source_folder_name, target_folder_name)


#
#  serialize the player details to JSON files
#
def save_json(player_details):
    #  serialize JSON
    if os.path.exists('data/json'):
        #  archive the existing folder and create a new one
        archive_folder('data/json')

    os.mkdir('data/json')

    player_count = 0
    for player_detail in player_details:
        player_count = player_count + 1
        player_file_name = player_detail['player_url'].rsplit('/', 1)[-1]
        with open('data/json/' + player_file_name + '.json', 'w') as player_file:
            player_file.write(json.dumps(player_detail, indent = 4, cls = NumpyEncoder, default=str))    

    logging.info('wrote %s players to data/json', player_count)


def main():
    logging.info('starting')




    #  extract the data from wikipedia
    player_details = []

    #  scrape an array of teams pages
    teams = scrape_league(NHL_LEAGUE_URL)
    logging.info('scraped %s teams', len(teams))
    for team in teams:

        #  scrape a list of players from the team page
        players = scrape_roster(team)
        logging.info('scraped %s players on team %s', len(players), team['team'])
        for player in players:

            # get career statisttics for each player
            logging.debug('scraping %s', player['player_url'])

            #  append to list of player details
            player_details.append(scrape_player(player))


    #  save the data
    logging.info('saving the data')



    #  make target data directory
    if not os.path.exists('data'):
        os.mkdir('data')

    #  make archive directory
    if not os.path.exists('data/archive'):
        os.mkdir('data/archive')


    #  serialize J
    save_json(player_details)


    logging.info('ending')



if __name__ == '__main__':
    main()