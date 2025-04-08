#!/usr/bin/env python3
import os
import re
import time
import csv
import tempfile
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

OUTPUT_FILE = "data/dane.csv"
LAST_UPDATE = "last_update.txt"
INTERVAL = 1800  # 30 minut

# Lista tygodni do sprawdzenia
WEEKS = ["708", "709", "710"]  # ID tygodni na sztywno

def setup_driver():
    """Konfiguruje i zwraca przeglądarkę Selenium."""
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()))
    wait = WebDriverWait(driver, 15)
    return driver, wait

def ustaw_tydzien(driver, week_id):
    """Ustawia określony tydzień w planie zajęć."""
    try:
        week_select = driver.find_element(By.ID, "wBWeek")
        week_option = week_select.find_element(By.CSS_SELECTOR, f"option[value='{week_id}']")
        driver.execute_script("arguments[0].selected = true;", week_option)
        
        show_button = driver.find_element(By.ID, "wBButton")
        show_button.click()
        time.sleep(0.5)
        print(f"    Ustawiono tydzień: {week_id}")
        return True
    except Exception as e:
        print(f"    Nie udało się ustawić tygodnia {week_id}: {e}")
        return False

def pobierz_date(driver):
    """Pobiera datę aktualizacji ze strony używając Selenium."""
    try:
        driver.get("https://plany.ubb.edu.pl/right_menu.php")
        time.sleep(1)
        page_source = driver.page_source
        match = re.search(r"Aktualizacja bazy:\s*([\d\-]+\s*[\d:]+)", page_source)
        return match.group(0).strip() if match else ""
    except Exception as e:
        print("Błąd przy pobieraniu daty:", e)
    return ""

def pobierz_katedry(driver):
    """Pobiera listę identyfikatorów katedr używając Selenium."""
    try:
        driver.get("https://plany.ubb.edu.pl/left_menu_feed.php?type=2&branch=6168&link=0")
        time.sleep(1)
        page_source = driver.page_source
        return re.findall(r"div_([0-9]+)", page_source)
    except Exception as e:
        print("Błąd przy pobieraniu katedr:", e)
    return []

def pobierz_nauczycieli(driver, katedra_id):
    """Dla danej katedry pobiera listę ID nauczycieli używając Selenium."""
    try:
        driver.get(f"https://plany.ubb.edu.pl/left_menu_feed.php?type=2&branch={katedra_id}&link=0&bOne=1&iPos=NaN")
        time.sleep(1)
        page_source = driver.page_source
        return re.findall(r"plan\.php\?type=10&amp;id=([0-9]+)", page_source)
    except Exception as e:
        print(f"Błąd przy pobieraniu nauczycieli dla katedry {katedra_id}:", e)
    return []

