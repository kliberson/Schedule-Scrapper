from flask import Flask, render_template, request
import pandas as pd
import os

app = Flask(__name__)

# Upewnij się, że katalogi templates i static istnieją
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

# Stała ścieżka do pliku CSV
CSV_PATH = '../Scrapper/data/dane.csv'

# Funkcja do wczytywania danych z pliku CSV
def load_schedule_data():
    try:
        return pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"Błąd wczytywania pliku CSV: {e}")
        return pd.DataFrame()

# Trasa główna - od razu wyświetla plan zajęć
@app.route('/')
def index():
    df = load_schedule_data()
    if df.empty:
        return render_template('error.html', error="Nie można wczytać pliku z planem zajęć")
    
    return render_template('schedule.html', 
                          columns=df.columns.tolist(),
                          data=df.values.tolist())

# Trasa do filtrowania danych
@app.route('/filter', methods=['POST'])
def filter_schedule():
    filter_column = request.form.get('filter_column')
    filter_value = request.form.get('filter_value')
    filter_mode = request.form.get('filter_mode', 'all')
    
    df = load_schedule_data()
    if df.empty:
        return render_template('error.html', error="Nie można wczytać pliku z planem zajęć")
    
    # Filtrowanie według trybu studiów, jeśli nie wybrano "wszystkie"
    if filter_mode != 'all' and 'Mode' in df.columns:
        df = df[df['Mode'] == filter_mode]
    
    # Filtrowanie według wartości w wybranej kolumnie
    if filter_column in df.columns and filter_value:
        filtered_df = df[df[filter_column].astype(str).str.contains(filter_value, case=False)]
        
        applied_filters = []
        if filter_mode != 'all':
            applied_filters.append(f"Tryb: {filter_mode}")
        if filter_value:
            applied_filters.append(f"{filter_column}: {filter_value}")
            
        filter_info = ", ".join(applied_filters) if applied_filters else ""
        
        return render_template('schedule.html', 
                              columns=filtered_df.columns.tolist(),
                              data=filtered_df.values.tolist(),
                              filter_applied=filter_info)
    
    return render_template('schedule.html', 
                          columns=df.columns.tolist(),
                          data=df.values.tolist(),
                          filter_applied="Tryb: " + filter_mode if filter_mode != 'all' else None,
                          error="Nieprawidłowa kolumna do filtrowania" if filter_value else None)

# Stwórz pliki szablonów
def create_template_files():
    # Tworzenie error.html
    error_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Błąd - Plan Zajęć</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <div class="container">
        <h1>Błąd</h1>
        <div class="error">{{ error }}</div>
        <p>Sprawdź czy plik CSV istnieje w lokalizacji: ../Scrapper/data/dane.csv</p>
    </div>
</body>
</html>
    '''
    
    # Tworzenie schedule.html
    schedule_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Plan Zajęć</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <div class="container">
        <h1>Plan Zajęć</h1>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <div class="filter-form">
            <h3>Filtruj dane</h3>
            <form action="/filter" method="post">
                <div class="form-group">
                    <label for="filter_mode">Tryb studiów:</label>
                    <select name="filter_mode" id="filter_mode">
                        <option value="all">Wszystkie</option>
                        <option value="Stacjonarne">Stacjonarne</option>
                        <option value="Zaoczne">Zaoczne</option>
                        <option value="Nieokreślony">Nieokreślony</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="filter_column">Kolumna:</label>
                    <select name="filter_column" id="filter_column">
                        {% for column in columns %}
                        <option value="{{ column }}">{{ column }}</option>
                        {% endfor %}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="filter_value">Wartość:</label>
                    <input type="text" name="filter_value" id="filter_value" placeholder="Wpisz wartość">
                </div>
                
                <div class="form-buttons">
                    <button type="submit">Filtruj</button>
                    <button type="button" onclick="location.href='/'">Resetuj filtry</button>
                </div>
            </form>
        </div>
        
        {% if filter_applied %}
        <div class="filter-info">
            <p>Zastosowano filtry: {{ filter_applied }}</p>
        </div>
        {% endif %}
        
        <div class="schedule-table">
            <table>
                <thead>
                    <tr>
                        {% for column in columns %}
                        <th>{{ column }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for row in data %}
                    <tr>
                        {% for cell in row %}
                        <td>{{ cell }}</td>
                        {% endfor %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
    '''
    
    # Tworzenie style.css
    css_content = '''
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: Arial, sans-serif;
    background-color: #f4f4f4;
    color: #333;
    line-height: 1.6;
}

.container {
    width: 95%;
    max-width: 1400px;
    margin: 20px auto;
    padding: 20px;
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

h1 {
    text-align: center;
    margin-bottom: 20px;
    color: #2c3e50;
}

h3 {
    color: #2c3e50;
    margin-bottom: 15px;
}

.filter-form {
    margin-bottom: 30px;
    padding: 15px;
    background-color: #f9f9f9;
    border-radius: 5px;
}

form {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
    align-items: flex-end;
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.form-buttons {
    display: flex;
    gap: 10px;
}

label {
    font-weight: bold;
    color: #555;
}

input, select, button {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

select {
    min-width: 150px;
}

button {
    background-color: #3498db;
    color: white;
    border: none;
    cursor: pointer;
    padding: 8px 15px;
}

button:hover {
    background-color: #2980b9;
}

.error {
    background-color: #f8d7da;
    color: #721c24;
    padding: 10px;
    margin-bottom: 20px;
    border-radius: 4px;
}

.filter-info {
    margin-bottom: 15px;
    padding: 8px;
    background-color: #e8f4fd;
    border-radius: 4px;
}

.schedule-table {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}

th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

th {
    background-color: #3498db;
    color: white;
    position: sticky;
    top: 0;
}

tr:nth-child(even) {
    background-color: #f2f2f2;
}

tr:hover {
    background-color: #ddd;
}

@media screen and (max-width: 768px) {
    form {
        flex-direction: column;
        align-items: stretch;
    }
    
    .form-buttons {
        flex-direction: column;
    }
    
    th, td {
        padding: 8px;
        font-size: 14px;
    }
}
    '''
    
    # Zapisz pliki
    with open('templates/error.html', 'w', encoding='utf-8') as f:
        f.write(error_html)
    
    with open('templates/schedule.html', 'w', encoding='utf-8') as f:
        f.write(schedule_html)
    
    with open('static/style.css', 'w', encoding='utf-8') as f:
        f.write(css_content)

if __name__ == '__main__':
    # Stwórz pliki szablonów przy pierwszym uruchomieniu
    create_template_files()
    
    # Sprawdź czy plik CSV istnieje przed uruchomieniem aplikacji
    if not os.path.exists(CSV_PATH):
        print(f"UWAGA: Plik CSV nie istnieje w ścieżce: {CSV_PATH}")
        print(f"Aplikacja zostanie uruchomiona, ale będzie wyświetlać błąd do czasu utworzenia pliku.")
        print(f"Upewnij się, że ścieżka {os.path.abspath(CSV_PATH)} jest poprawna.")
    
    # Uruchom aplikację Flaska
    app.run(debug=True, host='0.0.0.0', port=5000)