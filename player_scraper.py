import requests
from bs4 import BeautifulSoup
import pandas as pd
import re


def clean_number(raw_text):
    if raw_text is None:
        result = None
    else:
        result = raw_text.strip().replace('—', '')
        if len(result) > 0:
            result = int(result)
        else:
            result = None

    return result





class HockeyPlayer:
    player_name = ""
    birth_date = None

    def __init__(self, player_name, birth_date):
        self.player_name = player_name
        self.birth_date = birth_date

    

class Skater(HockeyPlayer):
    def __init__(self, player_name, birth_date):
        super().__init__(player_name, birth_date)
        


class Goalie(HockeyPlayer):
    def __init__(self, player_name, birth_date):
        super().__init__(player_name, birth_date)

    


# page to scrape
# url = "https://en.wikipedia.org/wiki/Nathan_MacKinnon"
url = "https://en.wikipedia.org/wiki/Wayne_Gretzky"


# page contents
page = requests.get(url)

# parse the contents if the page was retrieved
if page.status_code == 200:
    soup = BeautifulSoup(page.text, 'lxml')

    career_statistic_span = soup.find('span', id = 'Career_statistics')
    career_statistic_table = career_statistic_span.find_next('table')
    career_statistic_rows = career_statistic_table.findAll('tr')

    career_statistics = []

    for career_statistic_row in career_statistic_rows:
        columns = career_statistic_row.findAll('td')
        if len(columns) > 0:
            career_statistic = {
                "season": columns[0].text.strip(),
                "team": columns[1].text.strip(),
                "league": columns[2].text.strip(),
                "regular_season_games_played_count": clean_number(columns[3].text),
                "regular_season_goal_count": clean_number(columns[4].text),
                "regular_season_assist_count": clean_number(columns[5].text),
                "regular_season_point_count": clean_number(columns[6].text),
                "regular_season_penalty_minute_count": clean_number(columns[7].text),
                "playoff_season_games_played_count": clean_number(columns[8].text),
                "playoff_season_goal_count": clean_number(columns[9].text),
                "playoff_season_assist_count": clean_number(columns[10].text),
                "playoff_season_point_count": clean_number(columns[11].text),
                "playoff_season_penalty_minute_count": clean_number(columns[12].text)
            }
            career_statistics.append(career_statistic)



    player = {}
    infobox_table = soup.find('table', {"class": "infobox vcard"})
    infobox_rows = infobox_table.findAll('tr')
    for infobox_row in infobox_rows:
        attribute_name_column = infobox_row.findAll('th')
        attribute_name = None
        if len(attribute_name_column) > 0:
            attribute_name = attribute_name_column[0].text            

        attribute_value = None
        attribute_value_column = infobox_row.findAll('td')
        if len(attribute_value_column) > 0:
            attribute_value = attribute_value_column[0].text

        if attribute_name is not None:
            player[attribute_name] = attribute_value

    print('this')

else:
    print('that')