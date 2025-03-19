  UBB Plan Scrapper

UBB Plan Scraper is a Python tool that automatically retrieves class schedule data from https://plany.ubb.edu.pl using Selenium. It periodically checks for schedule updates and saves the retrieved data into a CSV file and displays teachers for selected subjects.

   Features

-   Automatic Update Check:    
  The script checks the update date on the website every 30 minutes (by default) and only retrieves data if changes are detected.

-   Data Retrieval:    
  -   Departments:   Scrapes a list of department IDs.
  -   Teachers:   For each department, retrieves a list of teacher IDs.
  -   Class Schedules:   For each teacher, extracts detailed schedule information including:
    - Major
    - Subject (both abbreviation and full name, mapped using the legend)
    - Type of class (e.g., lecture)
    - Teacher's name
    - Study mode (e.g., full-time, part-time)

-   Data Saving:    
  The gathered records are saved to a CSV file (`data/dane.csv`) with duplicates removed. The latest update date is stored in `last_update.txt`.

   Prerequisites

-   Python 3      
-   Python Libraries:    
  - `selenium`
  - `webdriver-manager`

   Installation

1.   Clone the repository:  


   git clone <repository_url>
   cd <repository_directory>


2.   (Optional) Create a virtual environment:  

   python3 -m venv venv
   source venv/bin/activate    For Windows: venv\Scripts\activate


3.   Install dependencies:  

   pip install selenium webdriver-manager


   Configuration

-   Update Interval:    
  The default interval for checking updates is set to `1800` seconds (30 minutes). You can adjust the `INTERVAL` constant in the script as needed.

-   Weeks List:    
  The weeks to be checked are defined in the `WEEKS` list (default: `["709", "710", "711"]`). Modify this list according to your requirements.

   Running the Script

To start the scraper, run the following command:

./<script_name>.py

or

python3 <script_name>.py


During execution, the script will:
- Launch Firefox via Selenium.
- Retrieve the current update date from the website.
- If an update is detected (i.e., the date has changed), scrape data for departments, teachers, and schedules.
- Save unique records to `data/dane.csv` and update `last_update.txt` with the new date.

    Stopping the Script

Press   CTRL+C   to safely terminate the program.

   Notes

- Ensure you have write permissions to the `data/` directory.
- If you experience issues with Selenium, verify that your Firefox browser is up-to-date.
- The script is designed to run continuously and check for updates at the defined interval.

   License

This project is licensed under the MIT License.

---

Feel free to modify any sections as needed for your project.
