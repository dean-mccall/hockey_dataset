import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime

#
#  remove non-numeric characters from number in career statistics
#
def clean_career_statistic_number(raw_text):
    if raw_text is None:
        result = None
    else:
        result = raw_text.strip().replace('—', '')
        if len(result) > 0:
            result = int(result)
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



#
#  retrieve data from player data from wikipedia page
#
def scrape_player(wikipedia_url):

    # page contents
    page = requests.get(wikipedia_url)

    # parse the contents if the page was retrieved
    if page.status_code == 200:
        soup = BeautifulSoup(page.text, 'lxml')

        #  scrape the player information in the infobox
        player = {}
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
                        attribute_value = attribute_value_column[0].text.replace('\n', '')
                    case _:
                        attribute_value = attribute_value_column[0].text
                

            if attribute_name is not None:
                player[attribute_name] = attribute_value


        #  scrape the career statistics
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

            player['career_statistics'] = career_statistics

        return player

    else:
        print('that')



def main():
    # page to scrape
    url = "https://en.wikipedia.org/wiki/Nathan_MacKinnon"
    # url = "https://en.wikipedia.org/wiki/Wayne_Gretzky"

    player_data = scrape_player(url)

    print("done")



if __name__ == '__main__':
    main()