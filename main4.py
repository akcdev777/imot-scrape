import requests
from bs4 import BeautifulSoup
import pandas as pd
import chardet
import re
from datetime import datetime

# Function to extract URLs of all pages from the pagination section
def extract_pagination_urls(soup):
    page_urls = []

    # First, extract the current page number
    current_page_num = None
    page_info_span = soup.find('span', class_='pageNumbersInfo')
    if page_info_span:
        page_info_text = page_info_span.get_text(strip=True)
        if 'Страница' in page_info_text:
            parts = page_info_text.split(' ')
            current_page_num = int(parts[1])

    # Next, extract URLs of all available pages
    page_numbers_select = soup.find_all('a', class_='pageNumbersSelect')
    for link in page_numbers_select:
        href = link['href']
        if href.startswith('//'):
            href = 'https:' + href
        page_urls.append(href)

    page_numbers = soup.find_all('a', class_='pageNumbers')
    for link in page_numbers:
        href = link['href']
        if href.startswith('//'):
            href = 'https:' + href
        page_urls.append(href)  # Remove '//' from href

    return page_urls

# Function to scrape property data from a given URL
def scrape_properties(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        encoding = chardet.detect(response.content)['encoding']
        response.encoding = encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        properties = soup.find_all('table', width='660', cellspacing='0', cellpadding='0', border='0')

        property_data = []
        private_seller_data = []
        seen_urls = set()

        # Regex pattern to match phone number with 10 to 12 digits
        phone_pattern = r'тел\.: (\d{10,12})'
        # Regex pattern to match price and currency
        price_pattern = r'(\d+\s?\d*)\s*(лв\.|EUR)'

        for property_table in properties:
            try:
                # Extracting details from the property table
                price_div = property_table.find('div', class_='price')
                price_text = price_div.get_text(strip=True) if price_div else 'N/A'
                
                # Extract price and currency
                price_match = re.search(price_pattern, price_text)
                if price_match:
                    price = int(price_match.group(1).replace(' ', ''))
                    currency = price_match.group(2)
                else:
                    price = 'N/A'
                    currency = 'N/A'

                href_a_tag = property_table.find('a', class_='photoLink')
                href_value = href_a_tag['href'] if href_a_tag else 'N/A'

                seller_a_tag = property_table.find('a', class_='logoLink')
                seller = seller_a_tag['href'].replace('//', '') if seller_a_tag else 'N/A'

                location_a_tag = property_table.find('a', class_='lnk2')
                location = location_a_tag.get_text(strip=True) if location_a_tag else 'N/A'

                property_type_a_tag = property_table.find('a', class_='lnk1')
                property_type = property_type_a_tag.get_text(strip=True) if property_type_a_tag else 'N/A'

                # Extracting description including size, floor, year, and phone number
                description_td = property_table.find('td', width='520', colspan='3', height='50', style='padding-left:4px')
                if description_td:
                    description_text = description_td.get_text(strip=True)

                    # Extract size
                    size_pattern = r'(\d+)\s*кв\.м'
                    size_match = re.search(size_pattern, description_text)
                    size = size_match.group(1) if size_match else 'N/A'

                    # Extract floor
                    floor_pattern = r'(\d+)-ти\s*ет'
                    floor_match = re.search(floor_pattern, description_text)
                    floor = floor_match.group(1) if floor_match else 'N/A'

                    # Extract year
                    year_pattern = r'Тухла\s*(\d{4})\s*г\.'
                    year_match = re.search(year_pattern, description_text)
                    year = year_match.group(1) if year_match else 'N/A'

                    # Extract phone number
                    phone_number = 'N/A'
                    phone_match = re.search(phone_pattern, description_text)
                    if phone_match:
                        phone_number = phone_match.group(1)

                    if href_value != 'N/A' and price != 'N/A' and href_value not in seen_urls:
                        seen_urls.add(href_value)
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        property_entry = {
                            'Price': price,
                            'Currency': currency,
                            'URL': href_value,
                            'Seller': seller,
                            'Location': location,
                            'Size': size,
                            'Floor': floor,
                            'Year': year,
                            'Property Type': property_type,
                            'Phone': phone_number,
                            'Timestamp': timestamp
                        }

                        if seller == 'N/A':
                            private_seller_data.append(property_entry)
                        else:
                            property_data.append(property_entry)

                        print(f"Price: {price}, Currency: {currency}, URL: {href_value}, Seller: {seller}, Location: {location}, Size: {size}, Floor: {floor}, Year: {year}, Property Type: {property_type}, Phone: {phone_number}, Timestamp: {timestamp}")

            except Exception as e:
                print(f"An error occurred while scraping property: {e}")

        return property_data, private_seller_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {url}: {e}")
        return [], []

# URL of the property listing page
base_url = 'https://www.imot.bg/pcgi/imot.cgi?act=3&slink=auysd2&f1=1'  # replace with actual URL

try:
    response = requests.get(base_url)
    response.raise_for_status()  # Raise an exception for bad status codes
    encoding = chardet.detect(response.content)['encoding']
    response.encoding = encoding
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract all pagination URLs
    page_urls = [base_url] + extract_pagination_urls(soup)  # Include the base URL of the first page
    print(f"Total pages to scrape: {len(page_urls)}")

    # Initialize lists to store all properties
    all_property_data = []
    all_private_seller_data = []

    # Iterate through each page URL and scrape properties
    for url in page_urls:
        property_data, private_seller_data = scrape_properties(url)
        all_property_data.extend(property_data)
        all_private_seller_data.extend(private_seller_data)

    # Convert to DataFrame and save to CSV
    df = pd.DataFrame(all_property_data)
    df_private = pd.DataFrame(all_private_seller_data)

    df.to_csv('properties.csv', index=False)
    df_private.to_csv('private_seller_properties.csv', index=False)

    print("Scraping completed and data saved to properties.csv and private_seller_properties.csv")

except requests.exceptions.RequestException as e:
    print(f"Error accessing page {base_url}: {e}")
