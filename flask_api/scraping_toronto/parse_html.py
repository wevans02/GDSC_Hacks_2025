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
        # Specify encoding, common for web pages
        with open(file_name, "r", encoding="utf-8") as file:
            html = file.read()
    except FileNotFoundError:
        print(f"Error: HTML file not found at {file_name}")
        return []
    except Exception as e:
        print(f"Error reading HTML file {file_name}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    # Define the base URL for resolving relative links found in the HTML
    base_url = "https://www.toronto.ca/"

    bylaws = []
    # Find all tables with the specific class 'bylawDefault' used in the HTML
    tables = soup.find_all("table", class_="bylawDefault")

    if not tables:
        print("Error: No tables with class 'bylawDefault' found in the HTML.")
        return []

    print(f"Found {len(tables)} potential bylaw tables.")

    for table in tables:
        # Iterate through table rows (tr), skipping the header row (th)
        rows = table.find_all("tr")
        if not rows:
            continue

        for row in rows:
            # Find table data cells (td) within each row
            cols = row.find_all("td")

            # Expecting at least 2 columns for Chapter link and Title
            # Check for td elements specifically, not th
            if len(cols) >= 2 and cols[0].name == 'td':
                # First column (td.s2) should contain the link
                link_tag = cols[0].find("a")
                # Second column (td.s3) should contain the title
                title_tag = cols[1] # The whole cell contains the title text

                if link_tag and link_tag.has_attr('href') and title_tag:
                    chapter_text = link_tag.text.strip()
                    relative_link = link_tag['href'].strip()
                    title = title_tag.text.strip()

                    # Construct absolute URL using urljoin
                    absolute_link = urljoin(base_url, relative_link)

                    # Basic validation: check if chapter text exists, link ends with .pdf, and title exists
                    if chapter_text and absolute_link.lower().endswith(".pdf") and title:
                        # Exclude "Reserved" chapters as they likely don't have valid PDFs
                        if "reserved" not in title.lower():
                            print(f"  Found: {chapter_text} - {title} - {absolute_link}")
                            bylaws.append({
                                "_id": chapter_text, # Use chapter text like "Chapter 1" as ID
                                "title": title,
                                "pdf": absolute_link # Store the absolute URL
                            })
                        else:
                             print(f"  Skipping reserved chapter: {chapter_text} - {title}")
                    # else:
                        # Optional: Log rows skipped due to missing data or non-PDF links
                        # print(f"  Skipping row - Invalid data/link found: {chapter_text}, {title}, {absolute_link}")
                # else:
                    # Log rows where link or title tag is missing within the expected columns
                    # print(f"  Skipping row - Missing link or title tag in columns.")
                    # pass
            # else:
                 # Row doesn't have enough 'td' columns or is a header row ('th')
                 # print(f"  Skipping row - Found {len(cols)} 'td' columns or header row.")
                 # pass


    print(f"Finished parsing. Extracted {len(bylaws)} valid bylaw entries.")
    return bylaws

# Example usage (optional, for testing this script directly)
if __name__ == "__main__":
    results = parse_html("lawmcode.htm")
    if results:
        print("\nSample extracted data:")
        # Print first and last few items to verify
        print(results[0])
        if len(results) > 1:
            print(results[-1])
    else:
        print("No data extracted.")
