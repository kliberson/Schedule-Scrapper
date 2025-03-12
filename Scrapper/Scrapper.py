#!/usr/bin/env python3
import os
import re
import time
import csv
import tempfile
import requests

OUTPUT_FILE = "data/dane.csv"
LAST_UPDATE = "last_update.txt"
INTERVAL = 1800  # 30 minut

HEADERS = {"User-Agent": "Mozilla/5.0"}

def pobierz_date():
    """Pobiera datę aktualizacji ze strony."""
    url = "https://plany.ubb.edu.pl/right_menu.php#"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.ok:
            # Szukamy ciągu po "Aktualizacja bazy:" (np. "2025-03-11 12:34:56")
            match = re.search(r"Aktualizacja bazy:\s*([\d\-]+\s*[\d:]+)", response.text)

            return match.group(0).strip() if match else ""
    except Exception as e:
        print("Błąd przy pobieraniu daty:", e)
    return ""

def pobierz_katedry():
    """Pobiera listę identyfikatorów katedr."""
    url = "https://plany.ubb.edu.pl/left_menu_feed.php?type=2&branch=6168&link=0"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.ok:
            return re.findall(r"div_([0-9]+)", response.text)
    except Exception as e:
        print("Błąd przy pobieraniu katedr:", e)
    return []

def pobierz_nauczycieli(katedra_id):
    """Dla danej katedry pobiera listę ID nauczycieli."""
    url = f"https://plany.ubb.edu.pl/left_menu_feed.php?type=2&branch={katedra_id}&link=0&bOne=1&iPos=NaN"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.ok:
            return re.findall(r"plan\.php\?type=10&amp;id=([0-9]+)", response.text)
    except Exception as e:
        print(f"Błąd przy pobieraniu nauczycieli dla katedry {katedra_id}:", e)
    return []

def pobierz_plan(nauczyciel_id):
    """Pobiera stronę planu zajęć dla danego nauczyciela."""
    url = f"https://plany.ubb.edu.pl/plan.php?type=10&id={nauczyciel_id}&winW=1920&winH=1080&loadBG=000000"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.ok:
            return response.text
    except Exception as e:
        print(f"Błąd przy pobieraniu planu dla nauczyciela {nauczyciel_id}:", e)
    return ""

def przetworz_plan(plan):
    """
    Przetwarza stronę planu, wyciągając:
      - Nazwę nauczyciela (na podstawie nagłówka planu)
      - Legendę z danymi (fragment HTML zawierający mapowanie kodów na nazwy przedmiotów)
      - Bloki zawierające informacje o przedmiotach,
        z których pobierany jest kod przedmiotu, typ zajęć oraz kierunek (major)
      - Na podstawie legendy ustalana jest pełna nazwa przedmiotu (Subject)
    Zwraca listę rekordów, gdzie każdy rekord to lista: [Major, Subject, Type, Teacher].
    """
    # Wyciągnięcie nazwy nauczyciela
    teacher_match = re.search(r"Plan zajęć - (.*),\s*tydzień", plan)
    teacher_name = teacher_match.group(1).strip() if teacher_match else ""
    
    # Wyciągnięcie legendy
    legend_match = re.search(r'(<div class="data">.*?<img src="images/resize\.png".*?</div>)', plan, re.DOTALL)
    legend = legend_match.group(1) if legend_match else ""
    
    # Konwersja strony na jeden wiersz i podział na bloki zakończone </div>
    page_line = plan.replace("\n", " ")
    blocks = [block for block in re.split(r'</div>', page_line) if '<div id="course_' in block]
    
    records = []
    
    for block in blocks:
        # Pobranie informacji o przedmiocie z bloku: szukamy tekstu po <img ...> przed <br
        course_info_match = re.search(r'<img[^>]*>([^<]*)<br', block)
        if not course_info_match:
            continue
        course_info = course_info_match.group(1).strip()
        # Usuwamy białe znaki (wszystkie spacje)
        course_info = re.sub(r'\s+', '', course_info)
        if not course_info:
            continue
        parts = course_info.split(',')
        course_code = parts[0] if parts else ""
        course_type = parts[1] if len(parts) > 1 else ""
        
        # Pobranie kierunku (major) z bloku
        major_match = re.search(r'<a href[^>]*>([^/<]*)/', block)
        if not major_match:
            continue
        major = major_match.group(1).strip()
        
        # Ustalenie pełnej nazwy przedmiotu na podstawie legendy
        course_name = course_code  # domyślnie używamy kodu
        if legend:
            pattern = rf"<strong>{re.escape(course_code)}</strong>\s*-\s*(.+?)(?:,|<)"
            course_name_match = re.search(pattern, legend)
            if course_name_match:
                course_name = course_name_match.group(1).strip()
        
        records.append([major, course_name, course_type, teacher_name])
    return records

def zapisz_dane(dane, current_date):
    """
    Zapisuje dane do pliku CSV.
    Dane zapisywane są w kolejności: [Major, Subject, Type, Teacher],
    a przed zapisem usuwane są duplikaty.
    """
    try:
        # Zapisujemy do pliku tymczasowego
        with tempfile.NamedTemporaryFile("w", delete=False, newline='', encoding="utf-8") as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow(["Major", "Subject", "Type", "Teacher"])
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
    while True:
        print("Sprawdzam datę aktualizacji...")
        saved_date = ""
        if os.path.exists(LAST_UPDATE):
            try:
                with open(LAST_UPDATE, "r", encoding="utf-8") as f:
                    saved_date = f.read().strip()
            except Exception as e:
                print("Błąd przy odczycie pliku LAST_UPDATE:", e)
        
        current_date = pobierz_date()
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
        katedry = pobierz_katedry()
        for katedra in katedry:
            nauczyciele = pobierz_nauczycieli(katedra)
            for nauczyciel in nauczyciele:
                plan = pobierz_plan(nauczyciel)
                if plan:
                    records = przetworz_plan(plan)
                    all_records.extend(records)
        zapisz_dane(all_records, current_date)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
