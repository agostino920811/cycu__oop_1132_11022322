import requests
from bs4 import BeautifulSoup

def fetch_tvbs_news():
    url = 'https://news.tvbs.com.tw/'
    response = requests.get(url)
    response.encoding = 'utf-8'
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = soup.find_all('h2', class_='news_title')
        
        for index, headline in enumerate(headlines, start=1):
            print(f"{index}. {headline.text.strip()}")
    else:
        print(f"Failed to retrieve news. Status code: {response.status_code}")

if __name__ == "__main__":
    fetch_tvbs_news()