def pobierz_plan(driver, nauczyciel_id, wait):
    """Pobiera i przetwarza plan zajęć dla danego nauczyciela używając Selenium."""
    all_records = []
    url = f"https://plany.ubb.edu.pl/plan.php?type=10&id={nauczyciel_id}&winW=1920&winH=1080&loadBG=000000"
    
    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Pobierz nazwę nauczyciela
        title_divs = driver.find_elements(By.CLASS_NAME, "title")
        full_title = title_divs[-1].text if title_divs else "Nie znaleziono prowadzącego"
        teacher_match = re.search(r'Plan zajęć - (.*?), tydzień', full_title)
        teacher_name = teacher_match.group(1) if teacher_match else "Nie znaleziono prowadzącego"
        
        # Sprawdź każdy tydzień
        for week_id in WEEKS:
            if not ustaw_tydzien(driver, week_id):
                continue
            
            # Sprawdź, czy istnieje legenda
            legend_exists = driver.find_elements(By.ID, "legend")
            if not legend_exists:
                print(f"    Brak legendy w planie dla {teacher_name} (tydzień {week_id}). Pomijam tydzień.")
                continue
            
            # Pobierz legendę i stwórz słownik [kod -> nazwa przedmiotu]
            legend_element = driver.find_element(By.ID, "legend")
            legend_html = legend_element.get_attribute("innerHTML")
            legend_matches = re.findall(r'<strong>([\w\s()/|-]+)</strong>\s*(?:\([^)]*\))?\s*-\s*(.*?)(?:,|<)', legend_html)
            legend_dict = {abbr.strip().replace("-", ""): full_name.strip() for abbr, full_name in legend_matches}
            
            # Pobierz wszystkie bloki zajęć
            courses = driver.find_elements(By.CSS_SELECTOR, "div[id^='course_']")
            
            for course in courses:
                course_html = course.get_attribute("innerHTML")
                
                # Pobierz kod przedmiotu i typ zajęć
                subject_match = re.search(r'>([\w()/|-]+),\s*(\w+)<br>', course_html)
                if not subject_match:
                    continue
                
                subject_abbr = subject_match.group(1).strip()
                course_type = subject_match.group(2).strip()
                
                # Znormalizuj kod przedmiotu i pobierz pełną nazwę z legendy
                normalized_abbr = subject_abbr.replace("-", "")
                full_subject_name = legend_dict.get(normalized_abbr, subject_abbr)
                
                # Pobierz kierunek
                kierunek_match = re.search(r'<a href=.*?>([\w\sŚśŻżŹźĆćŃńÓóŁłĄąĘę]+?)/', course_html)
                if not kierunek_match:
                    continue
                major = kierunek_match.group(1).strip()
                if "erasmus" in major.lower():
                    continue
                
                # Ustalenie rodzaju studiów
                mode = "Nieokreślony"
                course_lower = course_html.lower()
                
                if "niestacjonarne wieczorowe" in course_lower or "nw parzyste" in course_lower or "nw nieparzyste" in course_lower: 
                    mode = "Niestacjonarne Wieczorowe"
                elif "s parzyste" in course_lower or "stacjonarne" in course_lower or "s nieparzyste" in course_lower:
                    mode = "Stacjonarne"
                elif "nz parzyste" in course_lower or "nz nieparzyste" in course_lower:
                    mode = "Niestacjonarne"
                else:
                    mode = "Niestacjonarne"
                
                # Dodaj rekord
                all_records.append([major, full_subject_name, course_type, teacher_name, mode])
    
    except Exception as e:
        print(f"Błąd przy pobieraniu planu dla nauczyciela {nauczyciel_id}: {e}")
    
    return all_records

def zapisz_dane(dane, current_date):
    """
    Zapisuje dane do pliku CSV.
    Dane zapisywane są w kolejności: [Major, Subject, Type, Teacher, Mode],
    a przed zapisem usuwane są duplikaty.
    """
    try:
        # Upewnij się, że katalog istnieje
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        # Zapisujemy do pliku tymczasowego
        with tempfile.NamedTemporaryFile("w", delete=False, newline='', encoding="utf-8") as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow(["Major", "Subject", "Type", "Teacher", "Mode"])
            # Usuwamy duplikaty poprzez konwersję na zbiór krotek
            unique_rows = {tuple(row) for row in dane}
            sorted_rows = sorted(unique_rows)
            for row in sorted_rows:
                writer.writerow(row)
            temp_filename = temp_file.name
        os.replace(temp_filename, OUTPUT_FILE)
        # Aktualizacja daty ostatniej aktualizacji
        with open(LAST_UPDATE, "w", encoding="utf-8") as f:
            f.write(current_date)
        print(f"Dane zapisane do {OUTPUT_FILE}. Liczba znalezionych rekordów: {len(sorted_rows)}.")
    except Exception as e:
        print("Błąd przy zapisie danych:", e)

def main():
    driver, wait = setup_driver()
    
    try:
        while True:
            print("Sprawdzam datę aktualizacji...")
            saved_date = ""
            if os.path.exists(LAST_UPDATE):
                try:
                    with open(LAST_UPDATE, "r", encoding="utf-8") as f:
                        saved_date = f.read().strip()
                except Exception as e:
                    print("Błąd przy odczycie pliku LAST_UPDATE:", e)
            
            current_date = pobierz_date(driver)
            if not current_date:
                print("Błąd: Nie udało się pobrać daty aktualizacji.")
                time.sleep(INTERVAL)
                continue
            
            if os.path.exists(OUTPUT_FILE) and saved_date == current_date:
                print("Brak zmian. Oczekuję...")
                time.sleep(INTERVAL)
                continue
            
            print("Zmiana wykryta. Pobieram dane...")
            all_records = []
            katedry = pobierz_katedry(driver)
            for katedra in katedry:
                nauczyciele = pobierz_nauczycieli(driver, katedra)
                for nauczyciel in nauczyciele:
                    records = pobierz_plan(driver, nauczyciel, wait)
                    all_records.extend(records)
            zapisz_dane(all_records, current_date)
            time.sleep(INTERVAL)
    
    except KeyboardInterrupt:
        print("Program przerwany przez użytkownika.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()