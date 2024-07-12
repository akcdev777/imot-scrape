import requests
from bs4 import BeautifulSoup
import pandas as pd
import chardet
import re
from datetime import datetime
from urllib.parse import urlparse, urljoin
import aiohttp
import asyncio

# Function to extract URLs of all pages from the pagination section
def extract_pagination_urls(soup, base_url):
    page_urls = []
    for link in soup.find_all('a', class_='pageNumbersSelect'):
        href = format_url(link['href'], base_url)
        page_urls.append(href)
    for link in soup.find_all('a', class_='pageNumbers'):
        href = format_url(link['href'], base_url)
        page_urls.append(href)
    return page_urls

# Function to format URLs correctly
def format_url(href, base_url):
    if href.startswith('//'):
        return 'https:' + href
    return urljoin(base_url, href)

# Regular expression pattern to match Bulgarian date format
def parse_date(date_str):
    bulgarian_months = {
        'януари': 1, 'февруари': 2, 'март': 3, 'април': 4, 'май': 5, 'юни': 6,
        'юли': 7, 'август': 8, 'септември': 9, 'октомври': 10, 'ноември': 11, 'декември': 12
    }
    pattern = r"(Публикувана в|Коригирана в) (\d{2}:\d{2}) на (\d+) ([а-я]+), (\d{4}) год."
    match = re.search(pattern, date_str, re.IGNORECASE)
    if match:
        action, time, day, month, year = match.groups()
        month_number = bulgarian_months.get(month.lower(), 1)
        date_time_str = f"{year}-{month_number:02d}-{day} {time}:00"
        return action, datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A', 'N/A'

async def fetch(session, url):
    async with session.get(url) as response:
        raw_content = await response.read()
        detected_encoding = chardet.detect(raw_content)['encoding']
        return raw_content.decode(detected_encoding, errors='replace')

async def fetch_property_details(session, href_value):
    try:
        detail_response = await fetch(session, href_value)
        property_soup = BeautifulSoup(detail_response, 'html.parser')

        ad_price_div = property_soup.find('div', class_='adPrice')
        if ad_price_div:
            # Extract price per square meter
            price_per_sqm_span = ad_price_div.find('span', id='cenakv')
            price_per_sqm = price_per_sqm_span.get_text(strip=True) if price_per_sqm_span else 'N/A'

            # Extract publish or edit timestamp
            info_div = ad_price_div.find('div', class_='info')
            publish_time_div = info_div.find_all('div')[0] if info_div else None
            if publish_time_div:
                publish_time_text = publish_time_div.get_text(strip=True)
                action, date_time = parse_date(publish_time_text)
                if action == "Коригирана в":
                    publish_date = 'N/A'
                    edit_date = date_time
                else:
                    publish_date = date_time
                    edit_date = 'N/A'
            else:
                publish_date = 'N/A'
                edit_date = 'N/A'

            # Extract number of visits
            visits_span = info_div.find('span', style='font-weight:bold;')
            visits_count = visits_span.get_text(strip=True) if visits_span else 'N/A'

            return price_per_sqm, publish_date, edit_date, visits_count, href_value
    except Exception as e:
        print(f"An error occurred while fetching property details: {e}")
        return 'N/A', 'N/A', 'N/A', 'N/A', href_value

