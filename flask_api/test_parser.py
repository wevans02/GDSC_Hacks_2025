# test_parser.py
import parse_html # Import your updated parser script
import os

print("--- Starting test_parser.py ---")

html_file = "lawmcode.htm"
print(f"Checking for file: {os.path.abspath(html_file)}")

# Call the parsing function from your script
parsed_data = parse_html.parse_html(html_file)

print("\n--- test_parser.py Results ---")
print(f"parse_html function returned {len(parsed_data)} items.")

if parsed_data:
    print("First 3 items found:")
    for i, item in enumerate(parsed_data[:3]):
        print(f"{i+1}: {item}")
elif os.path.exists(html_file):
    print("Parsing failed, but the HTML file exists.")
    print("Check the DEBUG/ERROR messages printed above from within parse_html.")
else:
    print(f"Parsing failed because the file '{html_file}' was not found at this location.")

print("--- Finished test_parser.py ---")