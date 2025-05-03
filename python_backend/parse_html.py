from bs4 import BeautifulSoup
import json

def parse_html(file_name:str):
    # Load your HTML (from file or string)
    with open(file_name, "r") as file:
        html = file.read()

    soup = BeautifulSoup(html, "html.parser")

    # Find all table rows except the header
    rows = soup.select("table.bylawTable tr")[1:]

    # Extract data into a list of dictionaries
    bylaws = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 2:
            link_tag = cols[0].find("a")
            number = link_tag.text.strip()
            link = link_tag['href'].strip()
            title = cols[1].text.strip()
            bylaws.append({
                "_id": number,
                "title": title,
                "pdf": link,
                "pdf_content": ""
            }) 

    # return the json list
    return bylaws


#parse_html("bylaws.html")