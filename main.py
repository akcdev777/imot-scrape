import pandas as pd
import requests
from bs4 import BeautifulSoup
from csv import writer
import time
import random
from lxml import etree as et
import chardet

# Initial setup
print("Starting the web scraping process...")
print("Please wait...")
print("")


request_url = 'https://www.imot.bg/pcgi/imot.cgi?act=3&slink=auysd2&f1=1'
response = requests.get(request_url)

# Detect encoding and set it correctly
print("Detecting the encoding of the response...")
encoding = chardet.detect(response.content)['encoding']
response.encoding = encoding

# Check if the request was successful
if response.status_code == 200:
    print("Request successful")
else:
    print("Request failed")
    exit()

# Parse the HTML content
print("Parsing the HTML content...")
soup = BeautifulSoup(response.text, 'html.parser')

# Extract property data
print("Extracting property data...")
properties = soup.find_all('tr')  # Adjust the selector as per the actual structure


property_data = []
private_seller_data = []
seen_urls = set()


# Loop through each property listing
print("Processing the data...")
# Loop through each property listing
# Loop through each property listing
for property in properties:
    try:
        # Extract the price
        price_div = property.find('div', class_='price')
        price = price_div.get_text(strip=True) if price_div else 'N/A'
        
        # Extract the href value
        href_a_tag = property.find('a', class_='photoLink')
        href_value = href_a_tag['href'] if href_a_tag else 'N/A'
        
        # Extract the seller information
        seller_a_tag = property.find('a', class_='logoLink')
        seller = seller_a_tag['href'].replace('//', '') if seller_a_tag else 'N/A'
        
        # Extract the location
        location_a_tag = property.find('a', class_='lnk2')
        location = location_a_tag.get_text(strip=True) if location_a_tag else 'N/A'
        
        # Extract the property size
        size_a_tag = property.find('a', class_='lnk1')
        size = size_a_tag.get_text(strip=True) if size_a_tag else 'N/A'
        
        # Check for duplicates and only add if URL is unique and price is valid
        if href_value != 'N/A' and price != 'N/A' and href_value not in seen_urls:
            seen_urls.add(href_value)
            property_entry = {
                'Price': price,
                'URL': href_value,
                'Seller': seller,
                'Location': location,
                'Size': size
            }
            
            if seller == 'N/A':
                private_seller_data.append(property_entry)
            else:
                property_data.append(property_entry)
        
        # Print intermediate values for debugging
        print(f"Price: {price}, URL: {href_value}, Seller: {seller}, Location: {location}, Size: {size}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

# Convert to DataFrame and save to CSV
df = pd.DataFrame(property_data)
df_private = pd.DataFrame(private_seller_data)

df.to_csv('properties.csv', index=False)
df_private.to_csv('private_seller_properties.csv', index=False)

print("Scraping completed and data saved to properties.csv and private_seller_properties.csv")







