from flask import Flask, render_template, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

CSV_PATH = '../Scrapper/data/dane.csv'

def load_schedule_data():
    try:
        return pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"Błąd wczytywania pliku CSV: {e}")
        return pd.DataFrame()

# Funkcja do filtrowania tylko wykładów gdy nauczyciel ma kilka typów zajęć z tego samego przedmiotu
def filter_lectures_for_teacher_subject(df):
    if 'Teacher' not in df.columns or 'Subject' not in df.columns or 'Type' not in df.columns:
        return df  
    
    result_df = pd.DataFrame(columns=df.columns)
    
    # Grupuj dane według nauczyciela i przedmiotu
    grouped = df.groupby(['Teacher', 'Subject'])
    
    for (teacher, subject), group in grouped:
        has_lecture = 'wyk' in group['Type'].values
        
        if has_lecture:
            lectures = group[group['Type'] == 'wyk']
            result_df = pd.concat([result_df, lectures])
        else:
            result_df = pd.concat([result_df, group])
    
    return result_df

@app.route('/')
def index():
    df = load_schedule_data()
    if df.empty:
        return render_template('error.html', error="Nie można wczytać pliku z planem zajęć")
    
    # Filtruj dane, aby pokazać tylko wykłady gdy nauczyciel ma kilka typów zajęć z tego samego przedmiotu
    filtered_df = filter_lectures_for_teacher_subject(df)
    
    # Przygotuj unikalne wartości dla każdej kolumny
    unique_values = {}
    for column in filtered_df.columns:
        unique_values[column] = sorted(filtered_df[column].dropna().unique().tolist())
    
    # Kolumny do filtrowania (bez "Mode")
    filter_columns = [col for col in filtered_df.columns if col != "Mode"]
    
    return render_template('schedule.html', 
                          columns=filtered_df.columns.tolist(),
                          filter_columns=filter_columns,
                          data=filtered_df.values.tolist(),
                          unique_values=unique_values)

@app.route('/get_values/<column>')
def get_values(column):
    df = load_schedule_data()
    if df.empty or column not in df.columns:
        return jsonify([])
    
    filtered_df = filter_lectures_for_teacher_subject(df)
    
    values = sorted(filtered_df[column].dropna().unique().tolist())
    return jsonify(values)

# Trasa do filtrowania danych
@app.route('/filter', methods=['POST'])
def filter_schedule():
    filter_column = request.form.get('filter_column')
    filter_value = request.form.get('filter_value')
    filter_mode = request.form.get('filter_mode', 'all')
    
    df = load_schedule_data()
    if df.empty:
        return render_template('error.html', error="Nie można wczytać pliku z planem zajęć")
    
    df = filter_lectures_for_teacher_subject(df)
    
    unique_values = {}
    for column in df.columns:
        unique_values[column] = sorted(df[column].dropna().unique().tolist())
    
    # Kolumny do filtrowania (bez "Mode")
    filter_columns = [col for col in df.columns if col != "Mode"]
    
    # Filtrowanie według trybu studiów, jeśli nie wybrano "wszystkie"
    if filter_mode != 'all' and 'Mode' in df.columns:
        df = df[df['Mode'] == filter_mode]
    
    # Filtrowanie według wartości w wybranej kolumnie
    if filter_column in df.columns and filter_value:
        filtered_df = df[df[filter_column] == filter_value]
        
        applied_filters = []
        if filter_mode != 'all':
            applied_filters.append(f"Tryb: {filter_mode}")
        if filter_value:
            applied_filters.append(f"{filter_column}: {filter_value}")
            
        filter_info = ", ".join(applied_filters) if applied_filters else ""
        
        return render_template('schedule.html', 
                              columns=filtered_df.columns.tolist(),
                              filter_columns=filter_columns,
                              data=filtered_df.values.tolist(),
                              filter_applied=filter_info,
                              unique_values=unique_values,
                              selected_column=filter_column,
                              selected_value=filter_value,
                              selected_mode=filter_mode)
    
    return render_template('schedule.html', 
                          columns=df.columns.tolist(),
                          filter_columns=filter_columns,
                          data=df.values.tolist(),
                          filter_applied="Tryb: " + filter_mode if filter_mode != 'all' else None,
                          unique_values=unique_values,
                          selected_column=filter_column,
                          selected_value=filter_value,
                          selected_mode=filter_mode)


if __name__ == '__main__':
    if not os.path.exists(CSV_PATH):
        print(f"UWAGA: Plik CSV nie istnieje w ścieżce: {CSV_PATH}")
        print(f"Aplikacja zostanie uruchomiona, ale będzie wyświetlać błąd do czasu utworzenia pliku.")
        print(f"Upewnij się, że ścieżka {os.path.abspath(CSV_PATH)} jest poprawna.")
    
    # Uruchom aplikację Flaska
    app.run(debug=True, host='0.0.0.0', port=5000)