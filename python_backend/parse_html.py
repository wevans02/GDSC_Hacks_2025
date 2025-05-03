# parse_html.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin # To construct full URLs

def parse_html(file_name: str) -> list[dict]:
    """
    Parses the lawmcode.htm file to extract bylaw chapter information.

    Args:
        file_name: The path to the HTML file (e.g., "lawmcode.htm").

    Returns:
        A list of dictionaries, where each dictionary contains:
        '_id': The chapter number (e.g., "Chapter 1").
        'title': The chapter title (e.g., "General Provisions").
        'pdf': The absolute URL to the PDF file.
    """
    print(f"Parsing HTML file: {file_name}")
    try:
        with open(file_name, "r", encoding="utf-8") as file: # Added encoding
            html = file.read()
    except FileNotFoundError:
        print(f"Error: HTML file not found at {file_name}")
        return []
    except Exception as e:
        print(f"Error reading HTML file {file_name}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    base_url = "https://www.toronto.ca/" # Base URL for relative links

    bylaws = []
    # Find all tables with the class 'bylawDefault'
    tables = soup.find_all("table", class_="bylawDefault")

    if not tables:
        print("Error: No tables with class 'bylawDefault' found in the HTML.")
        return []

    print(f"Found {len(tables)} potential bylaw tables.")

    for table in tables:
        # Find all table rows within this table, skipping the header row (usually <th>)
        rows = table.find_all("tr")
        if not rows:
            continue

        for row in rows:
            # Look for table data cells (td)
            cols = row.find_all("td")

            # Expecting at least 2 columns: Chapter/Link and Title
            if len(cols) >= 2:
                # First column (td.s2) should contain the link
                link_tag = cols[0].find("a")
                # Second column (td.s3) should contain the title
                title_tag = cols[1]

                if link_tag and link_tag.has_attr('href') and title_tag:
                    chapter_text = link_tag.text.strip()
                    relative_link = link_tag['href'].strip()
                    title = title_tag.text.strip()

                    # Construct absolute URL
                    absolute_link = urljoin(base_url, relative_link)

                    # Basic validation
                    if chapter_text and absolute_link.endswith(".pdf") and title:
                        print(f"  Found: {chapter_text} - {title} - {absolute_link}")
                        bylaws.append({
                            "_id": chapter_text, # Use chapter text like "Chapter 1" as ID
                            "title": title,
                            "pdf": absolute_link # Store the absolute URL
                        })
                    else:
                        print(f"  Skipping row - Invalid data found: {chapter_text}, {title}, {absolute_link}")
                # else:
                #     # This might be a header row or an empty row, safely ignore
                #     pass
            # else:
                 # Row doesn't have enough columns, likely header or formatting row
                 # print(f"  Skipping row - Found {len(cols)} columns, expected 2+.")
                 # pass


    print(f"Finished parsing. Extracted {len(bylaws)} bylaw entries.")
    return bylaws

# Example usage (optional, for testing)
# if __name__ == "__main__":
#     results = parse_html("lawmcode.htm")
#     if results:
#         print("\nSample extracted data:")
#         print(results[0])
#         print(results[-1])
