import requests
from bs4 import BeautifulSoup
import pandas as pd
import chardet
import re
import asyncio
import aiohttp
from datetime import datetime
from urllib.parse import urlparse, urljoin
import logging

# Configure logging
logging.basicConfig(filename='scraping_log.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Function to extract URLs of all pages from the pagination section
def extract_pagination_urls(soup, base_url):
    page_urls = []

    # First, extract the current page number
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
        page_urls.append(format_url(href, base_url))

    page_numbers = soup.find_all('a', class_='pageNumbers')
    for link in page_numbers:
        href = link['href']
        page_urls.append(format_url(href, base_url))

    return page_urls

# Function to format URLs correctly
def format_url(href, base_url):
    if href.startswith('//'):
        href = 'https:' + href
    elif href.startswith('/'):
        parsed_base_url = urlparse(base_url)
        href = urljoin(base_url, href)
    elif not href.startswith('http'):
        href = urljoin(base_url, href)
    return href

# Regular expression pattern to match Bulgarian date format
def parse_publish_date(date_str):
    bulgarian_months = {
        'януари': 1, 'февруари': 2, 'март': 3, 'април': 4, 'май': 5, 'юни': 6,
        'юли': 7, 'август': 8, 'септември': 9, 'октомври': 10, 'ноември': 11, 'декември': 12
    }
    pattern = r"(Публикувана|Коригирана) в (\d{2}:\d{2}) на (\d+) ([а-я]+), (\d{4}) год."
    match = re.search(pattern, date_str, re.IGNORECASE)
    if match:
        status, time, day, month, year = match.groups()
        month_number = bulgarian_months.get(month.lower(), 1)
        date_time_str = f"{year}-{month_number:02d}-{day} {time}:00"
        return status, datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
    return 'N/A', 'N/A'

async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        detected_encoding = chardet.detect(await response.read())['encoding']
        return await response.text(encoding=detected_encoding)

async def scrape_properties(url, session):
    property_data = []
    try:
        content = await fetch(session, url)
        soup = BeautifulSoup(content, 'html.parser')
        properties = soup.find_all('table', width='660', cellspacing='0', cellpadding='0', border='0')
        seen_urls = set()
        logging.info(f"Scraping {len(properties)} properties from {url}")

        for property_table in properties:
            try:
                href_a_tag = property_table.find('a', class_='photoLink')
                href_value = href_a_tag['href'] if href_a_tag else 'N/A'
                if href_value != 'N/A':
                    href_value = format_url(href_value, url)

                if href_value not in seen_urls:
                    seen_urls.add(href_value)

                    detail_content = await fetch(session, href_value)
                    detail_soup = BeautifulSoup(detail_content, 'html.parser')

                    ad_price_div = detail_soup.find('div', class_='adPrice')
                    cena_div = ad_price_div.find('div', id='cena')
                    price_text = cena_div.get_text(strip=True) if cena_div else 'N/A'
                    price_pattern = r'(\d+\s?\d*)\s*(лв\.|EUR)'
                    price_match = re.search(price_pattern, price_text)
                    if price_match:
                        price = int(price_match.group(1).replace(' ', ''))
                        currency = price_match.group(2)
                    else:
                        price = 'N/A'
                        currency = 'N/A'

                    # Extract additional information from adParams
                    ad_params_div = detail_soup.find('div', class_='adParams')
                    size, floor, total_floors, material, year = 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'
                    if ad_params_div:
                        for div in ad_params_div.find_all('div'):
                            text = div.get_text(strip=True)
                            if "Площ:" in text:
                                size_text = text.split(":")[1].strip()
                                size_match = re.search(r'(\d+)', size_text)
                                size = int(size_match.group(1)) if size_match else 'N/A'
                            elif "Етаж:" in text:
                                floor_text = text.split(":")[1].strip()
                                floor_match = re.search(r'(\d+)-ти от (\d+)', floor_text)
                                if floor_match:
                                    floor = floor_match.group(1)
                                    total_floors = floor_match.group(2)
                                else:
                                    floor = floor_text.split(" ")[0]
                            elif "Строителство:" in text:
                                material_year_text = text.split(":")[1].strip()
                                material_year_match = re.search(r'(.*), (\d{4}) г\.', material_year_text)
                                if material_year_match:
                                    material = material_year_match.group(1).strip()
                                    year = material_year_match.group(2)

                    # Extract publish timestamp
                    info_div = ad_price_div.find('div', class_='info')
                    publish_time_div = info_div.find('div')
                    if publish_time_div:
                        publish_time_text = publish_time_div.get_text(strip=True)
                        status, publish_date = parse_publish_date(publish_time_text)
                    else:
                        publish_date = 'N/A'
                        status = 'N/A'

                    # Extract number of visits
                    visits_span = info_div.find('span', style='font-weight:bold;')
                    visits_count = visits_span.get_text(strip=True) if visits_span else 'N/A'

                    # Extract location and property type
                    adv_header_div = detail_soup.find('div', class_='advHeader')
                    property_type_div = adv_header_div.find('div', class_='title')
                    property_type = property_type_div.get_text(strip=True) if property_type_div else 'N/A'
                    location_div = adv_header_div.find('div', class_='location')
                    location = location_div.get_text(strip=True) if location_div else 'N/A'

                    # Extract seller information
                    seller_name, seller_url, seller_phone = 'N/A', 'N/A', 'N/A'
                    seller_div = detail_soup.find('div', class_='boxAgenciaPaid')
                    if seller_div:
                        seller_a_tag = seller_div.find('a', class_='name')
                        if seller_a_tag:
                            seller_name = seller_a_tag.get_text(strip=True)
                            seller_url = format_url(seller_a_tag['href'], url)

                        seller_phone_div = seller_div.find('div', class_='phone')
                        if seller_phone_div:
                            seller_phone = seller_phone_div.get_text(strip=True).replace("тел.:", "").strip()

                    # Check for private seller
                    private_seller_div = detail_soup.find('div', class_='AG')
                    if private_seller_div:
                        private_seller_strong = private_seller_div.find('strong', style="font-size:16px")
                        if private_seller_strong and "Частно лице" in private_seller_strong.get_text(strip=True):
                            seller_name = "Частно лице"
                            seller_url = 'N/A'
                            seller_phone_div = private_seller_div.find('div', class_='phone')
                            if seller_phone_div:
                                seller_phone = seller_phone_div.get_text(strip=True).replace("тел.:", "").strip()

                    # Calculate price per sqm if not found
                    price_per_sqm_span = ad_price_div.find('span', id='cenakv')
                    if price_per_sqm_span:
                        price_per_sqm = price_per_sqm_span.get_text(strip=True)
                    else:
                        price_per_sqm = price / size if size != 'N/A' and size != 0 else 'N/A'

                    property_entry = {
                        'Price': price,
                        'Currency': currency,
                        'URL': href_value,
                        'Seller': seller_name,
                        'Seller URL': seller_url,
                        'Seller Phone': seller_phone,
                        'Location': location,
                        'Size': size,
                        'Floor': floor,
                        'Total Floors': total_floors,
                        'Year': year,
                        'Material': material,
                        'Property Type': property_type,
                        'Phone': seller_phone,
                        'Price per sqm': price_per_sqm,
                        'Publish Date': publish_date,
                        'Visits Count': visits_count,
                        'Status': status
                    }

                    property_data.append(property_entry)
                    logging.info(f"Scraped property: {property_entry}")

            except Exception as e:
                logging.error(f"An error occurred while scraping property details: {e}")

    except Exception as e:
        logging.error(f"An error occurred while scraping property list: {e}")

    return property_data

async def main():
    base_url = 'https://www.imot.bg/pcgi/imot.cgi?act=3&slink=av2tiu&f1=1'  # replace with actual URL
    start_time = datetime.now()
    logging.info("Scraping started")

    try:
        async with aiohttp.ClientSession() as session:
            content = await fetch(session, base_url)
            soup = BeautifulSoup(content, 'html.parser')

            # Extract all pagination URLs
            page_urls = [base_url] + extract_pagination_urls(soup, base_url)  # Include the base URL of the first page
            logging.info(f"Total pages to scrape: {len(page_urls)}")

            all_property_data = []

            for url in page_urls:
                properties = await scrape_properties(url, session)
                all_property_data.extend(properties)
                logging.info(f"Scraped {len(properties)} properties from {url}")

            # Convert to DataFrame and save to CSV
            df = pd.DataFrame(all_property_data)
            df.to_csv('properties.csv', index=False)

            end_time = datetime.now()
            logging.info(f"Scraping completed and data saved to properties.csv")
            logging.info(f"Total properties scraped: {len(all_property_data)}")
            logging.info(f"Scraping duration: {end_time - start_time}")

    except Exception as e:
        logging.error(f"Error accessing page {base_url}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
