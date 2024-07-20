# imot-scrape

This project is a web scraping tool designed to collect real estate property data from a Bulgarian real estate website. The tool extracts details such as price, currency, URL, seller information, location, size, floor, total floors, year built, material, property type, phone number, price per sqm, publish date, and visit count. It distinguishes between private sellers and agencies and ensures unique data capture for each property listing.

## Features

- **Pagination Handling**: Extracts URLs of all pages from the pagination section.
- **Property Detail Extraction**: Fetches additional data from property detail pages.
- **Data Parsing**: Handles different formats and patterns for dates, sizes, and other property attributes.
- **Error Handling**: Logs errors and handles exceptions to avoid crashes.
- **Logging**: Records details such as the number of pages, number of listings, timestamps, and error messages.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/real-estate-scraper.git
    cd real-estate-scraper
    ```

2. **Create a virtual environment**:
    ```bash
    python -m venv venv
    ```

3. **Activate the virtual environment**:

    - On Windows:
        ```bash
        .\venv\Scripts\activate
        ```

    - On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```

4. **Install the required packages**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. **Run the scraper**:
    ```bash
    python main.py
    ```

2. **Log Output**:
    The script will generate a log file named `scraping_log.log` which will contain information about the scraping process including the number of pages, number of listings, timestamps, and error messages if any.

3. **Output Data**:
    The scraped data will be saved to a CSV file named `properties.csv` in the root directory.

## Logging Details

- **Number of Pages**: The number of pages processed during the scraping.
- **Number of Listings**: The total number of property listings processed.
- **Timestamp**: The timestamp for each run of the scraper.
- **Errors**: Any errors encountered during the scraping process.

## Example Output

The CSV file `properties.csv` will contain the following columns:

- `Price`
- `Currency`
- `URL`
- `Seller`
- `Seller URL`
- `Seller Phone`
- `Location`
- `Size`
- `Floor`
- `Total Floors`
- `Year`
- `Material`
- `Property Type`
- `Phone`
- `Price per sqm`
- `Publish Date`
- `Visits Count`
- `Status`

## Contributing

Feel free to fork this repository, make changes, and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

If you have any questions, feel free to reach out at [your-email@example.com].