async def scrape_properties(session, url):
    try:
        main_page_content = await fetch(session, url)
        soup = BeautifulSoup(main_page_content, 'html.parser')

        properties = soup.find_all('table', width='660', cellspacing='0', cellpadding='0', border='0')

        property_data = []
        private_seller_data = []
        seen_urls = set()

        phone_pattern = r'тел\.: (\d{10,12})'
        price_pattern = r'(\d+\s?\d*)\s*(лв\.|EUR)'

        tasks = []

        for property_table in properties:
            try:
                price_div = property_table.find('div', class_='price')
                price_text = price_div.get_text(strip=True) if price_div else 'N/A'

                price_match = re.search(price_pattern, price_text)
                if price_match:
                    price = int(price_match.group(1).replace(' ', ''))
                    currency = price_match.group(2)
                else:
                    price = 'N/A'
                    currency = 'N/A'

                href_a_tag = property_table.find('a', class_='photoLink')
                href_value = href_a_tag['href'] if href_a_tag else 'N/A'

                if href_value != 'N/A':
                    href_value = format_url(href_value, url)

                seller_a_tag = property_table.find('a', class_='logoLink')
                seller = seller_a_tag['href'].replace('//', '') if seller_a_tag else 'N/A'

                location_a_tag = property_table.find('a', class_='lnk2')
                location = location_a_tag.get_text(strip=True) if location_a_tag else 'N/A'

                property_type_a_tag = property_table.find('a', class_='lnk1')
                property_type = property_type_a_tag.get_text(strip=True) if property_type_a_tag else 'N/A'

                description_td = property_table.find('td', width='520', colspan='3', height='50', style='padding-left:4px')
                if description_td:
                    description_text = description_td.get_text(strip=True)

                    size_pattern = r'(\d+)\s*кв\.м'
                    size_match = re.search(size_pattern, description_text)
                    size = size_match.group(1) if size_match else 'N/A'

                    floor_pattern = r'(\d+)-ти\s*ет'
                    floor_match = re.search(floor_pattern, description_text)
                    floor = floor_match.group(1) if floor_match else 'N/A'

                    year_pattern = r'Тухла\s*(\d{4})\s*г\.'
                    year_match = re.search(year_pattern, description_text)
                    year = year_match.group(1) if year_match else 'N/A'

                    phone_number = 'N/A'
                    phone_match = re.search(phone_pattern, description_text)
                    if phone_match:
                        phone_number = phone_match.group(1)

                    if href_value != 'N/A' and price != 'N/A' and href_value not in seen_urls:
                        seen_urls.add(href_value)
                        task = asyncio.ensure_future(fetch_property_details(session, href_value))
                        tasks.append(task)
                        property_entry = (price, currency, href_value, seller, location, size, floor, year, property_type, phone_number)
                        property_data.append(property_entry)
            except Exception as e:
                print(f"An error occurred while scraping property: {e}")

        results = await asyncio.gather(*tasks)

        final_property_data = []

        for i, result in enumerate(results):
            price_per_sqm, publish_date, edit_date, visits_count, detail_url = result
            price, currency, href_value, seller, location, size, floor, year, property_type, phone_number = property_data[i]

            property_entry = {
                'Price': price,
                'Currency': currency,
                'URL': detail_url,  # Store the second URL
                'Seller': seller,
                'Location': location,
                'Size': size,
                'Floor': floor,
                'Year': year,
                'Property Type': property_type,
                'Phone': phone_number,
                'Price per sqm': price_per_sqm,
                'Publish Date': publish_date,
                'Edit Date': edit_date,  # Added field for edit date
                'Visits Count': visits_count
            }

            if seller == 'N/A':
                private_seller_data.append(property_entry)
            else:
                final_property_data.append(property_entry)

            print(f"Price: {price}, Currency: {currency}, URL: {detail_url}, Seller: {seller}, Location: {location}, Size: {size}, Floor: {floor}, Year: {year}, Property Type: {property_type}, Phone: {phone_number}")
            print(f"Price per sqm: {price_per_sqm}, Publish Date: {publish_date}, Edit Date: {edit_date}, Visits Count: {visits_count}")

        return final_property_data, private_seller_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {url}: {e}")
        return [], []

async def main():
    base_url = 'https://imoti-plovdiv.imot.bg/'  # replace with actual URL

    async with aiohttp.ClientSession() as session:
        main_page_content = await fetch(session, base_url)
        soup = BeautifulSoup(main_page_content, 'html.parser')

        page_urls = [base_url] + extract_pagination_urls(soup, base_url)
        print(f"Total pages to scrape: {len(page_urls)}")

        all_property_data = []
        all_private_seller_data = []

        tasks = []
        for url in page_urls:
            task = asyncio.ensure_future(scrape_properties(session, url))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        for property_data, private_seller_data in results:
            all_property_data.extend(property_data)
            all_private_seller_data.extend(private_seller_data)

        df = pd.DataFrame(all_property_data)
        df_private = pd.DataFrame(all_private_seller_data)

        df.to_csv('properties.csv', index=False)
        df_private.to_csv('private_seller_properties.csv', index=False)

        print("Scraping completed and data saved to properties.csv and private_seller_properties.csv")

if __name__ == '__main__':
    asyncio.run(main())
