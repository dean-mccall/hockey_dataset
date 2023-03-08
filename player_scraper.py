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

    span = soup.find('span', id = 'Career_statistics')
    table = span.find_next('table')
    rows = table.findAll('tr')

    season_stats = []

    for row in rows:
        columns = row.findAll('td')
        if len(columns) > 0:
            stat = {
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
            season_stats.append(stat)

    print('this')

else:
    print('that')